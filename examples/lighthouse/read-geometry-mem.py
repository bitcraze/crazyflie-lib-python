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
Example of how to read the Lighthouse base station geometry memory from a
Crazyflie
"""
import logging
import time

import cflib.crtp  # noqa
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.mem import MemoryElement
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
# Only output errors from the logging framework

logging.basicConfig(level=logging.ERROR)


class ReadMem:
    def __init__(self, uri):
        self.got_data = False

        with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
            mems = scf.cf.mem.get_mems(MemoryElement.TYPE_LH)

            count = len(mems)
            if count != 1:
                raise Exception('Unexpected nr of memories found:', count)

            print('Requesting data')
            mems[0].update(self._data_updated)

            while not self.got_data:
                time.sleep(1)

    def _data_updated(self, mem):
        mem.dump()
        self.got_data = True


if __name__ == '__main__':
    # URI to the Crazyflie to connect to
    uri = 'radio://0/80/2M'

    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    ReadMem(uri)
