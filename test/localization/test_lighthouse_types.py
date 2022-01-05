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
import unittest

import numpy as np

from cflib.localization.lighthouse_types import Pose


class TestLighthouseTypes(unittest.TestCase):
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
        pose = Pose.from_rot_vec(R_vec=(0.0, 0.0, np.pi / 2), t_vec=(1.0, 0.0, 0.0))
        point = (2.0, 0.0, 0.0)

        # Test
        actual = pose.rotate_translate(point)

        # Assert
        self.assertAlmostEqual(1.0, actual[0])
        self.assertAlmostEqual(2.0, actual[1])
        self.assertAlmostEqual(0.0, actual[2])

    def test_rotate_translate_and_back(self):
        # Fixture
        pose = Pose.from_rot_vec(R_vec=(1.0, 2.0, 3.0), t_vec=(0.1, 0.2, 0.3))
        expected = (2.0, 3.0, 4.0)

        # Test
        actual = pose.inv_rotate_translate(pose.rotate_translate(expected))

        # Assert
        self.assertAlmostEqual(expected[0], actual[0])
        self.assertAlmostEqual(expected[1], actual[1])
        self.assertAlmostEqual(expected[2], actual[2])
