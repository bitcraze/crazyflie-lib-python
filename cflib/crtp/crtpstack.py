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
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
"""
CRTP packet and ports.
"""
import logging

__author__ = 'Bitcraze AB'
__all__ = ['CRTPPort', 'CRTPPacket']

logger = logging.getLogger(__name__)


class CRTPPort:
    """
    Lists the available ports for the CRTP.
    """
    CONSOLE = 0x00
    PARAM = 0x02
    COMMANDER = 0x03
    MEM = 0x04
    LOGGING = 0x05
    LOCALIZATION = 0x06
    COMMANDER_GENERIC = 0x07
    SETPOINT_HL = 0x08
    PLATFORM = 0x0D
    DEBUGDRIVER = 0x0E
    LINKCTRL = 0x0F
    ALL = 0xFF


class CRTPPacket(object):
    """
    A packet that can be sent via the CRTP.
    """

    # The max size of a CRTP packet payload
    MAX_DATA_SIZE = 30

    def __init__(self, header=0, data=None):
        """
        Create an empty packet with default values.
        """
        self.size = 0
        self._data = bytearray()
        # The two bits in position 3 and 4 needs to be set for legacy
        # support of the bootloader
        self.header = header | 0x3 << 2
        self._port = (header & 0xF0) >> 4
        self._channel = header & 0x03
        if data:
            self._set_data(data)

    def _get_channel(self):
        """Get the packet channel"""
        return self._channel

    def _set_channel(self, channel):
        """Set the packet channel"""
        self._channel = channel
        self._update_header()

    def _get_port(self):
        """Get the packet port"""
        return self._port

    def _set_port(self, port):
        """Set the packet port"""
        self._port = port
        self._update_header()

    def get_header(self):
        """Get the header"""
        self._update_header()
        return self.header

    def set_header(self, port, channel):
        """
        Set the port and channel for this packet.
        """
        self._port = port
        self.channel = channel
        self._update_header()

    def _update_header(self):
        """Update the header with the port/channel values"""
        # The two bits in position 3 and 4 needs to be set for legacy
        # support of the bootloader
        self.header = ((self._port & 0x0f) << 4 | 3 << 2 |
                       (self.channel & 0x03))

    # Some python madness to access different format of the data
    def _get_data(self):
        """Get the packet data"""
        return self._data

    def _set_data(self, data):
        """Set the packet data"""
        if type(data) == bytearray:
            self._data = data
        elif type(data) == str:
            self._data = bytearray(data.encode('ISO-8859-1'))
        elif type(data) == list or type(data) == tuple:
            self._data = bytearray(data)
        elif type(data) == bytes:
            self._data = bytearray(data)
        else:
            raise Exception('Data must be bytearray, string, list or tuple,'
                            ' not {}'.format(type(data)))

    def _get_data_l(self):
        """Get the data in the packet as a list"""
        return list(self._get_data_t())

    def _get_data_t(self):
        """Get the data in the packet as a tuple"""
        return tuple(self._data)

    def __str__(self):
        """Get a string representation of the packet"""
        return '{}:{} {}'.format(self._port, self.channel, self.datat)

    def get_data_size(self):
        return len(self._data)

    def available_data_size(self):
        return self.MAX_DATA_SIZE - self.get_data_size()

    def is_data_size_valid(self):
        return self.available_data_size() >= 0

    data = property(_get_data, _set_data)
    datal = property(_get_data_l, _set_data)
    datat = property(_get_data_t, _set_data)
    datas = property(_get_data, _set_data)
    port = property(_get_port, _set_port)
    channel = property(_get_channel, _set_channel)
