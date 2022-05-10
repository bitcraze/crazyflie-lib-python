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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
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
from cflib.utils import uri_helper

# URI to the Crazyflie to connect to
URI = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

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
        cf.param.set_value('ring.fadeColor', int('0000A0', 16))
        time.sleep(1)
        cf.param.set_value('ring.fadeColor', int('00A000', 16))
        time.sleep(1)
        cf.param.set_value('ring.fadeColor', int('A00000', 16))
        time.sleep(1)
