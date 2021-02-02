# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2020 Bitcraze AB
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
This class is used to turn the power of the Crazyflie on and off via
a Crazyradio.
"""
import time

import cflib.crtp
from cflib.crtp.crtpstack import CRTPPacket


class PowerSwitch:
    BOOTLOADER_CMD_ALLOFF = 0x01
    BOOTLOADER_CMD_SYSOFF = 0x02
    BOOTLOADER_CMD_SYSON = 0x03

    def __init__(self, uri):
        uri_augmented = uri+"[noSafelink][noAutoPing][noAckFilter]"
        self.link = cflib.crtp.get_link_driver(uri_augmented)

    def platform_power_down(self):
        """ Power down the platform, both NRF and STM MCUs.
            Same as turning off the platform with the power button."""
        self._send(self.BOOTLOADER_CMD_ALLOFF)

    def stm_power_down(self):
        """ Power down the STM MCU, the NRF will still be powered and handle
            basic radio communication. The STM can be restarted again remotely.
            Note: the power to expansion decks is also turned off. """
        self._send(self.BOOTLOADER_CMD_SYSOFF)

    def stm_power_up(self):
        """ Power up (boot) the STM MCU and decks."""
        self._send(self.BOOTLOADER_CMD_SYSON)

    def stm_power_cycle(self):
        """ Restart the STM MCU by powering it off and on.
            Expansion decks will also be rebooted."""
        self.stm_power_down()
        time.sleep(1)
        self.stm_power_up()

    def _send(self, cmd):
        # make sure receive queue is empty
        while True:
            pk = self.link.receive_packet(0)
            if not pk:
                break
        # send command (will be repeated until acked)
        pk = CRTPPacket(0xFF, [0xfe, cmd])

        # wait until ack was received
        while True:
            self.link.send_packet(pk)
            pk = self.link.receive_packet(0.1)
            if pk:
                break
