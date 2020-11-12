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
Example of how to write to the Lighthouse base station geometry memory in a
Crazyflie
"""
import logging
import time

import cflib.crtp  # noqa
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.mem import LighthouseBsCalibration
from cflib.crazyflie.mem import LighthouseBsGeometry
from cflib.crazyflie.mem import MemoryElement
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
# Only output errors from the logging framework

logging.basicConfig(level=logging.ERROR)


class WriteMem:
    def __init__(self, uri, bs1geo, bs2geo, bs1calib, bs2calib):
        self.data_written = False

        with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
            mems = scf.cf.mem.get_mems(MemoryElement.TYPE_LH)

            count = len(mems)
            if count != 1:
                raise Exception('Unexpected nr of memories found:', count)

            mems[0].geometry_data = [bs1geo, bs2geo]
            mems[0].calibration_data = [bs1calib, bs2calib]

            print('Writing data')
            mems[0].write_geo_data(self._data_written)

            while not self.data_written:
                time.sleep(1)

            self.data_written = False
            mems[0].write_calib_data(
                bs1calib, 0, self._data_written,
                write_failed_cb=self._data_failed)

            while not self.data_written:
                time.sleep(1)

            self.data_written = False
            mems[0].write_calib_data(
                bs2calib, 1, self._data_written,
                write_failed_cb=self._data_failed)

            while not self.data_written:
                time.sleep(1)

    def _data_written(self, mem, addr):
        self.data_written = True
        print('Data written')

    def _data_failed(self, mem, addr):
        print('Data failed')
        raise Exception()


if __name__ == '__main__':
    # URI to the Crazyflie to connect to
    uri = 'radio://0/80/2M/'

    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    bs1geo = LighthouseBsGeometry()
    bs1geo.origin = [1.0, 2.0, 3.0]
    bs1geo.rotation_matrix = [
        [4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0],
        [10.0, 11.0, 12.0],
    ]

    bs2geo = LighthouseBsGeometry()
    bs2geo.origin = [21.0, 22.0, 23.0]
    bs2geo.rotation_matrix = [
        [24.0, 25.0, 26.0],
        [27.0, 28.0, 29.0],
        [30.0, 31.0, 32.0],
    ]

    bs1calib = LighthouseBsCalibration()
    bs1calib.sweeps[0].phase = 1.0
    bs1calib.sweeps[0].tilt = 2.0
    bs1calib.sweeps[0].curve = 3.0
    bs1calib.sweeps[0].gibmag = 4.0
    bs1calib.sweeps[0].gibphase = 5.0
    bs1calib.sweeps[0].ogeemag = 6.0
    bs1calib.sweeps[0].ogeephase = 7.0
    bs1calib.sweeps[1].phase = 1.1
    bs1calib.sweeps[1].tilt = 2.1
    bs1calib.sweeps[1].curve = 3.1
    bs1calib.sweeps[1].gibmag = 4.1
    bs1calib.sweeps[1].gibphase = 5.1
    bs1calib.sweeps[1].ogeemag = 6.1
    bs1calib.sweeps[1].ogeephase = 7.1
    bs1calib.is_valid = True

    bs2calib = LighthouseBsCalibration()
    bs2calib.sweeps[0].phase = 1.5
    bs2calib.sweeps[0].tilt = 2.5
    bs2calib.sweeps[0].curve = 3.5
    bs2calib.sweeps[0].gibmag = 4.5
    bs2calib.sweeps[0].gibphase = 5.5
    bs2calib.sweeps[0].ogeemag = 6.5
    bs2calib.sweeps[0].ogeephase = 7.5
    bs2calib.sweeps[1].phase = 1.51
    bs2calib.sweeps[1].tilt = 2.51
    bs2calib.sweeps[1].curve = 3.51
    bs2calib.sweeps[1].gibmag = 4.51
    bs2calib.sweeps[1].gibphase = 5.51
    bs2calib.sweeps[1].ogeemag = 6.51
    bs2calib.sweeps[1].ogeephase = 7.51
    bs2calib.is_valid = True

    WriteMem(uri, bs1geo, bs2geo, bs1calib, bs2calib)
