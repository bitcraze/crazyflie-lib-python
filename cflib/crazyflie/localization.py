#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2017 Bitcraze AB
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
Subsytem handling localization-related data communication
"""
import collections
import logging
import struct

from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.callbacks import Caller

__author__ = 'Bitcraze AB'
__all__ = ['Localization', 'LocalizationPacket']

logger = logging.getLogger(__name__)

# A generic location packet contains type and data. When received the data
# may be decoded by the lib.
LocalizationPacket = collections.namedtuple('localizationPacket',
                                            ['type', 'raw_data', 'data'])


class Localization():
    """
    Handle localization-related data communication with the Crazyflie
    """

    # Implemented channels
    POSITION_CH = 0
    GENERIC_CH = 1

    # Location message types for generig channel
    RANGE_STREAM_REPORT = 0x00
    RANGE_STREAM_REPORT_FP16 = 0x01
    LPS_SHORT_LPP_PACKET = 0x02

    def __init__(self, crazyflie=None):
        """
        Initialize the Extpos object.
        """
        self._cf = crazyflie

        self.receivedLocationPacket = Caller()
        self._cf.add_port_callback(CRTPPort.LOCALIZATION, self._incoming)

    def _incoming(self, packet):
        """
        Callback for data received from the copter.
        """
        if len(packet.data) < 1:
            logger.warning('Localization packet received with incorrect' +
                           'length (length is {})'.format(len(packet.data)))
            return

        pk_type = struct.unpack('<B', packet.data[:1])[0]
        data = packet.data[1:]

        # Decoding the known packet types
        # TODO: more generic decoding scheme?
        decoded_data = None
        if pk_type == self.RANGE_STREAM_REPORT:
            if len(data) % 5 != 0:
                logger.error('Wrong range stream report data lenght')
                return
            decoded_data = {}
            raw_data = data
            for i in range(int(len(data) / 5)):
                anchor_id, distance = struct.unpack('<Bf', raw_data[:5])
                decoded_data[anchor_id] = distance
                raw_data = raw_data[5:]

        pk = LocalizationPacket(pk_type, data, decoded_data)
        self.receivedLocationPacket.call(pk)

    def send_extpos(self, pos):
        """
        Send the current Crazyflie X, Y, Z position. This is going to be
        forwarded to the Crazyflie's position estimator.
        """

        pk = CRTPPacket()
        pk.port = CRTPPort.LOCALIZATION
        pk.channel = self.POSITION_CH
        pk.data = struct.pack('<fff', pos[0], pos[1], pos[2])
        self._cf.send_packet(pk)

    def send_short_lpp_packet(self, dest_id, data):
        """
        Send ultra-wide-band LPP packet to dest_id
        """

        pk = CRTPPacket()
        pk.port = CRTPPort.LOCALIZATION
        pk.channel = self.GENERIC_CH
        pk.data = struct.pack('<BB', self.LPS_SHORT_LPP_PACKET, dest_id) + data
        self._cf.send_packet(pk)
