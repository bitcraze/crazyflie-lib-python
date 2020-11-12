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


class Poly4D:
    class Poly:
        def __init__(self, values=[0.0] * 8):
            self.values = values

    def __init__(self, duration, x=None, y=None, z=None, yaw=None):
        self.duration = duration
        self.x = x if x else self.Poly()
        self.y = y if y else self.Poly()
        self.z = z if z else self.Poly()
        self.yaw = yaw if yaw else self.Poly()


class TrajectoryMemory(MemoryElement):
    """
    Memory interface for trajectories used by the high level commander
    """

    def __init__(self, id, type, size, mem_handler):
        """Initialize trajectory memory"""
        super(TrajectoryMemory, self).__init__(id=id, type=type, size=size,
                                               mem_handler=mem_handler)
        self._write_finished_cb = None
        self._write_failed_cb = None

        # A list of Poly4D objects to write to the Crazyflie
        self.poly4Ds = []

    def write_data(self, write_finished_cb, write_failed_cb=None):
        """Write trajectory data to the Crazyflie"""
        self._write_finished_cb = write_finished_cb
        self._write_failed_cb = write_failed_cb
        data = bytearray()

        for poly4D in self.poly4Ds:
            data += struct.pack('<ffffffff', *poly4D.x.values)
            data += struct.pack('<ffffffff', *poly4D.y.values)
            data += struct.pack('<ffffffff', *poly4D.z.values)
            data += struct.pack('<ffffffff', *poly4D.yaw.values)
            data += struct.pack('<f', poly4D.duration)

        self.mem_handler.write(self, 0x00, data, flush_queue=True)

    def write_done(self, mem, addr):
        if self._write_finished_cb and mem.id == self.id:
            logger.debug('Write trajectory data done')
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None
            self._write_failed_cb = None

    def write_failed(self, mem, addr):
        if mem.id == self.id:
            if self._write_failed_cb:
                logger.debug('Write of trajectory data failed')
                self._write_failed_cb(self, addr)
            self._write_finished_cb = None
            self._write_failed_cb = None

    def disconnect(self):
        self._write_finished_cb = None
