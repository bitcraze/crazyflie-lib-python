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
This example demonstrate the LEDTIMING led ring sequence memory. This memory and
led-ring effect allows to pre-program a LED sequence to be played autonomously
by the Crazyflie.

Change the URI variable to your Crazyflie configuration.
"""
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.mem import MemoryElement
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

# URI to the Crazyflie to connect to
URI = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        cf = scf.cf

        # Get LED memory and write to it
        mem = cf.mem.get_mems(MemoryElement.TYPE_DRIVER_LEDTIMING)
        if len(mem) > 0:
            mem[0].add(25, {'r': 100, 'g': 0, 'b': 0})
            mem[0].add(0, {'r': 0, 'g': 100, 'b': 0}, leds=1)
            mem[0].add(0, {'r': 0, 'g': 100, 'b': 0}, leds=2)
            mem[0].add(3000, {'r': 0, 'g': 100, 'b': 0}, leds=3, rotate=1)
            mem[0].add(50, {'r': 0, 'g': 0, 'b': 100}, leds=1)
            mem[0].add(25, {'r': 0, 'g': 0, 'b': 100}, leds=0, fade=True)
            mem[0].add(25, {'r': 100, 'g': 0, 'b': 100}, leds=1)
            mem[0].add(25, {'r': 100, 'g': 0, 'b': 0})
            mem[0].add(50, {'r': 100, 'g': 0, 'b': 100})
            mem[0].write_data(None)
        else:
            print('No LED ring present')

        # Set virtual mem effect effect
        cf.param.set_value('ring.effect', '0')
        time.sleep(2)
        cf.param.set_value('ring.effect', '17')
        time.sleep(2)
