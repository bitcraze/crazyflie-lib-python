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
import copy

from cflib.localization.lighthouse_types import Pose


class LighthouseSystemAligner2:
    """This class is used to align a lighthouse system to a few sampled positions"""
    @classmethod
    def align(cls, real: list[npt.ArrayLike], estimated: list[npt.ArrayLike], bss: dict[int, Pose], cfs: list[Pose]) -> tuple[dict[int, Pose], list[Pose]]:
        transform = Pose()

        scale = cls._find_scale(real, estimated)
        print(f"found scale: {scale}")

        scaled_estimated = []
        for pos in estimated:
            scaled_estimated.append(scale * pos)

        transform = cls._find_transformation(real, scaled_estimated)
        print(f"found trans: {transform.translation}")
        print(f"found rot: {transform.rot_vec}")

        transformed_bss = {}
        for id, pose in bss.items():
            scaled_pose = copy.copy(pose)
            scaled_pose.scale(scale)
            transformed_bss[id] = transform.rotate_translate_pose(scaled_pose)

        transformed_cfs = []
        for pose in cfs:
            scaled_pose = copy.copy(pose)
            scaled_pose.scale(scale)
            transformed_cfs.append(transform.rotate_translate_pose(scaled_pose))

        return transformed_bss, transformed_cfs

    @classmethod
    def _find_scale(cls, real: list[npt.ArrayLike], estimated: list[npt.ArrayLike]) -> float:
        scales = []
        for i in range(len(real) - 1):
            real_dist = np.linalg.norm(real[i] - real[i + 1])
            estimate_dist = np.linalg.norm(estimated[i] - estimated[i + 1])
            scale = real_dist / estimate_dist
            scales.append(scale)
        print(f"found partial scales: {scales}")
        return np.mean(scales)

    @classmethod
    def _find_transformation(cls, real: list[npt.ArrayLike], estimated: list[npt.ArrayLike]) -> Pose:
        args = (real, estimated)

        x0 = np.zeros((6))

        result = scipy.optimize.least_squares(cls._calc_residual,
                                              x0, verbose=0,
                                              jac_sparsity=None,
                                              x_scale='jac',
                                              ftol=1e-8,
                                              method='trf',
                                              max_nfev=None,
                                              args=args)
        return cls._Pose_from_params(result.x)

    @classmethod
    def _calc_residual(cls, params, real: list[npt.ArrayLike], estimated: list[npt.ArrayLike]):
        transform = cls._Pose_from_params(params)

        transformed_estimated = map(lambda x: transform.rotate_translate(x), estimated)
        diff = list(map(lambda x, y: x - y, real, transformed_estimated))

        residual = np.ravel(diff)
        return residual

    @classmethod
    def _Pose_from_params(cls, params: npt.ArrayLike) -> Pose:
        return Pose.from_rot_vec(R_vec=params[:3], t_vec=params[3:])




if __name__ == '__main__':

    real = [
        np.array((-3.92, 0.32, 3.10)),
        np.array((3.01, 0.17, 3.10)),
        np.array((-4.95, 11.24, 2.99)),
        np.array((3.45, 14.83, 3.14)),
    ]

    def test1():
        rot = Pose.from_rot_vec(R_vec=np.array((1.0, 2.0, 3.0)), t_vec=np.array((1.0, 2.0, 4.0)))
        scale = 5.123

        measured = list(map(lambda x: rot.inv_rotate_translate(x) * (1.0 / scale), real))

        print(f"real: {real}")
        print(f"measured: {measured}")
        print(f"expected scale: {scale}")
        print(f"expected trans: {rot.translation}")
        print(f"expected rot: {rot.rot_vec}")
        print("-----------------------------")

        cfs = list(map(lambda x: Pose(t_vec=x), measured))

        bs, actual_cfs = LighthouseSystemAligner2.align(
            real,
            measured,
            {},
            cfs
        )

        print("actual_cfs:")
        for cf in actual_cfs:
            print(cf.translation)

    def test2():
        measured = [
            np.array((3.607453217625117, -0.2439291163433713, 2.805806347814388)),
            np.array((-2.73104691814534, -0.328295555207515, 2.8238490326425403)),
            np.array((4.829439906688111, -10.086759204374, 2.6376328979020105)),
            np.array((-2.6380355251782874, -13.594010350495099, 2.739280913376707)),
        ]

        print(f"real: {real}")
        print(f"measured: {measured}")
        print("-----------------------------")

        cfs = list(map(lambda x: Pose(t_vec=x), measured))

        bs, actual_cfs = LighthouseSystemAligner2.align(
            real,
            measured,
            {},
            cfs
        )

        print("actual_cfs:")
        for cf in actual_cfs:
            print(cf.translation)


    test2()
