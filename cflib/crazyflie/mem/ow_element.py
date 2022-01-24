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
import struct
from binascii import crc32

from .memory_element import MemoryElement

logger = logging.getLogger(__name__)


class OWElement(MemoryElement):
    """Memory class with extra functionality for 1-wire memories"""

    element_mapping = {
        1: 'Board name',
        2: 'Board revision',
        3: 'Custom'
    }

    def __init__(self, id, type, size, addr, mem_handler):
        """Initialize the memory with good defaults"""
        super(OWElement, self).__init__(id=id, type=type, size=size,
                                        mem_handler=mem_handler)
        self.addr = addr

        self.valid = False

        self.vid = None
        self.pid = None
        self.name = None
        self.pins = None
        self.elements = {}

        self._update_finished_cb = None
        self._write_finished_cb = None

        self._rev_element_mapping = {}
        for key in list(OWElement.element_mapping.keys()):
            self._rev_element_mapping[OWElement.element_mapping[key]] = key

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            if addr == 0:
                if self._parse_and_check_header(data[0:8]):
                    if self._parse_and_check_elements(data[9:11]):
                        self.valid = True
                        self._update_finished_cb(self)
                        self._update_finished_cb = None
                    else:
                        # We need to fetch the elements, find out the length
                        (elem_ver, elem_len) = struct.unpack('BB', data[8:10])
                        self.mem_handler.read(self, 8, elem_len + 3)
                else:
                    # Call the update if the CRC check of the header fails,
                    # we're done here
                    if self._update_finished_cb:
                        self._update_finished_cb(self)
                        self._update_finished_cb = None
            elif addr == 0x08:
                if self._parse_and_check_elements(data):
                    self.valid = True
                if self._update_finished_cb:
                    self._update_finished_cb(self)
                    self._update_finished_cb = None

    def _parse_and_check_elements(self, data):
        """
        Parse and check the CRC and length of the elements part of the memory
        """
        crc = data[-1]
        test_crc = crc32(data[:-1]) & 0x0ff
        elem_data = data[2:-1]
        if test_crc == crc:
            while len(elem_data) > 0:
                (eid, elen) = struct.unpack('BB', elem_data[:2])
                self.elements[self.element_mapping[eid]] = \
                    elem_data[2:2 + elen].decode('ISO-8859-1')
                elem_data = elem_data[2 + elen:]
            return True
        return False

    def write_done(self, mem, addr):
        if self._write_finished_cb:
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None

    def write_data(self, write_finished_cb):
        # First generate the header part
        header_data = struct.pack('<BIBB', 0xEB, self.pins, self.vid, self.pid)
        header_crc = crc32(header_data) & 0x0ff
        header_data += struct.pack('B', header_crc)

        # Now generate the elements part
        elem = bytearray()
        logger.debug(list(self.elements.keys()))
        for element in reversed(list(self.elements.keys())):
            elem_string = self.elements[element]
            key_encoding = self._rev_element_mapping[element]
            elem += struct.pack('BB', key_encoding, len(elem_string))
            elem += bytearray(elem_string.encode('ISO-8859-1'))

        elem_data = struct.pack('BB', 0x00, len(elem))
        elem_data += elem
        elem_crc = crc32(elem_data) & 0x0ff
        elem_data += struct.pack('B', elem_crc)

        data = header_data + elem_data

        self.mem_handler.write(self, 0x00,
                               struct.unpack('B' * len(data), data))

        self._write_finished_cb = write_finished_cb

    def erase(self, write_finished_cb):
        erase_data = bytes([0xFF] * 112)
        self.mem_handler.write(self, 0x00,
                               struct.unpack('B' * len(erase_data),
                                             erase_data))

        self._write_finished_cb = write_finished_cb

    def update(self, update_finished_cb):
        """Request an update of the memory content"""
        if not self._update_finished_cb:
            self._update_finished_cb = update_finished_cb
            self.valid = False
            logger.debug('Updating content of memory {}'.format(self.id))
            # Start reading the header
            self.mem_handler.read(self, 0, 11)

    def _parse_and_check_header(self, data):
        """Parse and check the CRC of the header part of the memory"""
        (start, self.pins, self.vid, self.pid, crc) = struct.unpack('<BIBBB',
                                                                    data)
        test_crc = crc32(data[:-1]) & 0x0ff
        if start == 0xEB and crc == test_crc:
            return True
        return False

    def __str__(self):
        """Generate debug string for memory"""
        return ('OW {} ({:02X}:{:02X}): {}'.format(
            self.addr, self.vid, self.pid, self.elements))

    def disconnect(self):
        self._update_finished_cb = None
        self._write_finished_cb = None
