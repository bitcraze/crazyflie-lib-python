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
from test.localization.lighthouse_fixtures import LighthouseFixtures
from test.localization.lighthouse_test_base import LighthouseTestBase

import numpy as np

from cflib.localization.ippe_cf import IppeCf
from cflib.localization.lighthouse_types import LhDeck4SensorPositions
from cflib.localization.lighthouse_types import Pose


class TestIppeCf(LighthouseTestBase):
    def setUp(self):
        self.fixtures = LighthouseFixtures()

    def test_that_pose_is_found(self):
        # Fixture
        pose_bs = Pose(t_vec=(0.0, 0.0, 0.0))
        pose_cf = Pose(t_vec=(1.0, 0.0, -1.0))

        U = LhDeck4SensorPositions.positions
        Q = self.fixtures.synthesize_angles(pose_cf, pose_bs).projection_pair_list()

        # The CF pose seen from the base station
        expected_0 = pose_cf

        # Not sure if (why) this is the expected mirror solution
        expected_1 = Pose.from_rot_vec(R_vec=(0.0, -np.pi / 2, 0.0), t_vec=pose_cf.translation)

        # Test
        actual = IppeCf.solve(U, Q)

        # Assert
        actual_pose_0 = Pose(actual[0].R, actual[0].t)
        self.assertPosesAlmostEqual(expected_0, actual_pose_0, places=3)

        actual_pose_1 = Pose(actual[1].R, actual[1].t)
        self.assertPosesAlmostEqual(expected_1, actual_pose_1, places=3)
