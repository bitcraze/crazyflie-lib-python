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
The syncronous Crazyflie class is a wrapper around the "normal" Crazyflie
class. It handles the asynchronous nature of the Crazyflie API and turns it
into blocking function. It is useful for simple scripts that performs tasks
as a sequence of events.
"""
from threading import Event

from cflib.crazyflie import Crazyflie


class SyncCrazyflie:

    def __init__(self, link_uri, cf=None):
        """ Create a synchronous Crazyflie instance with the specified
        link_uri """

        if cf:
            self.cf = cf
        else:
            self.cf = Crazyflie()

        self._link_uri = link_uri
        self._connect_event = Event()
        self._is_link_open = False
        self._error_message = None

        self.cf.connected.add_callback(self._connected)
        self.cf.connection_failed.add_callback(self._connection_failed)
        self.cf.disconnected.add_callback(self._disconnected)

    def open_link(self):
        if (self.is_link_open()):
            raise Exception('Link already open')

        print('Connecting to %s' % self._link_uri)
        self.cf.open_link(self._link_uri)
        self._connect_event.wait()
        if not self._is_link_open:
            raise Exception(self._error_message)

    def __enter__(self):
        self.open_link()
        return self

    def close_link(self):
        self.cf.close_link()
        self._is_link_open = False

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_link()

    def is_link_open(self):
        return self._is_link_open

    def _connected(self, link_uri):
        """ This callback is called form the Crazyflie API when a Crazyflie
        has been connected and the TOCs have been downloaded."""
        print('Connected to %s' % link_uri)
        self._is_link_open = True
        self._connect_event.set()

    def _connection_failed(self, link_uri, msg):
        """Callback when connection initial connection fails (i.e no Crazyflie
        at the specified address)"""
        print('Connection to %s failed: %s' % (link_uri, msg))
        self._is_link_open = False
        self._error_message = msg
        self._connect_event.set()

    def _disconnected(self, link_uri):
        self._is_link_open = False
