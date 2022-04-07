#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2013 Bitcraze AB
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
Callback objects used in the Crazyflie library
"""
from threading import Event

__author__ = 'Bitcraze AB'
__all__ = ['Caller']


class Caller():
    """ An object were callbacks can be registered and called """

    def __init__(self):
        """ Create the object """
        self.callbacks = []

    def add_callback(self, cb):
        """ Register cb as a new callback. Will not register duplicates. """
        if ((cb in self.callbacks) is False):
            self.callbacks.append(cb)

    def remove_callback(self, cb):
        """ Un-register cb from the callbacks """
        self.callbacks.remove(cb)

    def call(self, *args):
        """ Call the callbacks registered with the arguments args """
        copy_of_callbacks = list(self.callbacks)
        for cb in copy_of_callbacks:
            cb(*args)


class Syncer:
    """A class to create synchronous behavior for methods using callbacks"""

    def __init__(self):
        self._event = Event()
        self.success_args = None
        self.failure_args = None
        self.is_success = False

    def success_cb(self, *args):
        self.success_args = args
        self.is_success = True
        self._event.set()

    def failure_cb(self, *args):
        self.failure_args = args
        self.is_success = False
        self._event.set()

    def wait(self):
        self._event.wait()

    def clear(self):
        self._event.clear()
