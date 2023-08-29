# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2023 Bitcraze AB
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
import unittest

import numpy as np

from cflib.utils.encoding import compress_quaternion
from cflib.utils.encoding import decompress_quaternion


class EncodingTest(unittest.TestCase):

    def test_compress_decompress(self):
        # Fixture
        expected = self._normalize_quat([1, 2, 3, 4])

        # Test
        compressed = compress_quaternion(expected)
        actual = decompress_quaternion(compressed)

        # Assert
        np.testing.assert_allclose(actual, expected, 0.001)

    def test_compress_decompress_not_normalized(self):
        # Fixture
        quat = [1, 2, 3, 4]
        expected = self._normalize_quat(quat)

        # Test
        compressed = compress_quaternion(quat)
        actual = decompress_quaternion(compressed)

        # Assert
        np.testing.assert_allclose(actual, expected, 0.001)

    def test_other_largest_component(self):
        # Fixture
        quat = [5, 10, 3, 4]
        expected = self._normalize_quat(quat)

        # Test
        compressed = compress_quaternion(quat)
        actual = decompress_quaternion(compressed)

        # Assert
        np.testing.assert_allclose(actual, expected, 0.001)

    def _normalize_quat(self, quat):
        quat = np.array(quat)
        return quat / np.linalg.norm(quat)
