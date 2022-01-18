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

from cflib.localization import LighthouseBsGeoEstimator


class TestLighthouseBsGeoEstimator(unittest.TestCase):
    def setUp(self):

        self.sut = LighthouseBsGeoEstimator()

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
