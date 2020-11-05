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

from .memory_element import MemoryElement

logger = logging.getLogger(__name__)


class MemoryTester(MemoryElement):
    """
    Memory interface for testing the memory sub system, end to end.

    Usage
    1. To verify reading:
      * Call read_data()
      * Wait for the callback to be called
      * Verify that readValidationSucess is True

    2. To verify writing:
      * Set the parameter 'memTst.resetW' in the CF
      * call write_data()
      * Wait for the callback
      * Read the log var 'memTst.errCntW' from the CF and validate that it
        is 0
    """

    def __init__(self, id, type, size, mem_handler):
        """Initialize Memory tester"""
        super(MemoryTester, self).__init__(id=id, type=type, size=size,
                                           mem_handler=mem_handler)

        self._update_finished_cb = None
        self._write_finished_cb = None

        self.readValidationSucess = True

    def new_data(self, mem, start_address, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            for i in range(len(data)):
                actualValue = struct.unpack('<B', data[i:i + 1])[0]
                expectedValue = (start_address + i) & 0xff

                if (actualValue != expectedValue):
                    address = start_address + i
                    self.readValidationSucess = False
                    logger.error(
                        'Error in data - expected: {}, actual: {}, address:{}',
                        expectedValue, actualValue, address)

                if self._update_finished_cb:
                    self._update_finished_cb(self)
                    self._update_finished_cb = None

    def read_data(self, start_address, size, update_finished_cb):
        """Request an update of the memory content"""
        if not self._update_finished_cb:
            self._update_finished_cb = update_finished_cb
            logger.debug('Reading memory {}'.format(self.id))
            self.mem_handler.read(self, start_address, size)

    def write_data(self, start_address, size, write_finished_cb):
        """Write data to the Crazyflie"""
        self._write_finished_cb = write_finished_cb
        data = bytearray()

        for i in range(size):
            value = (start_address + i) & 0xff
            data += struct.pack('<B', value)

        self.mem_handler.write(self, start_address, data, flush_queue=True)

    def write_done(self, mem, addr):
        if self._write_finished_cb and mem.id == self.id:
            logger.debug('Write of data finished')
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None

    def disconnect(self):
        self._update_finished_cb = None
        self._write_finished_cb = None
