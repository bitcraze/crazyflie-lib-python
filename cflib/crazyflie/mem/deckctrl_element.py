# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2026 Bitcraze AB
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
import struct

from .memory_element import MemoryElement

logger = logging.getLogger(__name__)

# DeckCtrl memory layout at offset 0x0000 (32 bytes):
# Offset | Size | Field
# -------|------|----------------
# 0x00   |  2   | Magic (0xBCDC big-endian)
# 0x02   |  1   | Major Version
# 0x03   |  1   | Minor Version
# 0x04   |  1   | Vendor ID
# 0x05   |  1   | Product ID
# 0x06   |  1   | Board Revision
# 0x07   | 15   | Product Name (null-terminated)
# 0x16   |  1   | Year
# 0x17   |  1   | Month
# 0x18   |  1   | Day
# 0x19   |  6   | Reserved
# 0x1F   |  1   | Checksum (makes sum of bytes 0-31 = 0)

DECKCTRL_MAGIC = 0xBCDC
DECKCTRL_INFO_SIZE = 32


class DeckCtrlElement(MemoryElement):
    """Memory class with functionality for DeckCtrl memories"""

    def __init__(self, id, type, size, mem_handler):
        """Initialize the memory with good defaults"""
        super(DeckCtrlElement, self).__init__(id=id, type=type, size=size,
                                              mem_handler=mem_handler)

        self.valid = False

        self.vid = None
        self.pid = None
        self.name = None
        self.revision = None
        self.fw_version_major = None
        self.fw_version_minor = None
        self.elements = {}

        self._update_finished_cb = None

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            if addr == 0:
                if self._parse_and_check_info(data[:DECKCTRL_INFO_SIZE]):
                    self.valid = True
                if self._update_finished_cb:
                    self._update_finished_cb(self)
                    self._update_finished_cb = None

    def read_failed(self, mem, addr):
        """Callback for when a memory read fails"""
        if mem.id == self.id:
            logger.warning('DeckCtrl memory read failed for id {}'.format(self.id))
            if self._update_finished_cb:
                self._update_finished_cb(self)
                self._update_finished_cb = None

    def _parse_and_check_info(self, data):
        """Parse and validate the DeckCtrl info block"""
        if len(data) < DECKCTRL_INFO_SIZE:
            logger.warning('DeckCtrl data too short: {} bytes'.format(len(data)))
            return False

        # Validate checksum (sum of all 32 bytes should be 0 mod 256)
        checksum = sum(data[:DECKCTRL_INFO_SIZE]) & 0xFF
        if checksum != 0:
            logger.warning('DeckCtrl checksum failed: {}'.format(checksum))
            return False

        # Parse the header
        magic = struct.unpack('>H', data[0:2])[0]  # Big-endian
        if magic != DECKCTRL_MAGIC:
            logger.warning('DeckCtrl magic mismatch: 0x{:04X}'.format(magic))
            return False

        self.fw_version_major = data[2]
        self.fw_version_minor = data[3]
        self.vid = data[4]
        self.pid = data[5]
        self.revision = chr(data[6]) if data[6] != 0 else ''

        # Product name is 15 bytes, null-terminated
        name_bytes = data[7:22]
        null_pos = name_bytes.find(0)
        if null_pos >= 0:
            name_bytes = name_bytes[:null_pos]
        self.name = name_bytes.decode('ISO-8859-1')

        # Manufacturing date
        year = data[22]
        month = data[23]
        day = data[24]

        # Populate elements dict for compatibility with OWElement interface
        self.elements['Board name'] = self.name
        self.elements['Board revision'] = self.revision
        if year != 0 or month != 0 or day != 0:
            self.elements['Manufacturing date'] = '{:04d}-{:02d}-{:02d}'.format(
                2000 + year, month, day)
        self.elements['Firmware version'] = '{}.{}'.format(
            self.fw_version_major, self.fw_version_minor)

        return True

    def update(self, update_finished_cb):
        """Request an update of the memory content"""
        if not self._update_finished_cb:
            self._update_finished_cb = update_finished_cb
            self.valid = False
            logger.debug('Updating content of DeckCtrl memory {}'.format(self.id))
            # Read the 32-byte info block
            self.mem_handler.read(self, 0, DECKCTRL_INFO_SIZE)

    def __str__(self):
        """Generate debug string for memory"""
        return ('DeckCtrl ({:02X}:{:02X}): {}'.format(
            self.vid or 0, self.pid or 0, self.elements))

    def disconnect(self):
        self._update_finished_cb = None
