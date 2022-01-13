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

from collections import namedtuple

import numpy as np
import numpy.typing as npt

from ._ippe import mat_run


class IppeCf:
    """
    A wrapper class to simplify usage of IPPE in CF code.
    Converts between CF style of coordinate systems/data structures and
    IPPE (Open CV) style.
    """

    # Rotation matrix to transform from IPPE to CF
    _R_ippe_to_cf = np.array([
        [0.0, 0.0, 1.0],
        [-1.0, 0.0, 0.0],
        [0.0, -1.0, 0.0],
    ])

    # Rotation matrix to transform from CF to IPPE
    _R_cf_to_ippe = np.transpose(_R_ippe_to_cf)

    Solution = namedtuple('Solution', ['R', 't', 'reproj_err'])

    @staticmethod
    def solve(U_cf: npt.ArrayLike, Q_cf: npt.ArrayLike) -> list[Solution]:
        """
        The solution to Perspective IPPE with point correspondences computed
        between points in world coordinates on the plane z=0, and normalised points in the
        camera's image.

        This is a wrapper function to convert from/to CF coordinate system/array style

        :param U_cf: Nx3 matrix holding the model points in world coordinates.
        :param Q_cf: Nx2 matrix holding the points in the image. These are in normalised
                     pixel coordinates. That is, the effects of the camera's intrinsic matrix
                     and lens distortion are corrected, so that the Q projects with a perfect
                     pinhole model.

                     First param: Y (positive to the left)
                     Second param: Z (positive up)
        :return: A list that contains 2 sets of pose solution from IPPE including rotation matrix
                 translation matrix, and reprojection error. The first solution in the list has
                 the smallest reprojection error.
        """

        U, Q = IppeCf._cf_to_ippe(U_cf, Q_cf)
        solutions = mat_run(U, Q)
        return IppeCf._ippe_to_cf(solutions)

    @staticmethod
    def _cf_to_ippe(U_cf, Q_cf):
        modelDims = U_cf.shape[0]
        U_t = np.zeros_like(U_cf, dtype=float)
        Q_t = np.zeros_like(Q_cf, dtype=float)
        for i in range(modelDims):
            U_t[i] = IppeCf._rotate_vector_to_ippe(U_cf[i])
            Q_t[i] = np.array((-Q_cf[i][0], -Q_cf[i][1]))

        U = np.transpose(U_t)
        Q = np.transpose(Q_t)

        return U, Q

    @staticmethod
    def _ippe_to_cf(solutions):
        result = [
            IppeCf.Solution(
                IppeCf._rotate_rot_mat_to_cf(solutions['R1']),
                IppeCf._rotate_vector_to_cf(solutions['t1']),
                solutions['reprojError1']
            ),
            IppeCf.Solution(
                IppeCf._rotate_rot_mat_to_cf(solutions['R2']),
                IppeCf._rotate_vector_to_cf(solutions['t2']),
                solutions['reprojError2']
            )
        ]

        return result

    @staticmethod
    def _rotate_vector_to_ippe(v):
        return np.dot(IppeCf._R_cf_to_ippe, v)

    def _rotate_vector_to_cf(v):
        return np.dot(IppeCf._R_ippe_to_cf, v)

    @staticmethod
    def _rotate_rot_mat_to_cf(R):
        return np.dot(IppeCf._R_ippe_to_cf, np.dot(R, IppeCf._R_cf_to_ippe))
