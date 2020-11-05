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
from functools import reduce

from .memory_element import MemoryElement

logger = logging.getLogger(__name__)


EEPROM_TOKEN = b'0xBC'


class I2CElement(MemoryElement):

    def __init__(self, id, type, size, mem_handler):
        super(I2CElement, self).__init__(id=id, type=type, size=size,
                                         mem_handler=mem_handler)
        self._update_finished_cb = None
        self._write_finished_cb = None
        self.elements = {}
        self.valid = False

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            if addr == 0:
                done = False
                # Check for header
                if data[0:4] == EEPROM_TOKEN:
                    logger.debug('Got new data: {}'.format(data))
                    [self.elements['version'],
                     self.elements['radio_channel'],
                     self.elements['radio_speed'],
                     self.elements['pitch_trim'],
                     self.elements['roll_trim']] = struct.unpack('<BBBff',
                                                                 data[4:15])
                    if self.elements['version'] == 0:
                        done = True
                    elif self.elements['version'] == 1:
                        self.datav0 = data
                        self.mem_handler.read(self, 16, 5)
                else:
                    self.valid = False
                    if self._update_finished_cb:
                        self._update_finished_cb(self)
                        self._update_finished_cb = None

            if addr == 16:
                [radio_address_upper, radio_address_lower] = struct.unpack(
                    '<BI', self.datav0[15:16] + data[0:4])
                self.elements['radio_address'] = int(
                    radio_address_upper) << 32 | radio_address_lower

                logger.debug(self.elements)
                data = self.datav0 + data
                done = True

            if done:
                if self._checksum256(data[:len(data) - 1]) == \
                        data[len(data) - 1]:
                    self.valid = True
                if self._update_finished_cb:
                    self._update_finished_cb(self)
                    self._update_finished_cb = None

    def _checksum256(self, st):
        return reduce(lambda x, y: x + y, list(st)) % 256

    def write_data(self, write_finished_cb):
        image = bytearray()
        if self.elements['version'] == 0:
            data = (
                0x00, self.elements['radio_channel'],
                self.elements['radio_speed'],
                self.elements['pitch_trim'], self.elements['roll_trim'])
            image += struct.pack('<BBBff', *data)
        elif self.elements['version'] == 1:
            data = (
                0x01, self.elements['radio_channel'],
                self.elements['radio_speed'],
                self.elements['pitch_trim'], self.elements['roll_trim'],
                self.elements['radio_address'] >> 32,
                self.elements['radio_address'] & 0xFFFFFFFF)
            image += struct.pack('<BBBffBI', *data)
        # Adding some magic:
        image = EEPROM_TOKEN + image
        image += struct.pack('B', self._checksum256(image))

        self._write_finished_cb = write_finished_cb

        self.mem_handler.write(self, 0x00,
                               struct.unpack('B' * len(image), image))

    def update(self, update_finished_cb):
        """Request an update of the memory content"""
        if not self._update_finished_cb:
            self._update_finished_cb = update_finished_cb
            self.valid = False
            logger.debug('Updating content of memory {}'.format(self.id))
            # Start reading the header
            self.mem_handler.read(self, 0, 16)

    def write_done(self, mem, addr):
        if self._write_finished_cb and mem.id == self.id:
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None

    def disconnect(self):
        self._update_finished_cb = None
        self._write_finished_cb = None
