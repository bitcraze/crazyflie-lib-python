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

from .memory_element import MemoryElement

logger = logging.getLogger(__name__)


class LED:
    """Used to set color/intensity of one LED in the LED-ring"""

    def __init__(self):
        """Initialize to off"""
        self.r = 0
        self.g = 0
        self.b = 0
        self.intensity = 100

    def set(self, r, g, b, intensity=None):
        """Set the R/G/B and optionally intensity in one call"""
        self.r = r
        self.g = g
        self.b = b
        if intensity:
            self.intensity = intensity


class LEDDriverMemory(MemoryElement):
    """Memory interface for using the LED-ring mapped memory for setting RGB
       values for all the LEDs in the ring"""

    def __init__(self, id, type, size, mem_handler):
        """Initialize with 12 LEDs"""
        super(LEDDriverMemory, self).__init__(id=id, type=type, size=size,
                                              mem_handler=mem_handler)
        self._update_finished_cb = None
        self._write_finished_cb = None

        self.leds = []
        for i in range(12):
            self.leds.append(LED())

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            logger.debug(
                "Got new data from the LED driver, but we don't care.")

    def write_data(self, write_finished_cb):
        """Write the saved LED-ring data to the Crazyflie"""
        self._write_finished_cb = write_finished_cb
        data = bytearray()
        for led in self.leds:
            # In order to fit all the LEDs in one radio packet RGB565 is used
            # to compress the colors. The calculations below converts 3 bytes
            # RGB into 2 bytes RGB565. Then shifts the value of each color to
            # LSB, applies the intensity and shifts them back for correct
            # alignment on 2 bytes.
            R5 = ((int)((((int(led.r) & 0xFF) * 249 + 1014) >> 11) & 0x1F) *
                  led.intensity / 100)
            G6 = ((int)((((int(led.g) & 0xFF) * 253 + 505) >> 10) & 0x3F) *
                  led.intensity / 100)
            B5 = ((int)((((int(led.b) & 0xFF) * 249 + 1014) >> 11) & 0x1F) *
                  led.intensity / 100)
            tmp = (int(R5) << 11) | (int(G6) << 5) | (int(B5) << 0)
            data += bytearray((tmp >> 8, tmp & 0xFF))
        self.mem_handler.write(self, 0x00, data, flush_queue=True)

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
            logger.debug('Write to LED driver done')
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None

    def disconnect(self):
        self._update_finished_cb = None
        self._write_finished_cb = None
