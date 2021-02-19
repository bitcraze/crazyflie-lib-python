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
import unittest

import numpy as np

from cflib.localization import LighthouseBsVector


class TestLighthouseBsVector(unittest.TestCase):
    def setUp(self):
        pass

    def test_init_from_lh1_angles(self):
        # Fixture
        horiz = 0.123
        vert = -1.23

        # Test
        actual = LighthouseBsVector(horiz, vert)

        # Assert
        self.assertEqual(horiz, actual.lh_v1_horiz_angle)
        self.assertEqual(vert, actual.lh_v1_vert_angle)

    def test_conversion_to_lh2_angles_are_zero_straight_forward(self):
        # Fixture
        horiz = 0
        vert = 0

        # Test
        actual = LighthouseBsVector(horiz, vert)

        # Assert
        self.assertEqual(0.0, actual.lh_v2_angle_1)
        self.assertEqual(0.0, actual.lh_v2_angle_2)

    def test_conversion_to_lh2_angles_are_equal_with_vert_zero(self):
        # Fixture
        horiz = 1.0
        vert = 0.0

        # Test
        actual = LighthouseBsVector(horiz, vert)

        # Assert
        self.assertEqual(actual.lh_v2_angle_1, actual.lh_v2_angle_2)

    def test_conversion_to_from_lh2(self):
        # Fixture
        horiz = 0.123
        vert = -0.987
        v1 = LighthouseBsVector(horiz, vert)

        # Test
        actual = LighthouseBsVector.from_lh2(v1.lh_v2_angle_1, v1.lh_v2_angle_2)

        # Assert
        self.assertAlmostEqual(horiz, actual.lh_v1_horiz_angle)
        self.assertAlmostEqual(vert, actual.lh_v1_vert_angle)

    def test_conversion_to_cartesian_straight_forward(self):
        # Fixture
        horiz = 0.0
        vert = 0.0
        vector = LighthouseBsVector(horiz, vert)

        # Test
        actual = vector.cart

        # Assert
        self.assertAlmostEqual(1.0, actual[0])
        self.assertAlmostEqual(0.0, actual[1])
        self.assertAlmostEqual(0.0, actual[2])

    def test_conversion_to_from_cartesian(self):
        # Fixture
        horiz = 0.123
        vert = -0.987
        v1 = LighthouseBsVector(horiz, vert)

        # Test
        actual = LighthouseBsVector.from_cart(v1.cart)

        # Assert
        self.assertAlmostEqual(horiz, actual.lh_v1_horiz_angle)
        self.assertAlmostEqual(vert, actual.lh_v1_vert_angle)

    def test_cartesian_is_normalized(self):
        # Fixture
        horiz = 0.123
        vert = 0.456
        vector = LighthouseBsVector(horiz, vert)

        # Test
        actual = np.linalg.norm(vector.cart)

        # Assert
        self.assertAlmostEqual(1.0, actual)
