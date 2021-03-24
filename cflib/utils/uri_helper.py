#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2021 Bitcraze AB
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
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
import os
import sys


def uri_from_env(env='CFLIB_URI', default='radio://0/80/2M/E7E7E7E7E7') -> str:
    try:
        return os.environ[env]
    except KeyError:
        return default


def address_from_env(env='CFLIB_URI', default=0xE7E7E7E7E7) -> int:
    try:
        uri = os.environ[env]
    except KeyError:
        return default

    # Get the address part of the uri
    address = uri.rsplit('/', 1)[-1]
    try:
        return int(address, 16)
    except ValueError:
        print('address is not hexadecimal! (%s)' % address, file=sys.stderr)
        return None
