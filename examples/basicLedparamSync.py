# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2019 Bitcraze AB
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
Simple example that connects to the crazyflie at `URI` and writes to
parameters that control the LED-ring,
it has been tested with (and designed for) the LED-ring deck.

Change the URI variable to your Crazyflie configuration.
"""
import logging
import time

import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

URI = 'radio://0/80/250K'

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


if __name__ == '__main__':
    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(URI) as scf:
        cf = scf.cf

        # Set solid color effect
        cf.param.set_value('ring.effect', '7')
        # Set the RGB values
        cf.param.set_value('ring.solidRed', '100')
        cf.param.set_value('ring.solidGreen', '0')
        cf.param.set_value('ring.solidBlue', '0')
        time.sleep(2)

        # Set black color effect
        cf.param.set_value('ring.effect', '0')
        time.sleep(1)

        # Set fade to color effect
        cf.param.set_value('ring.effect', '14')
        # Set fade time i seconds
        cf.param.set_value('ring.fadeTime', '1.0')
        # Set the RGB values in one uint32 0xRRGGBB
        cf.param.set_value('ring.fadeColor', '0x0000A0')
        time.sleep(1)
        cf.param.set_value('ring.fadeColor', '0x00A000')
        time.sleep(1)
        cf.param.set_value('ring.fadeColor', '0xA00000')
        time.sleep(1)
