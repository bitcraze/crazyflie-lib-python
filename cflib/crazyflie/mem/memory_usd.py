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


class MemoryUsd(MemoryElement):
    def __init__(self, id, type, size, mem_handler):
        """Initialize Memory tester"""
        super(MemoryUsd, self).__init__(id=id, type=type, size=size,
                                           mem_handler=mem_handler)

        self._update_finished_cb = None

        self._data = None

    def new_data(self, mem, start_address, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            logger.info('Recived uSD data')
            #print('Reading memory data {}'.format(data))
            self._data = data

    def read_data(self, start_address, size, update_finished_cb):
        """Request an update of the memory content"""
        if not self._update_finished_cb:
            self._update_finished_cb = update_finished_cb
            logger.debug('Reading memory {}'.format(self.id))
            self.mem_handler.read(self, start_address, size)
            
    def disconnect(self):
        self._update_finished_cb = None
