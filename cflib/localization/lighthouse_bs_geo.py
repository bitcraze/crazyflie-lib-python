# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2021 Bitcraze AB
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
Functionality to handle base station geometry in the lighthouse poistioning system
"""
import math

import numpy as np
import pkg_resources
installed = {pkg.key for pkg in pkg_resources.working_set}
if {'opencv-python-headless'} - installed:
    OPENCV_INSTALLED = False
else:
    import cv2 as cv
    OPENCV_INSTALLED = True


class LighthouseBsGeoEstimator:
    """
    This class is used to estimate the geometry (position and attitude)
    of a lighthouse base station, given angles measured using a lighthouse deck.
    """

    def __init__(self):

        self._estimator_available = True
        if OPENCV_INSTALLED is False:
            self._estimator_available = False

        self._directions = {
            self._hash_sensor_order([2, 0, 1, 3]): math.radians(0),
            self._hash_sensor_order([2, 0, 3, 1]): math.radians(25),
            self._hash_sensor_order([2, 3, 0, 1]): math.radians(65),
            self._hash_sensor_order([3, 2, 0, 1]): math.radians(90),
            self._hash_sensor_order([3, 2, 1, 0]): math.radians(115),
            self._hash_sensor_order([3, 1, 2, 0]): math.radians(155),
            self._hash_sensor_order([1, 3, 2, 0]): math.radians(180),
            self._hash_sensor_order([1, 3, 0, 2]): math.radians(205),
            self._hash_sensor_order([1, 0, 3, 2]): math.radians(245),
            self._hash_sensor_order([0, 1, 3, 2]): math.radians(270),
            self._hash_sensor_order([0, 1, 2, 3]): math.radians(295),
            self._hash_sensor_order([0, 2, 1, 3]): math.radians(335),
        }

        # Sensor distances on the lighthouse deck
        sensor_distance_width = 0.015
        sensor_distance_length = 0.03

        # Sensor positions in world coordinates, open cv style
        self._lighthouse_3d = np.float32(
            [
                [-sensor_distance_width / 2, 0, -sensor_distance_length / 2],
                [sensor_distance_width / 2, 0, -sensor_distance_length / 2],
                [-sensor_distance_width / 2, 0, sensor_distance_length / 2],
                [sensor_distance_width / 2, 0, sensor_distance_length / 2]
            ])

        # Camera matrix
        self._K = np.float64(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0]
            ])

        self._dist_coef = np.zeros(4)

        # Sanity check maximum pos
        self._sanity_max_pos = 10

    def is_available(self):
        return self._estimator_available

    def estimate_geometry(self, bs_vectors):
        """
        Estimate the full pose of a base station based on angles from the 4 sensors
        on a lighthouse deck. The result is a rotation matrix and position of the
        base station, in the Crazyflie reference frame.

        :param bs_vectors A list of 4 LighthouseBsVector objects specifying vectors to the 4 sensors
        :return rot_bs_in_cf_coord: Rotation matrix of the BS in the CFs coordinate system
        :return pos_bs_in_cf_coord: Position vector of the BS in the CFs coordinate system
        """

        if OPENCV_INSTALLED is False:
            raise Exception('OpenCV is not installed. To use this function,' +
                            'do "pip3 install opencv-python-headless"' +
                            ' and restart the cfclient')

        guess_yaw = self._find_initial_yaw_guess(bs_vectors)
        rvec_guess, tvec_guess = self._convert_yaw_to_open_cv(guess_yaw)
        rw_ocv, tw_ocv = self._estimate_pose_by_pnp(bs_vectors, rvec_guess, tvec_guess)
        rot_bs_in_cf_coord, pos_bs_in_cf_coord = self._opencv_to_cf(rw_ocv, tw_ocv)
        return rot_bs_in_cf_coord, pos_bs_in_cf_coord

    def sanity_check_result(self, pos_bs_in_cf_coord):
        """
        Checks if the estimated geometry is within reasonable bounds. It returns
        true if it seems reasonable or false if it doesn't
        """
        for coord in pos_bs_in_cf_coord:
            if (abs(coord) > self._sanity_max_pos):
                return False
        return True

    def _find_initial_yaw_guess(self, bs_vectors):
        # Assume bs is faicing slighly downwards and fairly horizontal
        # Sort sensors in the order they are hit by the horizontal sweep
        # and use the order to figure out roughly the direction to the
        # base station
        sweeps_x = {
            0: bs_vectors[0].lh_v1_horiz_angle,
            1: bs_vectors[1].lh_v1_horiz_angle,
            2: bs_vectors[2].lh_v1_horiz_angle,
            3: bs_vectors[3].lh_v1_horiz_angle
        }

        ordered_map = {k: v for k, v in sorted(sweeps_x.items(), key=lambda item: item[1])}
        sensor_order = list(ordered_map.keys())

        # The base station is roughly in this direction, in CF (world) coordinates
        return self._directions[self._hash_sensor_order(sensor_order)]

    def _hash_sensor_order(self, order):
        hash = 0
        for i in range(4):
            hash += order[i] * 4 ** i
        return hash

    def _convert_yaw_to_open_cv(self, yaw):
        # Base station height
        bs_h = 2.0
        # Distance to base station along the floor
        bs_fd = 3.0
        # Distance to base station
        bs_dist = math.sqrt(bs_h ** 2 + bs_fd ** 2)
        elevation = math.atan2(bs_h, bs_fd)

        # Initial position of the CF in camera coordinate system, open cv style
        tvec_start = np.array([0, 0, bs_dist])

        # Calculate rotation matrix
        d_c = math.cos(-yaw + math.pi)
        d_s = math.sin(-yaw + math.pi)
        R_rot_y = np.array([
            [d_c, 0.0, d_s],
            [0.0, 1.0, 0.0],
            [-d_s, 0.0, d_c],
        ])

        e_c = math.cos(elevation)
        e_s = math.sin(elevation)
        R_rot_x = np.array([
            [1.0, 0.0, 0.0],
            [0.0, e_c, -e_s],
            [0.0, e_s, e_c],
        ])

        R = np.dot(R_rot_x, R_rot_y)
        rvec_start, _ = cv.Rodrigues(R)

        return rvec_start, tvec_start

    def _estimate_pose_by_pnp(self, bs_vectors, rvec_start, tvec_start):
        # Sensors as seen by the "camera"
        lighthouse_image_projection = np.float32(
            [
                [-math.tan(bs_vectors[0].lh_v1_horiz_angle), -math.tan(bs_vectors[0].lh_v1_vert_angle)],
                [-math.tan(bs_vectors[1].lh_v1_horiz_angle), -math.tan(bs_vectors[1].lh_v1_vert_angle)],
                [-math.tan(bs_vectors[2].lh_v1_horiz_angle), -math.tan(bs_vectors[2].lh_v1_vert_angle)],
                [-math.tan(bs_vectors[3].lh_v1_horiz_angle), -math.tan(bs_vectors[3].lh_v1_vert_angle)]
            ])

        _ret, rvec_est, tvec_est = cv.solvePnP(
            self._lighthouse_3d,
            lighthouse_image_projection,
            self._K,
            self._dist_coef,
            flags=cv.SOLVEPNP_ITERATIVE,
            rvec=rvec_start,
            tvec=tvec_start,
            useExtrinsicGuess=True)

        if not _ret:
            raise Exception('No solution found')

        Rw_ocv, Tw_ocv = self._cam_to_world(rvec_est, tvec_est)
        return Rw_ocv, Tw_ocv

    def _cam_to_world(self, rvec_c, tvec_c):
        R_c, _ = cv.Rodrigues(rvec_c)
        R_w = np.linalg.inv(R_c)
        tvec_w = -np.matmul(R_w, tvec_c)
        return R_w, tvec_w

    def _opencv_to_cf(self, R_cv, t_cv):
        R_opencv_to_cf = np.array([
            [0.0, 0.0, 1.0],
            [-1.0, 0.0, 0.0],
            [0.0, -1.0, 0.0],
        ])

        R_cf_to_opencv = np.array([
            [0.0, -1.0, 0.0],
            [0.0, 0.0, -1.0],
            [1.0, 0.0, 0.0],
        ])

        t_cf = np.dot(R_opencv_to_cf, t_cv)
        R_cf = np.dot(R_opencv_to_cf, np.dot(R_cv, R_cf_to_opencv))

        return R_cf, t_cf
