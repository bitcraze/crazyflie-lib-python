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


class AnchorData:
    """Holds data for one anchor"""

    def __init__(self, position=(0.0, 0.0, 0.0), is_valid=False):
        self.position = position
        self.is_valid = is_valid

    def set_from_mem_data(self, data):
        x, y, z, self.is_valid = struct.unpack('<fff?', data)
        self.position = (x, y, z)


class LocoMemory(MemoryElement):
    """Memory interface for accessing data from the Loco Positioning system"""

    SIZE_OF_FLOAT = 4
    MEM_LOCO_INFO = 0x0000
    MEM_LOCO_INFO_LEN = 1
    MEM_LOCO_ANCHOR_BASE = 0x1000
    MEM_LOCO_ANCHOR_PAGE_SIZE = 0x0100
    MEM_LOCO_PAGE_LEN = (3 * SIZE_OF_FLOAT) + 1

    def __init__(self, id, type, size, mem_handler):
        super(LocoMemory, self).__init__(id=id, type=type, size=size,
                                         mem_handler=mem_handler)
        self._update_finished_cb = None

        self.anchor_data = []
        self.nr_of_anchors = 0
        self.valid = False

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        done = False
        if mem.id == self.id:
            if addr == LocoMemory.MEM_LOCO_INFO:
                self.nr_of_anchors = data[0]
                if self.nr_of_anchors == 0:
                    done = True
                else:
                    self.anchor_data = \
                        [AnchorData() for _ in range(self.nr_of_anchors)]
                    self._request_page(0)
            else:
                page = int((addr - LocoMemory.MEM_LOCO_ANCHOR_BASE) /
                           LocoMemory.MEM_LOCO_ANCHOR_PAGE_SIZE)

                self.anchor_data[page].set_from_mem_data(data)

                next_page = page + 1
                if next_page < self.nr_of_anchors:
                    self._request_page(next_page)
                else:
                    done = True

        if done:
            self.valid = True
            if self._update_finished_cb:
                self._update_finished_cb(self)
                self._update_finished_cb = None

    def update(self, update_finished_cb):
        """Request an update of the memory content"""
        if not self._update_finished_cb:
            self._update_finished_cb = update_finished_cb
            self.anchor_data = []
            self.nr_of_anchors = 0
            self.valid = False
            logger.debug('Updating content of memory {}'.format(self.id))

            # Start reading the header
            self.mem_handler.read(self, LocoMemory.MEM_LOCO_INFO,
                                  LocoMemory.MEM_LOCO_INFO_LEN)

    def disconnect(self):
        self._update_finished_cb = None

    def _request_page(self, page):
        addr = LocoMemory.MEM_LOCO_ANCHOR_BASE + \
            LocoMemory.MEM_LOCO_ANCHOR_PAGE_SIZE * page
        self.mem_handler.read(self, addr, LocoMemory.MEM_LOCO_PAGE_LEN)
