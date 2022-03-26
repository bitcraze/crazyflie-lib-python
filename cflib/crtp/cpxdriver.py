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
""" CRTP CPX Driver. Tunnel CRTP over CPX to the Crazyflie STM32 """
import queue
import re
import socket
import struct
import threading
from urllib.parse import urlparse
from zeroconf import ServiceBrowser, Zeroconf

from .crtpdriver import CRTPDriver
from .crtpstack import CRTPPacket
from .exceptions import WrongUriType

__author__ = 'Bitcraze AB'
__all__ = ['CPXDriver']

class CPXTarget:
  """
  List of CPX targets
  """
  STM32 = 1
  ESP32 = 2
  HOST = 3
  GAP8 = 4    

class CPXFunction:
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
            self.destination = (targetsAndFlags >> 3) & 0x07
            self.source = targetsAndFlags & 0x07
            self.lastPacket = targetsAndFlags & 0x40 != 0

    def _get_wire_data(self):
        """Create raw data to send via the wire"""
        raw = bytearray()
        # This is the length excluding the 2 byte legnth
        wireLength = len(self.data) + 2 # 2 bytes for CPX header
        targetsAndFlags = ((self.source & 0x7) << 3) | (self.destination & 0x7)
        if self.lastPacket:
          targetsAndFlags |= 0x40
        #print(self.destination)
        #print(self.source)
        #print(targets)
        function = self.function & 0xFF
        raw.extend(struct.pack(self._wireHeaderFormat, wireLength, targetsAndFlags, function))
        raw.extend(self.data)
        
        # We need to handle this better...
        if (wireLength > 1022):
          raise "Cannot send this packet, the size is too large!"

        return raw

    def __str__(self):
        """Get a string representation of the packet"""
        return "{:02X}->{:02X}/{:02X}".format(self.source, self.destination, self.function)

    wireData = property(_get_wire_data, None)

class CPX(object):
  """
  A packet with routing and data
  """

  def __init__(self, socket):
    self._socket = socket

  def _rx_bytes(self, size):
    data = bytearray()
    while len(data) < size:
      #print(size - len(data))
      data.extend(self._socket.recv(size-len(data)))
    return data

  def send(self, packet):
    self._socket.send(packet.wireData)

  def receive(self):
    header = self._rx_bytes(4)
    packet = CPXPacket(wireHeader=header)
    packet.data = self._rx_bytes(packet.length - 2) # remove routing info here
    return packet

  def transaction(self, packet):
    self.send(packet)
    return self.receive()

# For each scan the driver is re-initialized, if we do ZeroConf inside
# the driver init we will not have time to find any devices, so start
# ZeroCont at startup and keep it running all the time. The driver
# will just query this to return discovered devices.
persistentZeroContListener = None
class ZeroConfListener:
    def __init__(self):
        self._hosts = []

        zeroconf = Zeroconf()
        browser = ServiceBrowser(zeroconf, "_cpx._tcp.local.", self)

    def remove_service(self, zeroconf, type, name):
        print("Service %s removed" % (name,))
        info = zeroconf.get_service_info(type, name)
        self._hosts.remove(info)

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        print("Service %s added, service info: %s" % (name, info))
        self._hosts.append(info)
    
    def getAvailableHosts(self):
      cpxHosts = []
      for hosts in self._hosts:
        cpxHosts.append(("cpx://{}:{}".format(hosts.server, hosts.port), hosts.properties[b"name"]))
      return cpxHosts

    def update_service(self, zeroconf, type, name):
      print("Updated service")

persistentZeroContListener = ZeroConfListener()

class CPXDriver(CRTPDriver):

    def __init__(self):
        self.needs_resending = False

    def connect(self, uri, linkQualityCallback, linkErrorCallback):
        if not re.search('^cpx://', uri):
            raise WrongUriType('Not an UDP URI')

        parse = urlparse(uri.split(" ")[0])

        print("Connecting to socket on {}:{}...".format(parse.hostname, parse.port))
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((parse.hostname, parse.port))

        self.in_queue = queue.Queue()

        self._cpx = CPX(self._socket)

        self._thread = _CPXReceiveThread(self._cpx, self.in_queue,
                                         linkErrorCallback)
        self._thread.start()


        self._cpx.send(CPXPacket(destination=CPXTarget.STM32,
                                 function=CPXFunction.SYSTEM,
                                 data=[0x10, 0x01]))

    def receive_packet(self, time=0):
        if time == 0:
            try:
                return self.in_queue.get(False)
            except queue.Empty:
                return None
        elif time < 0:
            try:
                return self.in_queue.get(True)
            except queue.Empty:
                return None
        else:
            try:
                return self.in_queue.get(True, time)
            except queue.Empty:
                return None

    def send_packet(self, pk):
        raw = (pk.header,) + struct.unpack('B' * len(pk.data), pk.data)
        self._cpx.send(CPXPacket(destination=CPXTarget.STM32,
                                 function=CPXFunction.CRTP,
                                 data=raw))

    def close(self):
        """ Close the link. """
        # Stop the comm thread
        self._thread.stop()

        # Close the socket
        try:
            self._socket.close()
            self._socket = None

        except Exception as e:
            logger.info('Could not close {}'.format(e))
            pass
        self._cpx = None

    def get_name(self):
        return 'cpx'

    def scan_interface(self, address):
        return persistentZeroContListener.getAvailableHosts()

# Transmit/receive thread
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
                cpxPacket = self._cpx.receive()
                data = struct.unpack('B' * len(cpxPacket.data), cpxPacket.data)
                if len(data) > 0:
                    pk = CRTPPacket(data[0],
                                    list(data[1:]))
                    self.in_queue.put(pk)
            except Exception as e:
                import traceback

                self.link_error_callback(
                    'Error communicating with the Crazyflie\n'
                    'Exception:%s\n\n%s' % (e,
                                            traceback.format_exc()))