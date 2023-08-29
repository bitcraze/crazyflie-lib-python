#!/usr/bin/env python
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
import struct

import numpy as np


# Code from davidejones at https://gamedev.stackexchange.com/a/28756
def fp16_to_float(float16):
    s = int((float16 >> 15) & 0x00000001)    # sign
    e = int((float16 >> 10) & 0x0000001f)    # exponent
    f = int(float16 & 0x000003ff)            # fraction

    if e == 0:
        if f == 0:
            return int(s << 31)
        else:
            while not (f & 0x00000400):
                f <<= 1
                e -= 1
            e += 1
            f &= ~0x00000400
            # print(s,e,f)
    elif e == 31:
        if f == 0:
            return int((s << 31) | 0x7f800000)
        else:
            return int((s << 31) | 0x7f800000 | (f << 13))

    e += 127 - 15
    f <<= 13
    result = int((s << 31) | (e << 23) | f)
    return struct.unpack('f', struct.pack('I', result))[0]


def decompress_quaternion(comp):
    """Decompress a quaternion

    see quatcompress.h in the firmware for definitions

    Args:
        comp int: A 32-bit number

    Returns:
        np array: q = [x, y, z, w]
    """
    q = np.zeros(4)
    mask = (1 << 9) - 1
    i_largest = comp >> 30
    sum_squares = 0
    for i in range(3, -1, -1):
        if i != i_largest:
            mag = comp & mask
            negbit = (comp >> 9) & 0x1
            comp = comp >> 10
            q[i] = mag / mask / np.sqrt(2)
            if negbit == 1:
                q[i] = -q[i]
            sum_squares += q[i] * q[i]
    q[i_largest] = np.sqrt(1.0 - sum_squares)
    return q


def compress_quaternion(quat):
    """Compress a quaternion.
    assumes input quaternion is normalized. will fail if not.

    see quatcompress.h in firmware the for definitions

    Args:
        quat : An array of floats representing a quaternion [x, y, z, w]

    Returns: 32-bit integer
    """
    # Normalize the quaternion
    quat_n = np.array(quat) / np.linalg.norm(quat)

    i_largest = 0
    for i in range(1, 4):
        if abs(quat_n[i]) > abs(quat_n[i_largest]):
            i_largest = i
    negate = quat_n[i_largest] < 0

    M_SQRT1_2 = 1.0 / np.sqrt(2)

    comp = i_largest
    for i in range(4):
        if i != i_largest:
            negbit = int((quat_n[i] < 0) ^ negate)
            mag = int(((1 << 9) - 1) * (abs(quat_n[i]) / M_SQRT1_2) + 0.5)
            comp = (comp << 10) | (negbit << 9) | mag

    return comp
