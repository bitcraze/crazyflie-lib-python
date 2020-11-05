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


class AnchorData2:
    """Holds data for one anchor"""

    def __init__(self, position=(0.0, 0.0, 0.0), is_valid=False):
        self.position = position
        self.is_valid = is_valid

    def set_from_mem_data(self, data):
        x, y, z, self.is_valid = struct.unpack('<fff?', data)
        self.position = (x, y, z)


class LocoMemory2(MemoryElement):
    """Memory interface for accessing data from the Loco Positioning system
       version 2"""

    SIZE_OF_FLOAT = 4

    # MAX_NR_OF_ANCHORS should be set to the number of anchors
    # supported by the firmware. Preferably short enough to fit into one packet
    MAX_NR_OF_ANCHORS = 16
    ID_LIST_LEN = 1 + MAX_NR_OF_ANCHORS

    ADR_ID_LIST = 0x0000
    ADR_ACTIVE_ID_LIST = 0x1000
    ADR_ANCHOR_BASE = 0x2000

    ANCHOR_PAGE_SIZE = 0x0100
    PAGE_LEN = (3 * SIZE_OF_FLOAT) + 1

    def __init__(self, id, type, size, mem_handler):
        super(LocoMemory2, self).__init__(id=id, type=type, size=size,
                                          mem_handler=mem_handler)
        self._update_ids_finished_cb = None
        self._update_active_ids_finished_cb = None
        self._update_data_finished_cb = None
        self._currently_fetching_index = -1

        self.anchor_ids = []
        self.active_anchor_ids = []
        self.anchor_data = {}
        self.nr_of_anchors = 0
        self.ids_valid = False
        self.active_ids_valid = False
        self.data_valid = False

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            if addr == LocoMemory2.ADR_ID_LIST:
                self._handle_id_list_data(data)
            elif addr == LocoMemory2.ADR_ACTIVE_ID_LIST:
                self._handle_active_id_list_data(data)
            else:
                id = int((addr - LocoMemory2.ADR_ANCHOR_BASE) /
                         LocoMemory2.ANCHOR_PAGE_SIZE)
                self._handle_anchor_data(id, data)

    def update_id_list(self, update_ids_finished_cb):
        """Request an update of the id list"""
        if not self._update_ids_finished_cb:
            self._update_ids_finished_cb = update_ids_finished_cb
            self.anchor_ids = []
            self.active_anchor_ids = []
            self.anchor_data = {}

            self.nr_of_anchors = 0
            self.ids_valid = False
            self.data_valid = False

            logger.debug('Updating ids of memory {}'.format(self.id))

            # Start reading the header
            self.mem_handler.read(self, LocoMemory2.ADR_ID_LIST,
                                  LocoMemory2.ID_LIST_LEN)

    def update_active_id_list(self, update_active_ids_finished_cb):
        """Request an update of the active id list"""
        if not self._update_active_ids_finished_cb:
            self._update_active_ids_finished_cb = update_active_ids_finished_cb
            self.active_anchor_ids = []

            self.active_ids_valid = False

            logger.debug('Updating active ids of memory {}'.format(self.id))

            # Start reading the header
            self.mem_handler.read(self, LocoMemory2.ADR_ACTIVE_ID_LIST,
                                  LocoMemory2.ID_LIST_LEN)

    def update_data(self, update_data_finished_cb):
        """Request an update of the anchor data"""
        if not self._update_data_finished_cb and self.nr_of_anchors > 0:
            self._update_data_finished_cb = update_data_finished_cb
            self.anchor_data = {}

            self.data_valid = False
            self._nr_of_anchors_to_fetch = self.nr_of_anchors

            logger.debug('Updating anchor data of memory {}'.format(self.id))

            # Start reading the first anchor
            self._currently_fetching_index = 0
            self._request_page(self.anchor_ids[self._currently_fetching_index])

    def disconnect(self):
        self._update_ids_finished_cb = None
        self._update_data_finished_cb = None

    def _handle_id_list_data(self, data):
        self.nr_of_anchors = data[0]
        for i in range(self.nr_of_anchors):
            self.anchor_ids.append(data[1 + i])
        self.ids_valid = True

        if self._update_ids_finished_cb:
            self._update_ids_finished_cb(self)
            self._update_ids_finished_cb = None

    def _handle_active_id_list_data(self, data):
        count = data[0]
        for i in range(count):
            self.active_anchor_ids.append(data[1 + i])
        self.active_ids_valid = True

        if self._update_active_ids_finished_cb:
            self._update_active_ids_finished_cb(self)
            self._update_active_ids_finished_cb = None

    def _handle_anchor_data(self, id, data):
        anchor = AnchorData2()
        anchor.set_from_mem_data(data)
        self.anchor_data[id] = anchor

        self._currently_fetching_index += 1
        if self._currently_fetching_index < self.nr_of_anchors:
            self._request_page(self.anchor_ids[self._currently_fetching_index])
        else:
            self.data_valid = True
            if self._update_data_finished_cb:
                self._update_data_finished_cb(self)
                self._update_data_finished_cb = None

    def _request_page(self, page):
        addr = LocoMemory2.ADR_ANCHOR_BASE + \
            LocoMemory2.ANCHOR_PAGE_SIZE * page
        self.mem_handler.read(self, addr, LocoMemory2.PAGE_LEN)
