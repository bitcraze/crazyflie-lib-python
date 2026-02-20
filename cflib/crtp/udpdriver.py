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
Crazyflie UDP driver.

This driver is used to communicate with the Crazyflie using a UDP connection.
Scanning feature assumes a crazyflie server is running on port 19850-19859
that will respond to a null CRTP packet with a valid CRTP packet.

v2.0 changelog:
- Complete rewrite to align with other CRTP driver implementations
- Added dedicated _UdpReceiveThread class for asynchronous packet reception
- Implemented functional scan_interface() that probes UDP ports 19850-19859
- Fixed send_packet() with null checks, proper error callbacks, and removed checksum.
- Added proper socket cleanup in close() method
- Changed variable naming to align with other CRTP drivers and added docstrings
- Added environment variable SCAN_ADDRESS for scan_interface() to specify target IP address.
  This is useful for server and clients running on different hosts.
"""
import logging
import os
import queue
import re
import socket
import struct
import threading
from urllib.parse import urlparse

from .crtpstack import CRTPPacket
from .exceptions import WrongUriType
from cflib.crtp.crtpdriver import CRTPDriver

__author__ = 'Bitcraze AB'
__all__ = ['UdpDriver']

logger = logging.getLogger(__name__)

_BASE_PORT = 19850
_NR_OF_PORTS_TO_SCAN = 10
_SCAN_TIMEOUT = 0.1


class UdpDriver(CRTPDriver):
    """ Crazyflie UDP link driver """

    def __init__(self):
        """ Create the link driver """
        CRTPDriver.__init__(self)
        self.socket = None
        self.addr = None
        self.uri = ''
        self.link_error_callback = None
        self.in_queue = None
        self._thread = None
        self.needs_resending = False

    def connect(self, uri, radio_link_statistics_callback, link_error_callback):
        """
        Connect the link driver to a specified URI of the format:
        udp://<host>:<port>

        The callback for radio link statistics is not used by the UDP driver.
        The callback from link_error_callback will be called when an error
        occurs with an error message.
        """
        if not re.search('^udp://', uri):
            raise WrongUriType('Not a UDP URI')

        if self.socket is not None:
            raise Exception('Link already open!')

        self.uri = uri
        self.link_error_callback = link_error_callback

        parse = urlparse(uri)

        # Prepare the inter-thread communication queue
        self.in_queue = queue.Queue()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr = (parse.hostname, parse.port)
        self.socket.connect(self.addr)

        # Launch the comm thread
        self._thread = _UdpReceiveThread(self.socket, self.in_queue,
                                         link_error_callback)
        self._thread.start()

    def receive_packet(self, wait=0):
        """
        Receive a packet though the link. This call is blocking but will
        timeout and return None if a timeout is supplied.
        """
        if wait == 0:
            try:
                return self.in_queue.get(False)
            except queue.Empty:
                return None
        elif wait < 0:
            try:
                return self.in_queue.get(True)
            except queue.Empty:
                return None
        else:
            try:
                return self.in_queue.get(True, wait)
            except queue.Empty:
                return None

    def send_packet(self, pk):
        """ Send the packet pk though the link """
        if self.socket is None:
            return

        try:
            raw = (pk.header,) + struct.unpack('B' * len(pk.data), pk.data)
            data = struct.pack('B' * len(raw), *raw)
            self.socket.send(data)
        except Exception as e:
            if self.link_error_callback:
                self.link_error_callback(
                    'UdpDriver: Could not send packet to Crazyflie\n'
                    'Exception: %s' % e)

    def pause(self):
        self._thread.stop()
        self._thread = None

    def restart(self):
        if self._thread:
            return

        self._thread = _UdpReceiveThread(self.socket, self.in_queue,
                                         self.link_error_callback)
        self._thread.start()

    def close(self):
        """ Close the link. """
        # Stop the comm thread
        if self._thread:
            self._thread.stop()

        # Close the UDP socket
        try:
            if self.socket:
                self.socket.close()
        except Exception as e:
            logger.info('Could not close {}'.format(e))
        self.socket = None

        # Clear callbacks
        self.link_error_callback = None

    def get_status(self):
        return 'No information available'

    def get_name(self):
        return 'udp'

    def scan_interface(self, address=None):
        """ Scan interface for Crazyflies """
        found = []
        scan_address = os.getenv('SCAN_ADDRESS', '127.0.0.1')

        for i in range(_NR_OF_PORTS_TO_SCAN):
            port = _BASE_PORT + i
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(_SCAN_TIMEOUT)
                s.connect((scan_address, port))
                s.send(b'\xFF')  # Null CRTP packet as probe
                s.recv(1024)
                # Got a response, Crazyflie is available
                s.close()
                found.append(['udp://{}:{}'.format(scan_address, port), ''])
            except socket.timeout:
                s.close()
            except Exception:
                pass

        return found


# Receive thread
class _UdpReceiveThread(threading.Thread):
    """
    UDP link receiver thread used to read data from the
    UDP socket. """

    def __init__(self, sock, inQueue, link_error_callback):
        """ Create the object """
        threading.Thread.__init__(self, name='UdpReceiveThread')
        self._socket = sock
        self._in_queue = inQueue
        self._sp = False
        self._link_error_callback = link_error_callback
        self.daemon = True

    def stop(self):
        """ Stop the thread """
        self._sp = True
        try:
            self.join()
        except Exception:
            pass

    def run(self):
        """ Run the receiver thread """
        self._socket.settimeout(1.0)

        while True:
            if self._sp:
                break
            try:
                packet = self._socket.recv(1024)
                data = struct.unpack('B' * len(packet), packet)
                if len(data) > 0:
                    pk = CRTPPacket(header=data[0], data=data[1:])
                    self._in_queue.put(pk)
            except socket.timeout:
                pass
            except Exception as e:
                import traceback

                self._link_error_callback(
                    'Error communicating with the Crazyflie\n'
                    'Exception:%s\n\n%s' % (e, traceback.format_exc()))
