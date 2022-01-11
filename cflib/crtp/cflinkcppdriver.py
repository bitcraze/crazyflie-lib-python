#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2021 Bitcraze AB
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
Crazyflie driver using the cflinkcpp implementation.

This driver is used to communicate over the radio or USB.
"""
import logging
import threading

import cflinkcpp

from .crtpstack import CRTPPacket
from cflib.crtp.crtpdriver import CRTPDriver

__author__ = 'Bitcraze AB'
__all__ = ['CfLinkCppDriver']

logger = logging.getLogger(__name__)


class CfLinkCppDriver(CRTPDriver):
    """ cflinkcpp driver """

    def __init__(self):
        """Driver constructor. Throw an exception if the driver is unable to
        open the URI
        """
        self.uri = ''

        # cflinkcpp resends packets internally
        self.needs_resending = False

        self._connection = None

    def connect(self, uri, link_quality_callback, link_error_callback):
        """Connect the driver to a specified URI

        @param uri Uri of the link to open
        @param link_quality_callback Callback to report link quality in percent
        @param link_error_callback Callback to report errors (will result in
               disconnection)
        """

        self._connection = cflinkcpp.Connection(uri)
        self.uri = uri
        self._link_quality_callback = link_quality_callback
        self._link_error_callback = link_error_callback

        if uri.startswith('radio://') and link_quality_callback is not None:
            self._last_connection_stats = self._connection.statistics
            self._recompute_link_quality_timer()

    def send_packet(self, pk):
        """Send a CRTP packet"""
        nativePk = cflinkcpp.Packet()
        nativePk.port = pk.port
        nativePk.channel = pk.channel
        nativePk.payload = bytes(pk.data)
        try:
            self._connection.send(nativePk)
        except Exception as e:
            if self._link_error_callback is not None:
                import traceback
                self._link_error_callback(
                    'Error communicating! Perhaps your device has been unplugged?\n'
                    'Exception:{}\n\n{}'.format(e, traceback.format_exc()))

    def receive_packet(self, wait=0):
        """Receive a CRTP packet.

        @param wait The time to wait for a packet in second. -1 means forever

        @return One CRTP packet or None if no packet has been received.
        """
        if wait < 0:
            # Since we block in the native lib, break up infinity timeouts into smaller
            # pieces, so Ctrl+C keeps working as expected
            timeout = 100
        elif wait == 0:
            timeout = 1
        else:
            timeout = int(wait*1000)

        try:
            while True:
                nativePk = self._connection.recv(timeout=timeout)
                if wait >= 0 or nativePk.valid:
                    break

            if not nativePk.valid:
                return None

            pk = CRTPPacket()
            pk.port = nativePk.port
            pk.channel = nativePk.channel
            pk.data = nativePk.payload
            return pk
        except Exception as e:
            if self._link_error_callback is not None:
                import traceback
                self._link_error_callback(
                    'Error communicating! Perhaps your device has been unplugged?\n'
                    'Exception:{}\n\n{}'.format(e, traceback.format_exc()))

    def get_status(self):
        """
        Return a status string from the interface.
        """
        'okay'

    def get_name(self):
        """
        Return a human readable name of the interface.
        """
        'cflinkcpp'

    def scan_interface(self, address=None):
        """
        Scan interface for available Crazyflie quadcopters and return a list
        with them.
        """
        if address:
            uris = cflinkcpp.Connection.scan(address)
        else:
            uris = cflinkcpp.Connection.scan()
        # convert to list of tuples, where the second part is a comment
        result = [(uri, '') for uri in uris]
        return result

    def scan_selected(self, uris):
        """
        Scan interface for available Crazyflie quadcopters and return a list
        with them.
        """
        return cflinkcpp.Connection.scan_selected(uris)

    def enum(self):
        """Enumerate, and return a list, of the available link URI on this
        system
        """
        return self.scan_interface()

    def get_help(self):
        """return the help message on how to form the URI for this driver
        None means no help
        """
        ''

    def close(self):
        """Close the link"""
        self._connection.close()
        self._connection = None

    def _recompute_link_quality_timer(self):
        if self._connection is None:
            return
        stats = self._connection.statistics
        sent_count = stats.sent_count - self._last_connection_stats.sent_count
        ack_count = stats.ack_count - self._last_connection_stats.ack_count
        if sent_count > 0:
            link_quality = min(ack_count, sent_count) / sent_count * 100.0
        else:
            link_quality = 1
        self._last_connection_stats = stats

        if self._link_quality_callback is not None:
            self._link_quality_callback(link_quality)

        if sent_count > 10 and ack_count == 0 and self._link_error_callback is not None:
            self._link_error_callback('Too many packets lost')

        threading.Timer(1.0, self._recompute_link_quality_timer).start()
