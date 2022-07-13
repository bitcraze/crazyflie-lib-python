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
An early serial link driver. This could still be used (after some fixing) to
run high-speed CRTP with the Crazyflie. The UART can be run at 2Mbit.
"""
import logging
import queue
import re
import struct
import threading

from .crtpstack import CRTPPacket
from .exceptions import WrongUriType
from cflib.cpx import CPX
from cflib.cpx import CPXFunction
from cflib.cpx import CPXPacket
from cflib.cpx import CPXTarget
from cflib.cpx.transports import UARTTransport
from cflib.crtp.crtpdriver import CRTPDriver

found_serial = True
try:
    import serial.tools.list_ports as list_ports
except ImportError:
    found_serial = False

__author__ = 'Bitcraze AB'
__all__ = ['SerialDriver']

logger = logging.getLogger(__name__)


class SerialDriver(CRTPDriver):

    def __init__(self):
        CRTPDriver.__init__(self)
        self.ser = None
        self.uri = ''
        self.link_error_callback = None
        self.in_queue = None
        self.out_queue = None
        self._receive_thread = None
        self._send_thread = None
        self.needs_resending = False
        logger.info('Initialized serial driver.')

    def connect(self, uri, linkQualityCallback, linkErrorCallback):
        # check if the URI is a serial URI
        if not re.search('^serial://', uri):
            raise WrongUriType('Not a serial URI')

        # Check if it is a valid serial URI
        uri_data = re.search('^serial://([-a-zA-Z0-9/.]+)$', uri)
        if not uri_data:
            raise Exception('Invalid serial URI')

        # Move to Serial transport?
        device_name = uri_data.group(1)
        devices = self.get_devices()
        if device_name not in devices:
            raise Exception('Could not identify device')
        device = devices[device_name]

        self.uri = uri

        self.link_error_callback = linkErrorCallback

        # Prepare the inter-thread communication queue
        self.in_queue = queue.Queue()

        self.cpx = CPX(UARTTransport(device, 576000))

        self._thread = _CPXReceiveThread(self.cpx, self.in_queue,
                                         linkErrorCallback)
        self._thread.start()

        # Switch the link bridge to CPX in the Crazyflie
        self.cpx.sendPacket(CPXPacket(destination=CPXTarget.STM32,
                                      function=CPXFunction.SYSTEM,
                                      data=[0x21, 0x01]))
        # Force client connect to true
        self.cpx.sendPacket(CPXPacket(destination=CPXTarget.STM32,
                                      function=CPXFunction.SYSTEM,
                                      data=[0x20, 0x01]))

    def send_packet(self, pk):
        raw = (pk.header,) + struct.unpack('B' * len(pk.data), pk.data)
        self.cpx.sendPacket(CPXPacket(destination=CPXTarget.STM32,
                                      function=CPXFunction.CRTP,
                                      data=raw))

    def receive_packet(self, wait=0):
        try:
            if wait == 0:
                pk = self.in_queue.get(False)
            elif wait < 0:
                pk = self.in_queue.get(True)
            else:
                pk = self.in_queue.get(True, wait)
        except queue.Empty:
            return None
        return pk

    def get_status(self):
        return 'No information available'

    def get_name(self):
        return 'serial'

    def scan_interface(self, address):
        print('Scanning serial')
        if found_serial:
            print('Found serial')
            devices_names = self.get_devices().keys()
            print(devices_names)
            return [('serial://' + x, '') for x in devices_names]
        else:
            return []

    def close(self):
        """ Close the link. """
        # Stop the comm thread
        self._thread.stop()

        # Close the socket
        try:
            self.cpx.close()
            self.cpx = None

        except Exception as e:
            print(e)
            logger.error('Could not close {}'.format(e))
            pass
        print('Driver closed')

    def get_devices(self):
        result = {}
        for port in list_ports.comports():
            name = port.name
            # Name is not populated on all systems, fall back on the device
            if not name:
                name = port.device

            result[name] = port.device

        return result


class _CPXReceiveThread(threading.Thread):
    """
    Radio link receiver thread used to read data from the
    Socket. """

    def __init__(self, cpx, inQueue, link_error_callback):
        """ Create the object """
        threading.Thread.__init__(self)
        self._cpx = cpx
        self.in_queue = inQueue
        self.sp = False
        self.link_error_callback = link_error_callback

    def stop(self):
        """ Stop the thread """
        self.sp = True
        try:
            self.join()
        except Exception:
            pass

    def run(self):
        """ Run the receiver thread """

        while (True):
            if (self.sp):
                break
            try:
                # Block until a packet is available though the socket
                # CPX receive will only return full packets
                cpxPacket = self._cpx.receivePacket(CPXFunction.CRTP, timeout=1)
                data = struct.unpack('B' * cpxPacket.length, cpxPacket.data)
                if len(data) > 0:
                    pk = CRTPPacket(data[0],
                                    list(data[1:]))
                    self.in_queue.put(pk)
            except queue.Empty:
                pass  # This is ok
            except Exception as e:
                import traceback

                self.link_error_callback(
                    'Error communicating with the Crazyflie\n'
                    'Exception:%s\n\n%s' % (e,
                                            traceback.format_exc()))
