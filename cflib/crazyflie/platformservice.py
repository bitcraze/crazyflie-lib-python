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
Used for sending control setpoints to the Crazyflie
"""
import logging

from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort

__author__ = 'Bitcraze AB'
__all__ = ['PlatformService']

logger = logging.getLogger(__name__)

PLATFORM_COMMAND = 0
VERSION_COMMAND = 1
APP_CHANNEL = 2

PLATFORM_SET_CONT_WAVE = 0
PLATFORM_REQUEST_ARMING = 1

VERSION_GET_PROTOCOL = 0
VERSION_GET_FIRMWARE = 1

LINKSERVICE_SOURCE = 1


class PlatformService():
    """
    Used for sending control setpoints to the Crazyflie
    """

    def __init__(self, crazyflie=None):
        """
        Initialize the platform object.
        """
        self._cf = crazyflie

        self._cf.add_port_callback(CRTPPort.PLATFORM, self._platform_callback)
        self._cf.add_port_callback(CRTPPort.LINKCTRL, self._crt_service_callback)

        self._protocolVersion = -1
        self._callback = None

    def fetch_platform_informations(self, callback):
        """
        Fetch platform info from the firmware
        Should be called at the earliest in the connection sequence
        """

        self._protocolVersion = -1
        self._callback = callback

        self._request_protocol_version()

    def set_continous_wave(self, enabled):
        """
        Enable/disable the client side X-mode. When enabled this recalculates
        the setpoints before sending them to the Crazyflie.
        """
        pk = CRTPPacket()
        pk.set_header(CRTPPort.PLATFORM, PLATFORM_COMMAND)

        pk.data = (PLATFORM_SET_CONT_WAVE, enabled)
        self._cf.send_packet(pk)

    def send_arming_request(self, do_arm: bool):
        """
        Send system arm/disarm request

        Args:
            do_arm (bool): True = arm the system, False = disarm the system
        """
        pk = CRTPPacket()
        pk.set_header(CRTPPort.PLATFORM, PLATFORM_COMMAND)
        pk.data = (PLATFORM_REQUEST_ARMING, do_arm)
        self._cf.send_packet(pk)

    def get_protocol_version(self):
        """
        Return version of the CRTP protocol
        """
        return self._protocolVersion

    def _request_protocol_version(self):
        # Sending a sink request to detect if the connected Crazyflie
        # supports protocol versioning
        pk = CRTPPacket()
        pk.set_header(CRTPPort.LINKCTRL, LINKSERVICE_SOURCE)
        pk.data = (0,)
        self._cf.send_packet(pk)
        logger.info('Request _request_protocol_version()')

    def _crt_service_callback(self, pk):
        if pk.channel == LINKSERVICE_SOURCE:
            logger.info('_crt_service_callback')
            # If the sink contains a magic string, get the protocol version,
            # otherwise -1
            if pk.data[:18].decode('utf8') == 'Bitcraze Crazyflie':
                pk = CRTPPacket()
                pk.set_header(CRTPPort.PLATFORM, VERSION_COMMAND)
                pk.data = (VERSION_GET_PROTOCOL, )
                logger.info('Request protocol version')
                self._cf.send_packet(pk)
            else:
                self._protocolVersion = -1
                logger.info('Protocol version (crt): {}'.format(self.get_protocol_version()))
                self._callback()

    def _platform_callback(self, pk):
        if pk.channel == VERSION_COMMAND:
            logger.info('_platform_callback')

            if pk.data[0] == VERSION_GET_PROTOCOL:
                self._protocolVersion = pk.data[1]
                logger.info('Protocol version (platform): {}'.format(self.get_protocol_version()))
                self._callback()
