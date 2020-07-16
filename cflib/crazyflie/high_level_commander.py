#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2018-2020 Bitcraze AB
#
#  Crazyflie Nano Quadcopter Client
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
"""
Used for sending high level setpoints to the Crazyflie
"""
import struct

from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort

__author__ = 'Bitcraze AB'
__all__ = ['HighLevelCommander']


class HighLevelCommander():
    """
    Used for sending high level setpoints to the Crazyflie
    """

    COMMAND_SET_GROUP_MASK = 0
    COMMAND_STOP = 3
    COMMAND_GO_TO = 4
    COMMAND_START_TRAJECTORY = 5
    COMMAND_DEFINE_TRAJECTORY = 6
    COMMAND_TAKEOFF_2 = 7
    COMMAND_LAND_2 = 8

    ALL_GROUPS = 0

    TRAJECTORY_LOCATION_MEM = 1
    TRAJECTORY_TYPE_POLY4D = 0

    def __init__(self, crazyflie=None):
        """
        Initialize the object.
        """
        self._cf = crazyflie

    def set_group_mask(self, group_mask=ALL_GROUPS):
        """
        Set the group mask that the Crazyflie belongs to

        :param group_mask: mask for which groups this CF belongs to
        """
        self._send_packet(struct.pack('<BB',
                                      self.COMMAND_SET_GROUP_MASK,
                                      group_mask))

    def takeoff(self, absolute_height_m, duration_s, group_mask=ALL_GROUPS,
                yaw=0.0):
        """
        vertical takeoff from current x-y position to given height

        :param absolute_height_m: absolute (m)
        :param duration_s: time it should take until target height is
                           reached (s)
        :param group_mask: mask for which CFs this should apply to
        :param yaw: yaw (rad). Use current yaw if set to None.
        """
        target_yaw = yaw
        useCurrentYaw = False
        if yaw is None:
            target_yaw = 0.0
            useCurrentYaw = True

        self._send_packet(struct.pack('<BBff?f',
                                      self.COMMAND_TAKEOFF_2,
                                      group_mask,
                                      absolute_height_m,
                                      target_yaw,
                                      useCurrentYaw,
                                      duration_s))

    def land(self, absolute_height_m, duration_s, group_mask=ALL_GROUPS,
             yaw=0.0):
        """
        vertical land from current x-y position to given height

        :param absolute_height_m: absolute (m)
        :param duration_s: time it should take until target height is
                           reached (s)
        :param group_mask: mask for which CFs this should apply to
        :param yaw: yaw (rad). Use current yaw if set to None.
        """
        target_yaw = yaw
        useCurrentYaw = False
        if yaw is None:
            target_yaw = 0.0
            useCurrentYaw = True

        self._send_packet(struct.pack('<BBff?f',
                                      self.COMMAND_LAND_2,
                                      group_mask,
                                      absolute_height_m,
                                      target_yaw,
                                      useCurrentYaw,
                                      duration_s))

    def stop(self, group_mask=ALL_GROUPS):
        """
        stops the current trajectory (turns off the motors)

        :param group_mask: mask for which CFs this should apply to
        :return:
        """
        self._send_packet(struct.pack('<BB',
                                      self.COMMAND_STOP,
                                      group_mask))

    def go_to(self, x, y, z, yaw, duration_s, relative=False,
              group_mask=ALL_GROUPS):
        """
        Go to an absolute or relative position

        :param x: x (m)
        :param y: y (m)
        :param z: z (m)
        :param yaw: yaw (radians)
        :param duration_s: time it should take to reach the position (s)
        :param relative: True if x, y, z is relative to the current position
        :param group_mask: mask for which CFs this should apply to
        """
        self._send_packet(struct.pack('<BBBfffff',
                                      self.COMMAND_GO_TO,
                                      group_mask,
                                      relative,
                                      x, y, z,
                                      yaw,
                                      duration_s))

    def start_trajectory(self, trajectory_id, time_scale=1.0, relative=False,
                         reversed=False, group_mask=ALL_GROUPS):
        """
        starts executing a specified trajectory

        :param trajectory_id: id of the trajectory (previously defined by
               define_trajectory)
        :param time_scale: time factor; 1.0 = original speed;
                                        >1.0: slower;
                                        <1.0: faster
        :param relative: set to True, if trajectory should be shifted to
               current setpoint
        :param reversed: set to True, if trajectory should be executed in
               reverse
        :param group_mask: mask for which CFs this should apply to
        :return:
        """
        self._send_packet(struct.pack('<BBBBBf',
                                      self.COMMAND_START_TRAJECTORY,
                                      group_mask,
                                      relative,
                                      reversed,
                                      trajectory_id,
                                      time_scale))

    def define_trajectory(self, trajectory_id, offset, n_pieces):
        """
        Define a trajectory that has previously been uploaded to memory.

        :param trajectory_id: The id of the trajectory
        :param offset: offset in uploaded memory
        :param n_pieces: Nr of pieces in the trajectory
        :return:
        """
        self._send_packet(struct.pack('<BBBBIB',
                                      self.COMMAND_DEFINE_TRAJECTORY,
                                      trajectory_id,
                                      self.TRAJECTORY_LOCATION_MEM,
                                      self.TRAJECTORY_TYPE_POLY4D,
                                      offset,
                                      n_pieces))

    def _send_packet(self, data):
        pk = CRTPPacket()
        pk.port = CRTPPort.SETPOINT_HL
        pk.data = data
        self._cf.send_packet(pk)
