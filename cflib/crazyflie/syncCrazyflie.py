# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2016-2022 Bitcraze AB
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
The synchronous Crazyflie class is a wrapper around the "normal" Crazyflie
class. It handles the asynchronous nature of the Crazyflie API and turns it
into blocking functions. It is useful for simple scripts that performs tasks
as a sequence of events.

Example:
```python
with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
    with PositionHlCommander(scf, default_height=0.5, default_velocity=0.2) as pc:
        # fly onto a landing platform at non-zero height (ex: from floor to desk, etc)
        pc.forward(1.0)
        pc.left(1.0)
```
"""
import logging
from threading import Event

from cflib.crazyflie import Crazyflie

logger = logging.getLogger(__name__)


class SyncCrazyflie:

    def __init__(self, link_uri, cf=None):
        """
        Create a synchronous Crazyflie instance with the specified link_uri

        :param link_uri: The uri to use when connecting to the Crazyflie
        :param cf: Optional Crazyflie instance to use, None by default. If no object is supplied, a Crazyflie instance
         is created. This parameters is useful if you want to use a Crazyflie instance with log/param caching.
        """
        if cf:
            self.cf = cf
        else:
            self.cf = Crazyflie()

        self._link_uri = link_uri
        self._connect_event = None
        self._disconnect_event = None
        self._params_updated_event = Event()
        self._is_link_open = False
        self._error_message = None

    def open_link(self):
        """
        Open a link to a Crazyflie on the underlying Crazyflie instance.

        This function is blocking and will return when the connection is established and TOCs for log and
        parameters have been downloaded or fetched from the cache.

        Note: Parameter values have not been updated when this function returns. See the wait_for_params()
        method.
        """
        if (self.is_link_open()):
            raise Exception('Link already open')

        self._add_callbacks()

        logger.debug('Connecting to %s' % self._link_uri)

        self._connect_event = Event()
        self._params_updated_event.clear()
        self.cf.open_link(self._link_uri)
        self._connect_event.wait()
        self._connect_event = None

        if not self._is_link_open:
            self._remove_callbacks()
            self._params_updated_event.clear()
            raise Exception(self._error_message)

    def wait_for_params(self):
        """
        Wait for parameter values to be updated.

        During the connection sequence, parameter values are downloaded after the TOCs have been received. The
        open_link() method will return after the TOCs have been received but before the parameter values
        are downloaded.
        This method will block until the parameter values are received and can be used
        to make sure the connection sequence has terminated. In most cases this is not important, but
        radio bandwidth will be limited while parameters are downloaded due to the communication that is going on.

        Example:
        ```python
        with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
            scf.wait_for_params()
            # At this point the connection sequence is finished
        ```

        """
        self._params_updated_event.wait()

    def __enter__(self):
        self.open_link()
        return self

    def close_link(self):
        if (self.is_link_open()):
            self._disconnect_event = Event()
            self.cf.close_link()
            self._disconnect_event.wait()
            self._disconnect_event = None
            self._params_updated_event.clear()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_link()

    def is_link_open(self):
        return self._is_link_open

    def is_params_updated(self):
        return self._params_updated_event.is_set()

    def _connected(self, link_uri):
        """ This callback is called form the Crazyflie API when a Crazyflie
        has been connected and the TOCs have been downloaded."""
        logger.debug('Connected to %s' % link_uri)
        self._is_link_open = True
        if self._connect_event:
            self._connect_event.set()

    def _connection_failed(self, link_uri, msg):
        """Callback when initial connection fails (i.e no Crazyflie
        at the specified address)"""
        logger.debug('Connection to %s failed: %s' % (link_uri, msg))
        self._is_link_open = False
        self._error_message = msg
        if self._connect_event:
            self._connect_event.set()

    def _disconnected(self, link_uri):
        self._remove_callbacks()
        self._is_link_open = False
        if self._disconnect_event:
            self._disconnect_event.set()

    def _all_params_updated(self, link_uri):
        self._params_updated_event.set()

    def _add_callbacks(self):
        self.cf.connected.add_callback(self._connected)
        self.cf.connection_failed.add_callback(self._connection_failed)
        self.cf.disconnected.add_callback(self._disconnected)
        self.cf.fully_connected.add_callback(self._all_params_updated)

    def _remove_callbacks(self):
        def remove_callback(container, callback):
            try:
                container.remove_callback(callback)
            except ValueError:
                pass

        remove_callback(self.cf.connected, self._connected)
        remove_callback(self.cf.connection_failed, self._connection_failed)
        remove_callback(self.cf.disconnected, self._disconnected)
        remove_callback(self.cf.fully_connected, self._all_params_updated)
