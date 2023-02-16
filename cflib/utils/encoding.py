#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2020 Bitcraze AB
#
#  Crazyflie Nano Quadcopter Client
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

from math import sqrt
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



# compress a quaternion, see quatcompress.h in firmware
# input: q = [x,y,z,w], output: 32-bit number
def compress_quaternion(qx, qy, qz, qw):

    q = [qx, qy, qz, qw]

    i_largest = 0
    for i in range(1, 4):
        if abs(q[i]) > abs(q[i_largest]):
            i_largest = i
    
    negate = q[i_largest] < 0

    comp = i_largest
    m_sqrt_2 = 1.0 / sqrt(2)

    for i in range(0,4):
        if i != i_largest:
            negbit = (q[i] < 0) ^ negate
            mag = ((1 << 9) - 1) * (abs(q[i]) / m_sqrt_2) * 0.5
            comp = (comp << 10) | (negbit << 9) | int(mag)

    return comp
