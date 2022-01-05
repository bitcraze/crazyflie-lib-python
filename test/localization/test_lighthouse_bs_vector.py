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
from test.localization.lighthouse_test_base import LighthouseTestBase

import numpy as np

from cflib.localization import LighthouseBsVector
from cflib.localization.lighthouse_bs_vector import LighthouseBsVectors


class TestLighthouseBsVector(LighthouseTestBase):
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

    def test_conversion_to_from_projection(self):
        # Fixture
        horiz = 0.123
        vert = 0.456
        v1 = LighthouseBsVector(horiz, vert)

        # Test
        actual = LighthouseBsVector.from_projection(v1.projection)

        # Assert
        self.assertAlmostEqual(horiz, actual.lh_v1_horiz_angle)
        self.assertAlmostEqual(vert, actual.lh_v1_vert_angle)

    def test_conversion_to_projection_pair_list(self):
        # Fixture
        vectors = LighthouseBsVectors((
            LighthouseBsVector(0.0, 0.0),
            LighthouseBsVector(0.1, 0.1),
            LighthouseBsVector(0.2, 0.2),
            LighthouseBsVector(0.3, 0.3),
        ))

        # Test
        actual = vectors.projection_pair_list()

        # Assert
        self.assertEqual(len(vectors), len(actual))
        self.assertListEqual(vectors[0].projection.tolist(), actual[0].tolist())
        self.assertListEqual(vectors[3].projection.tolist(), actual[3].tolist())

    def test_conversion_to_angle_list(self):
        # Fixture
        vectors = LighthouseBsVectors((
            LighthouseBsVector(0.0, 0.1),
            LighthouseBsVector(0.2, 0.3),
            LighthouseBsVector(0.4, 0.5),
            LighthouseBsVector(0.6, 0.7),
        ))

        # Test
        actual = vectors.angle_list()

        # Assert
        self.assertVectorsAlmostEqual((0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7), actual)
