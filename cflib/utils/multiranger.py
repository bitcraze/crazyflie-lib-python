# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2018 Bitcraze AB
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
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie


class Multiranger:
    FRONT = 'range.front'
    BACK = 'range.back'
    LEFT = 'range.left'
    RIGHT = 'range.right'
    UP = 'range.up'
    DOWN = 'range.zrange'

    def __init__(self, crazyflie, rate_ms=100, zranger=False):
        if isinstance(crazyflie, SyncCrazyflie):
            self._cf = crazyflie.cf
        else:
            self._cf = crazyflie
        self._log_config = self._create_log_config(rate_ms)

        self._up_distance = None
        self._front_distance = None
        self._back_distance = None
        self._left_distance = None
        self._right_distance = None
        self._down_distance = None

    def _create_log_config(self, rate_ms):
        log_config = LogConfig('multiranger', rate_ms)
        log_config.add_variable(self.FRONT)
        log_config.add_variable(self.BACK)
        log_config.add_variable(self.LEFT)
        log_config.add_variable(self.RIGHT)
        log_config.add_variable(self.UP)
        log_config.add_variable(self.DOWN)

        log_config.data_received_cb.add_callback(self._data_received)

        return log_config

    def start(self):
        self._cf.log.add_config(self._log_config)
        self._log_config.start()

    def _convert_log_to_distance(self, data):
        if data >= 8000:
            return None
        else:
            return data / 1000.0

    def _data_received(self, timestamp, data, logconf):
        self._up_distance = self._convert_log_to_distance(data[self.UP])
        self._front_distance = self._convert_log_to_distance(data[self.FRONT])
        self._back_distance = self._convert_log_to_distance(data[self.BACK])
        self._left_distance = self._convert_log_to_distance(data[self.LEFT])
        self._right_distance = self._convert_log_to_distance(data[self.RIGHT])
        if self.DOWN in data:
            self._down_distance = self._convert_log_to_distance(data[self.DOWN]
                                                                )

    def stop(self):
        self._log_config.delete()

    @property
    def up(self):
        return self._up_distance

    @property
    def left(self):
        return self._left_distance

    @property
    def right(self):
        return self._right_distance

    @property
    def front(self):
        return self._front_distance

    @property
    def back(self):
        return self._back_distance

    @property
    def down(self):
        return self._down_distance

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
