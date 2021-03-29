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
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
"""
Crazyflie driver using the Crazyradio Server.

This driver uses the zmq network protocol implemented by the CrazyradioServer
to communicate with the Crazyflie.
"""
from build.lib.cflib.crtp.exceptions import WrongUriType
import logging
import threading
import zmq

from .crtpstack import CRTPPacket
from cflib.crtp.crtpdriver import CRTPDriver

__author__ = 'Bitcraze AB'
__all__ = ['RadioServerDriver']

logger = logging.getLogger(__name__)


class RadioServerDriver(CRTPDriver):
    """ cflinkcpp driver """

    def __init__(self):
        """Driver constructor. Throw an exception if the driver is unable to
        open the URI
        """
        self.uri = ''

        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.REQ)
        self._socket.connect("tcp://localhost:7777")

        self._connection_tx = None
        self._connection_rx = None

        # The CrazyradioServer implements safelink
        self.needs_resending = False

        self._connection = None

    def connect(self, uri, link_quality_callback, link_error_callback):
        """Connect the driver to a specified URI

        @param uri Uri of the link to open
        @param link_quality_callback Callback to report link quality in percent
        @param link_error_callback Callback to report errors (will result in
               disconnection)
        """
        self._socket.send_json({
            'jsonrpc': '2',
            'method': 'connect',
            'params': {
                'uri': uri
            }
        })

        answer = self._socket.recv_json()

        if 'error' in answer:
            if answer['error']['code'] == 1:
                raise WrongUriType
            else:
                raise Exception('Error while connecting: {}'.format(answer['error']['message']))

        self.uri = uri
        self._link_quality_callback = link_quality_callback
        self._link_error_callback = link_error_callback

        self._connection_tx = self._ctx.socket(zmq.PUSH)
        self._connection_tx.connect('tcp://localhost:{}'.format(answer['result']['push']))

        self._connection_rx = self._ctx.socket(zmq.PULL)
        self._connection_rx.connect('tcp://localhost:{}'.format(answer['result']['pull']))
        

    def send_packet(self, pk):
        """Send a CRTP packet"""
        try:
            data = bytes([pk.header] + pk.datal)
            self._connection_tx.send(data)
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
        try:
            data = self._connection_rx.recv()

            if not data:
                return None

            pk = CRTPPacket()
            pk.port = data[0] >> 4
            pk.channel = data[0] & 0x03
            pk.data = data[1::]
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
        'Crazyradio Server'

    def scan_interface(self, address=None):
        """
        Scan interface for available Crazyflie quadcopters and return a list
        with them.
        """
        
        self._socket.send_json({
            "jsonrpc": "2",
            "method": "scan",
            "params": {}
        })

        answer = self._socket.recv_json();

        if 'error' in answer:
            raise Exception('Error scanning: {}'.format(answer['error']['message']))

        # convert to list of tuples, where the second part is a comment
        result = [(uri, '') for uri in answer['result']['found']]
        return result

    def scan_selected(self, uris):
        """
        Scan interface for available Crazyflie quadcopters and return a list
        with them.
        """

        self._socket.send_json({
            "jsonrpc": "2",
            "method": "scanSelected",
            "params": {
                "uris": uris
            }
        })

        answer = self._socket.recv_json();

        if 'error' in answer:
            raise Exception('Error in scan_selected: {}'.format(answer['error']['message']))

        return answer['result']['found']



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
        self._socket.send_json({
            'jsonrpc': '2',
            'method': 'disconnect',
            'params': {
                'uri': self.uri
            }
        })

        answer = self._socket.recv_json()

        if 'error' in answer:
            raise Exception('Error disconnecting: {}'.format(answer['error']['message']))


if __name__ == "__main__":
    link = RadioServerDriver()
    found = link.scan_interface()
    print(found)

    if len(found) > 0:
        link.connect(found[0][0], None, None)

        print(link.receive_packet())

        # link.close()

