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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
Example of how to read the memory from the multiranger
"""
import logging
import time
from threading import Event

import matplotlib.pyplot as plt

import cflib.crtp  # noqa
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.mem import MemoryElement
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


class ReadMem:
    def __init__(self, uri):
        self._event = Event()
        self._cf = Crazyflie(rw_cache='./cache')

        with SyncCrazyflie(uri, cf=self._cf) as scf:
            mems = scf.cf.mem.get_mems(MemoryElement.TYPE_DECK_PAA3905)

            count = len(mems)
            if count != 1:
                raise Exception('Unexpected nr of memories found:', count)

            mem = mems[0]

            data = [[0 for x in range(35)] for y in range(35)]
            im = plt.imshow(data, cmap='gray', vmin=0, vmax=255, origin='upper')

            start_time = time.time()
            for frames in range(100):
                data = mem.read_data_sync()
                im.set_data(data)
                plt.pause(0.01)

            end_time = time.time()
            print('FPS: {}'.format(100/(end_time - start_time)))
            time.sleep(5)


if __name__ == '__main__':
    # URI to the Crazyflie to connect to
    #    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')
    uri = uri_helper.uri_from_env(default='usb://0')

    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    rm = ReadMem(uri)
