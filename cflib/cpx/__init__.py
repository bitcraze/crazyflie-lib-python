#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2022 Bitcraze AB
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
""" CPX Router and discovery"""
import enum
import logging
import queue
import struct
import threading

__author__ = 'Bitcraze AB'
__all__ = ['CPXRouter']
logger = logging.getLogger(__name__)


class CPXTarget(enum.Enum):
    """
    List of CPX targets
    """
    STM32 = 1
    ESP32 = 2
    HOST = 3
    GAP8 = 4


class CPXFunction(enum.Enum):
    """
    List of CPX targets
    """
    SYSTEM = 1
    CONSOLE = 2
    CRTP = 3
    WIFI_CTRL = 4
    APP = 5
    TEST = 0x0E
    BOOTLOADER = 0x0F


class CPXPacket(object):
    """
    A packet with routing and data
    """
    CPX_VERSION = 0

    def __init__(self, function=0, destination=0, source=CPXTarget.HOST, data=bytearray()):
        """
        Create an empty packet with default values.
        """
        self.data = data
        self.source = source
        self.destination = destination
        self.function = function
        self.version = self.CPX_VERSION
        self.length = len(data)
        self.lastPacket = False

    def _get_wire_data(self):
        """Create raw data to send via the wire"""
        raw = bytearray()

        targetsAndFlags = ((self.source.value & 0x7) << 3) | (self.destination.value & 0x7)
        if self.lastPacket:
            targetsAndFlags |= 0x40

        functionAndVersion = (self.function.value & 0x3F) | ((self.version & 0x3) << 6)
        raw.extend(struct.pack('<BB', targetsAndFlags, functionAndVersion))
        raw.extend(self.data)

        return raw

    def _set_wire_data(self, data):
        [targetsAndFlags, functionAndVersion] = struct.unpack('<BB', data[0:2])
        self.version = (functionAndVersion >> 6) & 0x3
        if self.version != self.CPX_VERSION:
            logging.error(f'Unsupported CPX version {self.version} instead of {self.CPX_VERSION}')
            raise RuntimeError(f'Unsupported CPX version {self.version} instead of {self.CPX_VERSION}')
        self.source = CPXTarget((targetsAndFlags >> 3) & 0x07)
        self.destination = CPXTarget(targetsAndFlags & 0x07)
        self.lastPacket = targetsAndFlags & 0x40 != 0
        self.function = CPXFunction(functionAndVersion & 0x3F)
        self.data = data[2:]
        self.length = len(self.data)

    def __str__(self):
        """Get a string representation of the packet"""
        return '{}->{}/{} (size={} bytes)'.format(self.source, self.destination, self.function, self.length)

    wireData = property(_get_wire_data, _set_wire_data)


class CPXRouter(threading.Thread):

    def __init__(self, transport):
        threading.Thread.__init__(self)
        self.daemon = True
        self._transport = transport
        self._rxQueues = {}
        self._packet_assembly = []
        self._connected = True

    # Register and/or blocking calls for ports
    def receivePacket(self, function, timeout=None):

        # Check if a queue exists, if not then create it
        # the user might have implemented new functions
        if function.value not in self._rxQueues:
            print('Creating queue for {}'.format(function))
            self._rxQueues[function.value] = queue.Queue()

        return self._rxQueues[function.value].get(block=True, timeout=timeout)

    def makeTransaction(self, packet):
        self.sendPacket(packet)
        return self.receivePacket(packet.function)

    def sendPacket(self, packet):
        self._transport.writePacket(packet)

    def transport(self):
        self._connected = False
        return self._transport

    def run(self):
        while (self._connected):
            # Read one packet from the transport

            # Packages might have been split up along the
            # way, we should re-assemble here
            try:
                packet = self._transport.readPacket()

                if packet.function.value not in self._rxQueues:
                    pass
                else:
                    self._rxQueues[packet.function.value].put(packet)
            except Exception as e:
                print('Exception while reading transport, link probably closed?')
                print(e)
                import traceback
                print(traceback.format_exc())

# Public facing


class CPX:
    def __init__(self, transport):
        self._router = CPXRouter(transport)
        self._router.start()

    def receivePacket(self, function, timeout=None):
        # Block on a function queue

        # if self._router.isUsedBySubmodule(target, function):
        #  raise ValueError("The CPX target {} and function {} is registered in a sub module".format(target, function))

        # Will block on queue
        return self._router.receivePacket(function, timeout)

    def makeTransaction(self, packet):
        return self._router.makeTransaction(packet)

    def sendPacket(self, packet):
        self._router.sendPacket(packet)

    def close(self):
        self._router.transport().disconnect()
