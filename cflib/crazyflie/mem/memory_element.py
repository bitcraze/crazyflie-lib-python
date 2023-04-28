# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2019 - 2020 Bitcraze AB
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
import logging

logger = logging.getLogger(__name__)


class MemoryElement(object):
    """A memory """

    TYPE_I2C = 0
    TYPE_1W = 1
    TYPE_DRIVER_LED = 0x10
    TYPE_LOCO = 0x11
    TYPE_TRAJ = 0x12
    TYPE_LOCO2 = 0x13
    TYPE_LH = 0x14
    TYPE_MEMORY_TESTER = 0x15
    TYPE_DRIVER_LEDTIMING = 0x17
    TYPE_APP = 0x18
    TYPE_DECK_MEMORY = 0x19
    TYPE_DECK_MULTIRANGER = 0x1A
    TYPE_DECK_PAA3905 = 0x1B

    def __init__(self, id, type, size, mem_handler):
        """Initialize the element with default values"""
        self.id = id
        self.type = type
        self.size = size
        self.mem_handler = mem_handler

    @staticmethod
    def type_to_string(t):
        """Get string representation of memory type"""
        if t == MemoryElement.TYPE_I2C:
            return 'I2C'
        if t == MemoryElement.TYPE_1W:
            return '1-wire'
        if t == MemoryElement.TYPE_DRIVER_LEDTIMING:
            return 'LED memory driver'
        if t == MemoryElement.TYPE_DRIVER_LED:
            return 'LED driver'
        if t == MemoryElement.TYPE_LOCO:
            return 'Loco Positioning'
        if t == MemoryElement.TYPE_TRAJ:
            return 'Trajectory'
        if t == MemoryElement.TYPE_LOCO2:
            return 'Loco Positioning 2'
        if t == MemoryElement.TYPE_LH:
            return 'Lighthouse positioning'
        if t == MemoryElement.TYPE_MEMORY_TESTER:
            return 'Memory tester'
        return 'Unknown'

    def new_data(self, mem, addr, data):
        logger.debug('New data, but not OW mem')

    def __str__(self):
        """Generate debug string for memory"""
        return ('Memory: id={}, type={}, size={}'.format(
            self.id, MemoryElement.type_to_string(self.type), self.size))
