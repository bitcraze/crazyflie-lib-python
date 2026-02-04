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
from test.localization.lighthouse_test_base import LighthouseTestBase

import numpy as np
import yaml

from cflib.localization.lighthouse_types import Pose


class TestLighthouseTypes(LighthouseTestBase):
    def setUp(self):
        pass

    def test_default_matrix_constructor(self):
        # Fixture
        # Test
        actual = Pose()

        # Assert
        self.assertEqual(0.0, np.linalg.norm(actual.translation))
        self.assertEqual(0.0, np.linalg.norm(actual.rot_matrix - np.identity(3)))

    def test_default_rot_vec_constructor(self):
        # Fixture
        # Test
        actual = Pose.from_rot_vec()

        # Assert
        self.assertEqual(0.0, np.linalg.norm(actual.translation))
        self.assertEqual(0.0, np.linalg.norm(actual.rot_matrix - np.identity(3)))

    def test_rotate_translate(self):
        # Fixture
        transform = Pose.from_rot_vec(R_vec=(0.0, 0.0, np.pi / 2), t_vec=(1.0, 0.0, 0.0))
        point = (2.0, 0.0, 0.0)

        # Test
        actual = transform.rotate_translate(point)

        # Assert
        self.assertAlmostEqual(1.0, actual[0])
        self.assertAlmostEqual(2.0, actual[1])
        self.assertAlmostEqual(0.0, actual[2])

    def test_rotate_translate_and_back(self):
        # Fixture
        transform = Pose.from_rot_vec(R_vec=(1.0, 2.0, 3.0), t_vec=(0.1, 0.2, 0.3))
        expected = (2.0, 3.0, 4.0)

        # Test
        actual = transform.inv_rotate_translate(transform.rotate_translate(expected))

        # Assert
        self.assertAlmostEqual(expected[0], actual[0])
        self.assertAlmostEqual(expected[1], actual[1])
        self.assertAlmostEqual(expected[2], actual[2])

    def test_rotate_translate_pose(self):
        # Fixture
        transform = Pose.from_rot_vec(R_vec=(0.0, 0.0, np.pi / 2), t_vec=(1.0, 0.0, 0.0))
        pose = Pose(t_vec=(2.0, 0.0, 0.0))
        expected = Pose.from_rot_vec(R_vec=(0.0, 0.0, np.pi / 2), t_vec=(1.0, 2.0, 0.0))

        # Test
        actual = transform.rotate_translate_pose(pose)

        # Assert
        self.assertPosesAlmostEqual(expected, actual)

    def test_rotate_translate_pose_and_back(self):
        # Fixture
        transform = Pose.from_rot_vec(R_vec=(1.0, 2.0, 3.0), t_vec=(0.1, 0.2, 0.3))
        expected = Pose(t_vec=(2.0, 3.0, 4.0))

        # Test
        actual = transform.inv_rotate_translate_pose(transform.rotate_translate_pose(expected))

        # Assert
        self.assertPosesAlmostEqual(expected, actual)

    def test_pose_equality(self):
        # Fixture
        pose1 = Pose.from_rot_vec(R_vec=(1.0, 2.0, 3.0), t_vec=(0.1, 0.2, 0.3))
        pose2 = Pose.from_rot_vec(R_vec=(1.0, 2.0, 3.0), t_vec=(0.1, 0.2, 0.3))
        pose3 = Pose.from_rot_vec(R_vec=(4.0, 5.0, 6.0), t_vec=(7.0, 8.0, 9.0))

        # Test
        # Assert
        self.assertEqual(pose1, pose2)
        self.assertNotEqual(pose1, pose3)

    def test_pose_yaml(self):
        # Fixture
        expected = Pose.from_rot_vec(R_vec=(1.0, 2.0, 3.0), t_vec=(0.1, 0.2, 0.3))

        # Test
        yaml_str = yaml.dump(expected)
        actual = yaml.load(yaml_str, Loader=yaml.FullLoader)

        # Assert
        self.assertTrue(yaml_str.startswith('!Pose'))
        self.assertEqual(expected, actual)

    def test_cf_rpy_and_back(self):
        # Fixture
        expected = (37.0, -22.0, 100.0)

        # Test
        actual = Pose.from_cf_rpy(roll=37.0, pitch=-22.0, yaw=100.0).rot_cf_rpy

        # Assert
        self.assertAlmostEqual(expected[0], actual[0])
        self.assertAlmostEqual(expected[1], actual[1])
        self.assertAlmostEqual(expected[2], actual[2])
