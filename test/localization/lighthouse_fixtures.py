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
import numpy as np

from cflib.localization.lighthouse_bs_vector import LighthouseBsVector
from cflib.localization.lighthouse_bs_vector import LighthouseBsVectors
from cflib.localization.lighthouse_types import LhDeck4SensorPositions
from cflib.localization.lighthouse_types import Pose


class LighthouseFixtures:
    """
    Fixtures to be used in lighthouse unit tests
    """

    # Stock objects
    # BS0 is pointing along the X-axis
    BS0_POSE = Pose(t_vec=(-2.0, 1.0, 3.0))
    # BS1 is pointing along the Y-axis
    BS1_POSE = Pose.from_rot_vec(R_vec=(0.0, 0.0, np.pi / 2), t_vec=(0.0, -2.0, 3.0))
    # BS2 is pointing along the negative Y-axis
    BS2_POSE = Pose.from_rot_vec(R_vec=(0.0, 0.0, -np.pi / 2), t_vec=(0.0, 2.0, 3.0))
    # BS3 is pointing along the negative X-axis
    BS3_POSE = Pose.from_rot_vec(R_vec=(0.0, 0.0, np.pi), t_vec=(2.0, 0.0, 2.0))

    # CF_ORIGIN is in the origin, pointing along the X-axis
    CF_ORIGIN_POSE = Pose()

    # CF1 is pointing along the X-axis
    CF1_POSE = Pose(t_vec=(0.3, 0.2, 0.1))

    # CF2 is pointing along the Y-axis
    CF2_POSE = Pose.from_rot_vec(R_vec=(0.0, 0.0, np.pi / 2), t_vec=(1.0, 0.0, 0.0))

    def __init__(self) -> None:
        self.angles_cf_origin_bs0 = self.synthesize_angles(self.CF_ORIGIN_POSE, self.BS0_POSE)
        self.angles_cf_origin_bs1 = self.synthesize_angles(self.CF_ORIGIN_POSE, self.BS1_POSE)

        self.angles_cf1_bs1 = self.synthesize_angles(self.CF1_POSE, self.BS1_POSE)
        self.angles_cf1_bs2 = self.synthesize_angles(self.CF1_POSE, self.BS2_POSE)

        self.angles_cf2_bs0 = self.synthesize_angles(self.CF2_POSE, self.BS0_POSE)
        self.angles_cf2_bs1 = self.synthesize_angles(self.CF2_POSE, self.BS1_POSE)
        self.angles_cf2_bs2 = self.synthesize_angles(self.CF2_POSE, self.BS2_POSE)
        self.angles_cf2_bs3 = self.synthesize_angles(self.CF2_POSE, self.BS3_POSE)

    def synthesize_angles(self, pose_cf: Pose, pose_bs: Pose) -> LighthouseBsVectors:
        """
        Genereate a LighthouseBsVectors object based
        """

        result = LighthouseBsVectors()
        for sens_pos_ref_cf in LhDeck4SensorPositions.positions:
            sens_pos_ref_global = pose_cf.rotate_translate(sens_pos_ref_cf)
            sens_pos_ref_bs = pose_bs.inv_rotate_translate(sens_pos_ref_global)
            result.append(LighthouseBsVector.from_cart(sens_pos_ref_bs))
        return result
