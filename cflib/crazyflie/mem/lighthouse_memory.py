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


class LighthouseBsGeometry:
    """Container for geometry data of one Lighthouse base station"""

    SIZE_FLOAT = 4
    SIZE_VECTOR = 3 * SIZE_FLOAT
    SIZE_GEOMETRY = (1 + 3) * SIZE_VECTOR
    SIZE_DATA = 2 * SIZE_GEOMETRY

    def __init__(self):
        self.origin = [0.0, 0.0, 0.0]
        self.rotation_matrix = [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        ]

    def set_from_mem_data(self, data):
        self.origin = self._read_vector(
            data[0 * self.SIZE_VECTOR:1 * self.SIZE_VECTOR])
        self.rotation_matrix = [
            self._read_vector(data[1 * self.SIZE_VECTOR:2 * self.SIZE_VECTOR]),
            self._read_vector(data[2 * self.SIZE_VECTOR:3 * self.SIZE_VECTOR]),
            self._read_vector(data[3 * self.SIZE_VECTOR:4 * self.SIZE_VECTOR]),
        ]

    def add_mem_data(self, data):
        self._add_vector(data, self.origin)
        self._add_vector(data, self.rotation_matrix[0])
        self._add_vector(data, self.rotation_matrix[1])
        self._add_vector(data, self.rotation_matrix[2])

    def _add_vector(self, data, vector):
        data += struct.pack('<fff', vector[0], vector[1], vector[2])

    def _read_vector(self, data):
        x, y, z = struct.unpack('<fff', data)
        return [x, y, z]

    def dump(self):
        print('origin:', self.origin)
        print('rotation matrix: ', self.rotation_matrix)


class LighthouseMemory(MemoryElement):
    """
    Memory interface for lighthouse configuration data
    """

    def __init__(self, id, type, size, mem_handler):
        """Initialize Lighthouse memory"""
        super(LighthouseMemory, self).__init__(id=id, type=type, size=size,
                                               mem_handler=mem_handler)

        self._update_finished_cb = None
        self._write_finished_cb = None

        # Geometry data for two base stations
        self.geometry_data = [
            LighthouseBsGeometry(),
            LighthouseBsGeometry(),
        ]

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            if addr == 0:
                self.geometry_data[0].set_from_mem_data(
                    data[0:LighthouseBsGeometry.SIZE_GEOMETRY])
                self.geometry_data[1].set_from_mem_data(
                    data[LighthouseBsGeometry.SIZE_GEOMETRY:])

                if self._update_finished_cb:
                    self._update_finished_cb(self)
                    self._update_finished_cb = None

    def update(self, update_finished_cb):
        """Request an update of the memory content"""
        if not self._update_finished_cb:
            self._update_finished_cb = update_finished_cb
            logger.debug('Updating content of memory {}'.format(self.id))
            self.mem_handler.read(self, 0, LighthouseBsGeometry.SIZE_DATA)

    def write_data(self, write_finished_cb):
        """Write geometry data to the Crazyflie"""
        self._write_finished_cb = write_finished_cb
        data = bytearray()

        for bs in self.geometry_data:
            bs.add_mem_data(data)

        self.mem_handler.write(self, 0x00, data, flush_queue=True)

    def write_done(self, mem, addr):
        if self._write_finished_cb and mem.id == self.id:
            logger.debug('Write of geometry data done')
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None

    def disconnect(self):
        self._update_finished_cb = None
        self._write_finished_cb = None

    def dump(self):
        for data in self.geometry_data:
            data.dump()
