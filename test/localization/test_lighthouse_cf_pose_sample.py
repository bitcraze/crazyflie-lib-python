# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2025 Bitcraze AB
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
import yaml
from cflib.localization.lighthouse_bs_vector import LighthouseBsVectors
from cflib.localization.lighthouse_bs_vector import LighthouseBsVector
from cflib.localization.lighthouse_cf_pose_sample import LhCfPoseSample
from test.localization.lighthouse_test_base import LighthouseTestBase


class TestLhCfPoseSample(LighthouseTestBase):
    def setUp(self):
        self.vec1 = LighthouseBsVector(0.0, 1.0)
        self.vec2 = LighthouseBsVector(0.1, 1.1)
        self.vec3 = LighthouseBsVector(0.2, 1.2)
        self.vec4 = LighthouseBsVector(0.3, 1.3)

        self.sample1 = LhCfPoseSample({})
        self.sample2 = LhCfPoseSample({3: LighthouseBsVectors([self.vec1, self.vec2, self.vec3, self.vec4])})
        self.sample3 = LhCfPoseSample({3: LighthouseBsVectors([self.vec4, self.vec3, self.vec2, self.vec1])})
        self.sample4 = LhCfPoseSample({3: LighthouseBsVectors([self.vec4, self.vec3, self.vec2, self.vec1])})

    def test_equality(self):
        # Fixture
        # Test
        # Assert
        self.assertEqual(self.sample3, self.sample4)
        self.assertNotEqual(self.sample1, self.sample4)
        self.assertNotEqual(self.sample2, self.sample4)

    def test_yaml(self):
        # Fixture
        expected = self.sample3

        # Test
        yaml_str = yaml.dump(expected)
        actual = yaml.load(yaml_str, Loader=yaml.FullLoader)

        # Assert
        self.assertTrue(yaml_str.startswith('!LhCfPoseSample'))
        self.assertEqual(expected, actual)
