# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2022 Bitcraze AB
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
from __future__ import annotations

import numpy as np
import numpy.typing as npt

from .ippe_cf import IppeCf
from cflib.localization.lighthouse_types import LhBsCfPoses
from cflib.localization.lighthouse_types import LhCfPoseSample
from cflib.localization.lighthouse_types import Pose


class LighthouseInitialEstimator:
    """
    Make initial estimates of base station and CF poses useing IPPE (analytical solution).
    The estimates are not good enough to use for flight but is a starting point for further
    Calculations.
    """

    @classmethod
    def estimate(cls, matched_samples: list[LhCfPoseSample], sensor_positions: npt.ArrayLike) -> LhBsCfPoses:
        """
        Make a rough estimate of the poses of all base stations and CF poses found in the samples.

        The pose of the Crazyflie in the first sample is used as a reference and will define the
        global reference frame.

        :param matched_samples: A list of samples with lihghthouse angles.
        :param sensor_positions: An array with the sensor positions on the lighthouse deck (3D, CF ref frame)
        :return: a
        """

        bs_poses_ref_cfs = cls._angles_to_poses(matched_samples, sensor_positions)

        # Use the first CF pose as the global reference frame
        bs_poses: dict[int, Pose] = bs_poses_ref_cfs[0]

        cls._calc_remaining_bs_poses(bs_poses_ref_cfs, bs_poses)
        cf_poses = cls._calc_cf_poses(bs_poses_ref_cfs, bs_poses)

        return LhBsCfPoses(bs_poses, cf_poses)

    @classmethod
    def _angles_to_poses(cls, matched_samples: list[LhCfPoseSample], sensor_positions: npt.ArrayLike
                         ) -> list[dict[int, Pose]]:
        """
        Estimate the base station poses in the Crazyflie reference frames, for each sample.
        """
        result: list[dict[int, Pose]] = []
        for sample in matched_samples:
            poses: dict[int, Pose] = {}
            for bs, angles in sample.angles_calibrated.items():
                Q = angles.projection_pair_list()
                estimates_ref_bs = IppeCf.solve(sensor_positions, Q)
                estimates_ref_cf = cls._convert_estimates_to_cf_reference_frame(estimates_ref_bs)
                bs_pose = cls._solution_picker(estimates_ref_cf)

                poses[bs] = bs_pose
            result.append(poses)
        return result

    @classmethod
    def _convert_estimates_to_cf_reference_frame(cls, estimates_ref_bs: list[IppeCf.Solution]) -> tuple[Pose, Pose]:
        """
        Convert the two ippe solutions from the base station reference frame to the CF reference frame
        """
        R1 = estimates_ref_bs[0].R.transpose()
        t1 = np.dot(R1, -estimates_ref_bs[0].t)

        R2 = estimates_ref_bs[1].R.transpose()
        t2 = np.dot(R2, -estimates_ref_bs[1].t)

        return Pose(R1, t1), Pose(R2, t2)

    @classmethod
    def _solution_picker(cls, estimates_ref_cf: tuple[Pose, Pose]) -> Pose:
        """
        IPPE produces two solutions and we have to pick the right one.
        The solutions are on opposite sides of the CF Z-axis and one of them is also flipped up side down.
        Assuming that our base stations are pointing downwards and that the CF is fairly flat, we can
        find the correct solution by looking at the orientation and pick the one where the Z-axis is pointing
        upwards.

        :param estimates_ref_cf: The two possible estimated base station poses
        :return: The selected solution
        """
        pose1 = estimates_ref_cf[0]
        pose2 = estimates_ref_cf[1]

        if np.dot(pose1.rot_matrix, (0.0, 0.0, 1.0))[2] > np.dot(pose2.rot_matrix, (0.0, 0.0, 1.0))[2]:
            return pose1
        else:
            return pose2

    @classmethod
    def _calc_remaining_bs_poses(cls, bs_poses_ref_cfs: list[dict[int, Pose]], bs_poses: dict[int, Pose]) -> None:
        # Find all base stations in the list
        all_bs = set()
        for initial_est_bs_poses in bs_poses_ref_cfs:
            all_bs.update(initial_est_bs_poses.keys())

        # Remove the reference base stations that we already have the poses for
        to_find = all_bs - bs_poses.keys()

        # run through the list of samples until we manage to find them all
        remaining = len(to_find)
        while remaining > 0:
            for initial_est_bs_poses in bs_poses_ref_cfs:
                bs_poses_in_sample = initial_est_bs_poses
                unknown = to_find.intersection(bs_poses_in_sample.keys())
                known = set(bs_poses.keys()).intersection(bs_poses_in_sample.keys())

                # We need (at least) one known bs pose to use when transforming the other poses to the global ref frame
                if len(known) > 0:
                    known_bs = list(known)[0]

                    # The known BS pose in the global reference frame
                    known_global = bs_poses[known_bs]
                    # The known BS pose in the CF reference frame (of this sample)
                    known_cf = bs_poses_in_sample[known_bs]

                    for bs in unknown:
                        # The unknown BS pose in the CF reference frame (of this sample)
                        unknown_cf = bs_poses_in_sample[bs]
                        # Finally we can calculate the BS pose in the global reference frame
                        bs_poses[bs] = cls._map_pose_to_ref_frame(known_global, known_cf, unknown_cf)

                to_find = all_bs - bs_poses.keys()
                if len(to_find) == 0:
                    break

            if len(to_find) == remaining:
                raise Exception('Can not link positions between all base stations')

            remaining = len(to_find)

    @classmethod
    def _calc_cf_poses(cls, bs_poses_ref_cfs: list[dict[int, Pose]], bs_poses: list[Pose]) -> list[Pose]:
        cf_poses: list[Pose] = []

        for initial_est_bs_poses in bs_poses_ref_cfs:
            # Use the first base station pose as a reference
            est_ref_cf = initial_est_bs_poses
            ref_bs = list(est_ref_cf.keys())[0]

            pose_global = bs_poses[ref_bs]
            pose_cf = est_ref_cf[ref_bs]
            est_ref_global = cls._map_cf_pos_to_cf_pos(pose_global, pose_cf)

            cf_poses.append(est_ref_global)

        return cf_poses

    @classmethod
    def _map_pose_to_ref_frame(cls, pose1_ref1: Pose, pose1_ref2: Pose, pose2_ref2: Pose) -> Pose:
        """
        Express pose2 in reference system 1, given pose1 in both reference system 1 and 2
        """
        R_o2_in_1, t_o2_in_1 = cls._map_cf_pos_to_cf_pos(pose1_ref1, pose1_ref2).matrix_vec

        t = np.dot(R_o2_in_1, pose2_ref2.translation) + t_o2_in_1
        R = np.dot(R_o2_in_1, pose2_ref2.rot_matrix)

        return Pose(R, t)

    @classmethod
    def _map_cf_pos_to_cf_pos(cls, pose1_ref1: Pose, pose1_ref2: Pose) -> Pose:
        """
        Find the rotation/translation from ref1 to ref2 given a pose,
        that is the returned Pose will tell us where the origin in ref2 is,
        expressed in ref1
        """

        R_inv_ref2 = np.matrix.transpose(pose1_ref2.rot_matrix)
        R = np.dot(pose1_ref1.rot_matrix, R_inv_ref2)
        t = pose1_ref1.translation - np.dot(R, pose1_ref2.translation)

        return Pose(R, t)
