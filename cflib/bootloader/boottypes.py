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
Bootloading utilities for the Crazyflie.
"""

__author__ = 'Bitcraze AB'
__all__ = ['BootVersion', 'TargetTypes', 'Target']


class BootVersion:
    CF1_PROTO_VER_0 = 0x00
    CF1_PROTO_VER_1 = 0x01
    CF2_PROTO_VER = 0x10

    @staticmethod
    def to_ver_string(ver):
        if (ver == BootVersion.CF1_PROTO_VER_0 or ver == BootVersion.
                CF1_PROTO_VER_1):
            return 'Crazyflie Nano Quadcopter (1.0)'
        if ver == BootVersion.CF2_PROTO_VER:
            return 'Crazyflie 2.0'
        return 'Unknown'

    @staticmethod
    def is_cf2(ver):
        return ver == BootVersion.CF2_PROTO_VER


class TargetTypes:
    STM32 = 0xFF
    NRF51 = 0xFE

    @staticmethod
    def to_string(target):
        if target == TargetTypes.STM32:
            return 'stm32'
        if target == TargetTypes.NRF51:
            return 'nrf51'
        return 'Unknown'

    @staticmethod
    def from_string(name):
        if name == 'stm32':
            return TargetTypes.STM32
        if name == 'nrf51':
            return TargetTypes.NRF51
        return 0


class Target:

    def __init__(self, id):
        self.id = id
        self.protocol_version = 0xFF
        self.page_size = 0
        self.buffer_pages = 0
        self.flash_pages = 0
        self.start_page = 0
        self.cpuid = ''
        self.data = None

    def __str__(self):
        ret = ''
        ret += 'Target info: {} (0x{:X})\n'.format(
            TargetTypes.to_string(self.id), self.id)
        ret += 'Flash pages: %d | Page size: %d | Buffer pages: %d |' \
               ' Start page: %d\n' % (self.flash_pages, self.page_size,
                                      self.buffer_pages, self.start_page)
        ret += '%d KBytes of flash available for firmware image.' % (
            (self.flash_pages - self.start_page) * self.page_size / 1024)
        return ret
