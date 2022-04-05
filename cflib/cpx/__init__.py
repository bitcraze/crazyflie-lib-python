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
import queue
import socket
import struct
import threading
import enum
from urllib.parse import urlparse
from zeroconf import ServiceBrowser, Zeroconf
from .gap8.bootloader import GAP8Bootloader

__author__ = 'Bitcraze AB'
__all__ = ['CPXRouter']

print("CPX import")

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

    def __init__(self, function=0, destination=0, source=CPXTarget.HOST, data=bytearray(), wireHeader=None):
        """
        Create an empty packet with default values.
        """
        self.data = data
        self.source = source
        self.destination = destination
        self.function = function
        self._wireHeaderFormat = "<HBB"
        self.length = 0
        self.lastPacket = False
        if wireHeader:
            [self.length, targetsAndFlags, self.function] = struct.unpack(self._wireHeaderFormat, wireHeader)
            
            self.source = CPXTarget((targetsAndFlags >> 3) & 0x07)
            self.destination = CPXTarget(targetsAndFlags & 0x07)
            self.lastPacket = targetsAndFlags & 0x40 != 0
            self.function = CPXFunction(self.function)

    def _get_wire_data(self):
        """Create raw data to send via the wire"""
        raw = bytearray()
        # This is the length excluding the 2 byte legnth
        wireLength = len(self.data) + 2 # 2 bytes for CPX header
        targetsAndFlags = ((self.source.value & 0x7) << 3) | (self.destination.value & 0x7)
        if self.lastPacket:
          targetsAndFlags |= 0x40
        #print(self.destination)
        #print(self.source)
        #print(targets)
        function = self.function.value & 0xFF
        raw.extend(struct.pack(self._wireHeaderFormat, wireLength, targetsAndFlags, function))
        raw.extend(self.data)
        
        # We need to handle this better...
        if (wireLength > 1022):
          raise "Cannot send this packet, the size is too large!"

        return raw

    def __str__(self):
        """Get a string representation of the packet"""
        return "{}->{}/{} (size={} bytes)".format(self.source, self.destination, self.function, self.length)

    wireData = property(_get_wire_data, None)

# Internal here, route to modules and from public facing API
class CPXRouter(threading.Thread):
    
    def __init__(self, transport):
      threading.Thread.__init__(self)
      self._transport = transport
      self._rxQueues = {}
      self._packet_assembly = []

    # Register and/or blocking calls for ports
    def receivePacket(self, function):

      # Check if a queue exists, if not then create it
      # the user might have implemented new functions
      if not function.value in self._rxQueues:
        print("Creating queue for {}".format(function))
        self._rxQueues[function.value] = queue.Queue()
      
      return self._rxQueues[function.value].get(block=True)

    def makeTransaction(self, packet):
      self.sendPacket(packet)
      return self.getPacket(packet.function)

    def sendPacket(self, packet):
      # Do we queue here?
      self._transport.write(packet.wireData)
      
    def run(self):
        while(1):
        # Read one packet from the transport

        # Packages might have been split up along the
        # way, due to MTU limitations on links. But here we have
        # lots of memory, so assemble full packets by looking at last
        # packet byte. Note that chunks of one packet could be mixed
        # with chunks from antother packet.
          header = self._transport.read(4)
          packet = CPXPacket(wireHeader=header)
          packet.data = self._transport.read(packet.length - 2) # remove routing info here
          #print(packet)
        # if not packet.target in self._packet_assembly:
        #   self._packet_assembly[packet.target][packet.function] = []
        # else
        #   if not packet.function in self._packet_assembly[packet.target]:
        #     self._packet_assembly[packet.target][packet.function] = []

        # self._packet_assembly[packet.target][packet.function].append(packet)

        # if (packet.lastPart):
        #   # Assemble packet and send up stack
        #   pass
          if not packet.function.value in self._rxQueues:
            pass
            #print("Got packet for {}, but have no queue".format(packet.function))
          else:
            self._rxQueues[packet.function.value].put(packet)
          #self._rxQueues[packet.function.value] = queue.Queue()
          #print(self._rxQueues[packet.function.value].qsize())
          

# Public facing 
class CPX:
    def __init__(self, transport):
      self._router = CPXRouter(transport)
      self._router.start()
      #self.gap8.bootloader = GAP8Bootloader(self)

    def receivePacket(self, function):
      # Block on a function queue

      #if self._router.isUsedBySubmodule(target, function):
      #  raise ValueError("The CPX target {} and function {} is registered in a sub module".format(target, function))

      # Will block on queue
      return self._router.receivePacket(function)

    def makeTransaction(self, packet):
      return self._router.makeTransaction(packet)

    def sendPacket(self, packet):
      self._router.sendPacket(packet)

    def close(self):
      print("Should close transport connection")