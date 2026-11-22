# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2023-2026 Bitcraze AB
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
import math
import struct
import unittest

import numpy as np

from cflib.utils.encoding import compress_quaternion
from cflib.utils.encoding import decompress_quaternion
from cflib.utils.encoding import fp16_to_float


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

    def test_fp16_to_float_matches_ieee_half(self):
        # Fixture
        for bits in range(0x10000):
            expected = struct.unpack('<e', struct.pack('<H', bits))[0]

            # Test
            actual = fp16_to_float(bits)

            # Assert
            if math.isnan(expected):
                self.assertTrue(math.isnan(actual), hex(bits))
            else:
                self.assertEqual(expected, actual, hex(bits))
                self.assertEqual(math.copysign(1.0, expected), math.copysign(1.0, actual), hex(bits))

    def test_fp16_to_float_signed_input(self):
        # Fixture
        # The lighthouse angle stream unpacks the fp16 fields with 'h'
        negative_zero = struct.unpack('<h', struct.pack('<H', 0x8000))[0]
        negative_inf = struct.unpack('<h', struct.pack('<H', 0xfc00))[0]

        # Test
        # Assert
        self.assertEqual(0.0, fp16_to_float(negative_zero))
        self.assertEqual(-1.0, math.copysign(1.0, fp16_to_float(negative_zero)))
        self.assertEqual(-math.inf, fp16_to_float(negative_inf))

    def _normalize_quat(self, quat):
        quat = np.array(quat)
        return quat / np.linalg.norm(quat)
