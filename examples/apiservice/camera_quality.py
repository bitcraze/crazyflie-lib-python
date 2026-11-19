# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2026 Bitcraze AB
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
Set the Camera Deck's maximum JPEG quality, then read the quality it uses.

The Camera Deck is reached through the Crazyflie as the API Service endpoint
"deck:bcCam". Change the URI below, or set the CFLIB_URI environment variable.
"""
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.apiservice import ValueType
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

cflib.crtp.init_drivers()

with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
    camera = scf.cf.apiservice.endpoint('deck:bcCam')

    # Integers need their wire type: the deck stores this one as a u8.
    camera.set('stream.max_mjpeg_quality', 80, ValueType.U8)

    print('max quality:', camera.get('stream.max_mjpeg_quality'))
    print('quality:', camera.get('stream.mjpeg_quality'))
