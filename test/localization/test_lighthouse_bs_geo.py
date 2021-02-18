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
import math
import unittest

from cflib.localization import LighthouseBsGeoEstimator
from cflib.localization import LighthouseBsVector


class TestLighthouseBsGeoEstimator(unittest.TestCase):
    def setUp(self):

        self.sut = LighthouseBsGeoEstimator()

    def test_that_initial_yaw_guess_is_correct_ba_is_behind(self):
        # Fixture
        bs_vectors = [
            LighthouseBsVector(1, 0),
            LighthouseBsVector(2, 0),
            LighthouseBsVector(0, 0),
            LighthouseBsVector(3, 0),
        ]

        # Test
        actual = self.sut._find_initial_yaw_guess(bs_vectors)

        # Assert
        self.assertEqual(0.0, actual)

    def test_that_initial_yaw_guess_is_correct_ba_is_front(self):
        # Fixture 1, 3, 2, 0
        bs_vectors = [
            LighthouseBsVector(3, 0),
            LighthouseBsVector(0, 0),
            LighthouseBsVector(2, 0),
            LighthouseBsVector(1, 0),
        ]

        # Test
        actual = self.sut._find_initial_yaw_guess(bs_vectors)

        # Assert
        self.assertEqual(math.radians(180), actual)

    def test_that_initial_yaw_guess_is_correct_bs_left_behind(self):
        # Fixture
        bs_vectors = [
            LighthouseBsVector(1.0, 0),
            LighthouseBsVector(-0.5, 0),
            LighthouseBsVector(0.5, 0),
            LighthouseBsVector(-1.0, 0),
        ]

        # Test
        actual = self.sut._find_initial_yaw_guess(bs_vectors)

        # Assert
        self.assertEqual(math.radians(155), actual)

    def test_that_sanity_check_finds_coordinate_out_of_bounds(self):
        # Fixture
        pos_bs_in_cf_coord = [0, -20, 0]

        # Test
        actual = self.sut.sanity_check_result(pos_bs_in_cf_coord)

        # Assert
        self.assertFalse(actual)

    def test_that_sanity_check_passes_ok_position(self):
        # Fixture
        pos_bs_in_cf_coord = [0, 1, 2]

        # Test
        actual = self.sut.sanity_check_result(pos_bs_in_cf_coord)

        # Assert
        self.assertTrue(actual)
