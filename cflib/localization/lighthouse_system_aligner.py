# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2021-2022 Bitcraze AB
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
import scipy.optimize

from cflib.localization.lighthouse_types import Pose


class LighthouseSystemAligner:
    """This class is used to align a lighthouse system to a few sampled positions"""
    @classmethod
    def align(cls, origin: npt.ArrayLike, x_axis: list[npt.ArrayLike], xy_plane: list[npt.ArrayLike],
              bs_poses: dict[int, Pose]) -> tuple[dict[int, Pose], Pose]:
        """
        Align a coordinate system with the physical world. Finds the transform from the
        current reference frame to one that is aligned with measured positions, and transforms base station
        poses to the new coordinate system.

        :param origin: The position of the desired origin in the current reference frame
        :param x_axis: One or more positions on the desired positive X-axis (X>0, Y=Z=0) in the current
                       reference frame
        :param x_axis: One or more positions in the desired XY-plane (Z=0) in the current reference frame
        :param bs_poses: a dictionary with the base station poses in the current reference frame
        :return: a dictionary with the base station poses in the desired reference frame and the transformation
        """
        raw_transformation = cls._find_transformation(origin, x_axis, xy_plane)
        transformation = cls._de_flip_transformation(raw_transformation, x_axis, bs_poses)

        result: dict[int, Pose] = {}
        for bs_id, pose in bs_poses.items():
            result[bs_id] = transformation.rotate_translate_pose(pose)

        return result, transformation

    @classmethod
    def _find_transformation(cls, origin: npt.ArrayLike, x_axis: list[npt.ArrayLike],
                             xy_plane: list[npt.ArrayLike]) -> Pose:
        """
        Finds the transformation from the current reference frame to a desired reference frame based on measured
        positions of the desired reference frame.

        :param origin: The position of the desired origin in the current reference frame
        :param x_axis: One or more positions on the desired positive X-axis (X>0, Y=Z=0) in the current
                       reference frame
        :param x_axis: One or more positions in the desired XY-plane (Z=0) in the current reference frame
        :return: The transformation from the current reference frame to the desired reference frame. Note: the
                 solution may be flipped.
        """
        args = (origin, x_axis, xy_plane)

        x0 = np.zeros((6))

        result = scipy.optimize.least_squares(cls._calc_residual,
                                              x0, verbose=0,
                                              jac_sparsity=None,
                                              x_scale='jac',
                                              ftol=1e-8,
                                              method='trf',
                                              max_nfev=10,
                                              args=args)
        return cls._Pose_from_params(result.x)

    @classmethod
    def _calc_residual(cls, params, origin: npt.ArrayLike, x_axis: list[npt.ArrayLike], xy_plane: list[npt.ArrayLike]):
        transform = cls._Pose_from_params(params)

        origin_diff = transform.rotate_translate(origin)
        x_axis_diff = map(lambda x: transform.rotate_translate(x), x_axis)
        xy_plane_diff = map(lambda x: transform.rotate_translate(x), xy_plane)

        residual_origin = origin_diff

        # Points on X-axis: ignore X
        x_axis_residual = list(map(lambda x: x[1:3], x_axis_diff))

        # Points in the XY-plane: ignore X and Y
        xy_plane_residual = list(map(lambda x: x[2], xy_plane_diff))

        residual = np.concatenate((np.ravel(residual_origin), np.ravel(x_axis_residual), np.ravel(xy_plane_residual)))
        return residual

    @classmethod
    def _Pose_from_params(cls, params: npt.ArrayLike) -> Pose:
        return Pose.from_rot_vec(R_vec=params[:3], t_vec=params[3:])

    @classmethod
    def _de_flip_transformation(cls, raw_transformation: Pose, x_axis: list[npt.ArrayLike],
                                bs_poses: dict[int, Pose]) -> Pose:
        """
        Investigats a transformation and flips it if needed. This method assumes that
        1. all base stations are at Z>0
        2. x_axis samples are taken at X>0
        """
        transformation = raw_transformation

        # X-axis poses should be on the positivie X-axis, check that the "mean" of the x-axis points ends up at X>0
        x_axis_mean = np.mean(x_axis, axis=0)
        if raw_transformation.rotate_translate(x_axis_mean)[0] < 0.0:
            flip_around_z_axis = Pose.from_rot_vec(R_vec=(0.0, 0.0, np.pi))
            transformation = flip_around_z_axis.rotate_translate_pose(transformation)

        # Base station poses should be above the floor, check the first one
        bs_pose = list(bs_poses.values())[0]
        if raw_transformation.rotate_translate(bs_pose.translation)[2] < 0.0:
            flip_around_x_axis = Pose.from_rot_vec(R_vec=(np.pi, 0.0, 0.0))
            transformation = flip_around_x_axis.rotate_translate_pose(transformation)

        return transformation
