# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2025 Bitcraze AB
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
Functionality to get user input by shaking the Crazyflie.
"""
import time

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig


class UserActionDetector:
    """ This class is used as an user interface that lets the user trigger an event by using the Crazyflie as the
    input device. The class listens to the z component of the gyro and detects a quick left or right rotation followed
    by period of no motion. If such a sequence is detected, it calls the callback function provided in the constructor.
    """

    def __init__(self, cf: Crazyflie, cb=None):
        self._is_active = False
        self._reset()
        self._cf = cf
        self._cb = cb
        self._lg_config = None

        self.left_event_threshold_time = 0.0
        self.left_event_time = 0.0
        self.right_event_threshold_time = 0.0
        self.right_event_time = 0
        self.still_event_threshold_time = 0.0
        self.still_event_time = 0.0

    def start(self):
        if not self._is_active:
            self._is_active = True
            self._reset()
            self._cf.disconnected.add_callback(self.stop)

            self._lg_config = LogConfig(name='lighthouse_geo_estimator', period_in_ms=25)
            self._lg_config.add_variable('gyro.z', 'float')
            self._cf.log.add_config(self._lg_config)
            self._lg_config.data_received_cb.add_callback(self._log_callback)
            self._lg_config.start()

    def stop(self):
        if self._is_active:
            if self._lg_config is not None:
                self._lg_config.stop()
                self._lg_config.delete()
                self._lg_config.data_received_cb.remove_callback(self._log_callback)
                self._lg_config = None
            self._cf.disconnected.remove_callback(self.stop)
            self._is_active = False

    def _log_callback(self, ts, data, logblock):
        if self._is_active:
            gyro_z = data['gyro.z']
            self.process_rot(gyro_z)

    def _reset(self):
        self.left_event_threshold_time = 0.0
        self.left_event_time = 0.0

        self.right_event_threshold_time = 0.0
        self.right_event_time = 0

        self.still_event_threshold_time = 0.0
        self.still_event_time = 0.0

    def process_rot(self, gyro_z):
        now = time.time()

        MAX_DURATION_OF_EVENT_PEEK = 0.1
        MIN_DURATION_OF_STILL_EVENT = 0.5
        MAX_TIME_BETWEEN_LEFT_RIGHT_EVENTS = 0.3
        MAX_TIME_BETWEEN_FIRST_ROTATION_AND_STILL_EVENT = 1.0

        if gyro_z > 0:
            self.left_event_threshold_time = now
        if gyro_z < -300 and now - self.left_event_threshold_time < MAX_DURATION_OF_EVENT_PEEK:
            self.left_event_time = now

        if gyro_z < 0:
            self.right_event_threshold_time = now
        if gyro_z > 300 and now - self.right_event_threshold_time < MAX_DURATION_OF_EVENT_PEEK:
            self.right_event_time = now

        if abs(gyro_z) > 50:
            self.still_event_threshold_time = now
        if abs(gyro_z) < 30 and now - self.still_event_threshold_time > MIN_DURATION_OF_STILL_EVENT:
            self.still_event_time = now

        dt_left_right = self.left_event_time - self.right_event_time
        first_left_right = min(self.left_event_time, self.right_event_time)
        dt_first_still = self.still_event_time - first_left_right

        if self.left_event_time > 0 and self.right_event_time > 0 and self.still_event_time > 0:
            if (abs(dt_left_right) < MAX_TIME_BETWEEN_LEFT_RIGHT_EVENTS and
                dt_first_still > 0 and
                    dt_first_still < MAX_TIME_BETWEEN_FIRST_ROTATION_AND_STILL_EVENT):
                self._reset()
                if self._cb is not None:
                    self._cb()
