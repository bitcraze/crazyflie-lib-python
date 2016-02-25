#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2013 Bitcraze AB
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
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
"""
An early serial link driver. This could still be used (after some fixing) to
run high-speed CRTP with the Crazyflie. The UART can be run at 2Mbit.
"""
import re

from .crtpdriver import CRTPDriver
from .exceptions import WrongUriType

__author__ = 'Bitcraze AB'
__all__ = ['SerialDriver']


class SerialDriver(CRTPDriver):

    def __init__(self):
        None

    def connect(self, uri, linkQualityCallback, linkErrorCallback):
        # check if the URI is a serial URI
        if not re.search('^serial://', uri):
            raise WrongUriType('Not a serial URI')

        # Check if it is a valid serial URI
        uriRe = re.search('^serial://([a-z A-Z 0-9]+)/?([0-9]+)?$', uri)
        if not uriRe:
            raise Exception('Invalid serial URI')

    def get_name(self):
        return 'serial'

    def scan_interface(self, address):
        return []
