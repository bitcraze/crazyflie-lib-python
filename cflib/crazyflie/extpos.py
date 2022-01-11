#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2020 Bitcraze AB
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
"""
Used for sending external position to the Crazyflie
"""

__author__ = 'Bitcraze AB'
__all__ = ['Extpos']


class Extpos():
    """
    Used for sending its position to the Crazyflie
    """

    def __init__(self, crazyflie=None):
        """
        Initialize the Extpos object.
        """
        self._cf = crazyflie

    def send_extpos(self, x, y, z):
        """
        Send the current Crazyflie X, Y, Z position. This is going to be
        forwarded to the Crazyflie's position estimator.
        """

        self._cf.loc.send_extpos([x, y, z])

    def send_extpose(self, x, y, z, qx, qy, qz, qw):
        """
        Send the current Crazyflie X, Y, Z position and attitude as a
        normalized quaternion. This is going to be forwarded to the
        Crazyflie's position estimator.
        """
        self._cf.loc.send_extpose([x, y, z], [qx, qy, qz, qw])
