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
This class represents the connection to one or more Loco Positioning Anchors
"""
import struct


class LoPoAnchor():
    LPP_TYPE_POSITION = 1
    LPP_TYPE_REBOOT = 2
    LPP_TYPE_MODE = 3

    REBOOT_TO_BOOTLOADER = 0
    REBOOT_TO_FIRMWARE = 1

    MODE_TWR = 1
    MODE_TDOA = 2  # TDoA 2
    MODE_TDOA3 = 3

    def __init__(self, crazyflie):
        """
        :param crazyflie: A crazyflie object to be used as a bridge to the LoPo
         system."""
        self.crazyflie = crazyflie

    def set_position(self, anchor_id, position):
        """
        Send a packet with a position to one anchor.
        :param anchor_id: The id of the targeted anchor. This is the first byte
        of the anchor address.
        :param position: The position of the anchor, as an array
        """
        x = position[0]
        y = position[1]
        z = position[2]
        data = struct.pack('<Bfff', LoPoAnchor.LPP_TYPE_POSITION, x, y, z)

        self.crazyflie.loc.send_short_lpp_packet(anchor_id, data)

    def reboot(self, anchor_id, mode):
        data = struct.pack('<BB', LoPoAnchor.LPP_TYPE_REBOOT, mode)
        self.crazyflie.loc.send_short_lpp_packet(anchor_id, data)

    def set_mode(self, anchor_id, mode):
        """
        Send a packet to set the anchor mode. If the anchor receive the packet,
        it will change mode and resets.
        """
        data = struct.pack('<BB', LoPoAnchor.LPP_TYPE_MODE, mode)
        self.crazyflie.loc.send_short_lpp_packet(anchor_id, data)
