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

from cflib.localization.lighthouse_bs_vector import LighthouseBsVector
from cflib.localization.lighthouse_sample_matcher import LighthouseSampleMatcher
from cflib.localization.lighthouse_types import LhMeasurement


class TestLighthouseSampleMatcher(unittest.TestCase):
    def setUp(self):
        self.vec0 = LighthouseBsVector(0.0, 0.0)
        self.vec1 = LighthouseBsVector(0.1, 0.1)
        self.vec2 = LighthouseBsVector(0.2, 0.2)
        self.vec3 = LighthouseBsVector(0.3, 0.3)

        self.samples = [
            LhMeasurement(timestamp=1.000, base_station_id=0, angles=self.vec0),
            LhMeasurement(timestamp=1.015, base_station_id=1, angles=self.vec1),
            LhMeasurement(timestamp=1.020, base_station_id=0, angles=self.vec2),
            LhMeasurement(timestamp=1.035, base_station_id=1, angles=self.vec3),
        ]

    def test_that_samples_are_aggregated(self):
        # Fixture

        # Test
        actual = LighthouseSampleMatcher.match(self.samples, max_time_diff=0.010)

        # Assert
        self.assertEqual(1.000, actual[0].timestamp)
        self.assertEqual(1, len(actual[0].angles_calibrated))
        self.assertEqual(self.vec0, actual[0].angles_calibrated[0])

        self.assertEqual(1.015, actual[1].timestamp)
        self.assertEqual(2, len(actual[1].angles_calibrated))
        self.assertEqual(self.vec1, actual[1].angles_calibrated[1])
        self.assertEqual(self.vec2, actual[1].angles_calibrated[0])

        self.assertEqual(1.035, actual[2].timestamp)
        self.assertEqual(1, len(actual[2].angles_calibrated))
        self.assertEqual(self.vec3, actual[2].angles_calibrated[1])

    def test_that_single_bs_samples_are_fitered_out(self):
        # Fixture

        # Test
        actual = LighthouseSampleMatcher.match(self.samples, max_time_diff=0.010, min_nr_of_bs_in_match=2)

        # Assert
        self.assertEqual(1.015, actual[0].timestamp)
        self.assertEqual(2, len(actual[0].angles_calibrated))
        self.assertEqual(self.vec1, actual[0].angles_calibrated[1])
        self.assertEqual(self.vec2, actual[0].angles_calibrated[0])

    def test_that_empty_sample_list_works(self):
        # Fixture

        # Test
        actual = LighthouseSampleMatcher.match([])

        # Assert
        self.assertEqual(0, len(actual))
