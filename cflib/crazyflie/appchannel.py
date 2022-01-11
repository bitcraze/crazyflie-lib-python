# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2020 Bitcraze AB
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
Data channel to communicate with an application running in the Crazyflie
"""
import logging

import cflib.crazyflie.platformservice
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.callbacks import Caller
# from . import Crazyflie

__author__ = 'Bitcraze AB'
__all__ = ['Appchannel']

logger = logging.getLogger(__name__)


class Appchannel:
    def __init__(self, crazyflie):
        self._cf = crazyflie

        self.packet_received = Caller()

        self._cf.add_port_callback(CRTPPort.PLATFORM,
                                   self._incoming)

    def send_packet(self, data):
        packet = CRTPPacket()
        packet.port = CRTPPort.PLATFORM
        packet.channel = cflib.crazyflie.platformservice.APP_CHANNEL
        packet.data = data
        self._cf.send_packet(packet)

    def _incoming(self, packet: CRTPPacket):
        if packet.channel == cflib.crazyflie.platformservice.APP_CHANNEL:
            self.packet_received.call(packet.data)
