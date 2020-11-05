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


class LEDTimingsDriverMemory(MemoryElement):
    """Memory interface for using the LED-ring mapped memory for setting RGB
       values over time. To upload and run a show sequence of
       the LEDs in the ring"""

    def __init__(self, id, type, size, mem_handler):
        super(LEDTimingsDriverMemory, self).__init__(id=id,
                                                     type=type,
                                                     size=size,
                                                     mem_handler=mem_handler)
        self._update_finished_cb = None
        self._write_finished_cb = None

        self.timings = []

    def add(self, time, rgb, leds=0, fade=False, rotate=0):
        self.timings.append({
            'time': time,
            'rgb': rgb,
            'leds': leds,
            'fade': fade,
            'rotate': rotate
        })

    def write_data(self, write_finished_cb):
        if write_finished_cb is not None:
            self._write_finished_cb = write_finished_cb

        data = []
        for timing in self.timings:
            # In order to fit all the LEDs in one radio packet RGB565 is used
            # to compress the colors. The calculations below converts 3 bytes
            # RGB into 2 bytes RGB565. Then shifts the value of each color to
            # LSB, applies the intensity and shifts them back for correct
            # alignment on 2 bytes.
            R5 = ((int)((((int(timing['rgb']['r']) & 0xFF) * 249 + 1014) >> 11)
                        & 0x1F))
            G6 = ((int)((((int(timing['rgb']['g']) & 0xFF) * 253 + 505) >> 10)
                        & 0x3F))
            B5 = ((int)((((int(timing['rgb']['b']) & 0xFF) * 249 + 1014) >> 11)
                        & 0x1F))
            led = (int(R5) << 11) | (int(G6) << 5) | (int(B5) << 0)
            extra = ((timing['leds']) & 0x0F) | (
                (timing['fade'] << 4) & 0x10) | (
                (timing['rotate'] << 5) & 0xE0)

            if (timing['time'] & 0xFF) != 0 or led != 0 or extra != 0:
                data += [timing['time'] & 0xFF, led >> 8, led & 0xFF, extra]

        data += [0, 0, 0, 0]
        self.mem_handler.write(self, 0x00, bytearray(data), flush_queue=True)

    def write_done(self, mem, addr):
        if mem.id == self.id and self._write_finished_cb:
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None

    def disconnect(self):
        self._update_finished_cb = None
        self._write_finished_cb = None
