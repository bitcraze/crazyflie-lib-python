# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2016 Bitcraze AB
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
This class provides synchronous access to log data from the Crazyflie.

It acts as an iterator and returns the next value on each iteration.
If no value is available it blocks until log data is available again.
"""
import sys

from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

if sys.version_info < (3,):
    from Queue import Queue
else:
    from queue import Queue


class SyncLogger:
    DISCONNECT_EVENT = 'DISCONNECT_EVENT'

    def __init__(self, crazyflie, log_config):
        """
        Construct an instance of a SyncLogger

        Takes an Crazyflie or SyncCrazyflie instance and a log configuration
        """
        if isinstance(crazyflie, SyncCrazyflie):
            self._cf = crazyflie.cf
        else:
            self._cf = crazyflie

        self._log_config = log_config
        self._cf.log.add_config(self._log_config)

        self._queue = Queue()

        self._is_connected = False

    def connect(self):
        if self._is_connected:
            raise Exception('Already connected')

        self._cf.disconnected.add_callback(self._disconnected)
        self._log_config.data_received_cb.add_callback(self._log_callback)
        self._log_config.start()

        self._is_connected = True

    def disconnect(self):
        if self._is_connected:
            self._log_config.stop()
            self._log_config.delete()

            self._log_config.data_received_cb.remove_callback(
                self._log_callback)
            self._cf.disconnected.remove_callback(self._disconnected)

            self._queue.empty()

            self._is_connected = False

    def is_connected(self):
        return self._is_connected

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        if not self._is_connected:
            raise StopIteration

        data = self._queue.get()

        if data == self.DISCONNECT_EVENT:
            raise StopIteration

        return data

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def _log_callback(self, ts, data, logblock):
        self._queue.put((ts, data, logblock))

    def _disconnected(self, link_uri):
        self._queue.put(self.DISCONNECT_EVENT)
        self.disconnect()
