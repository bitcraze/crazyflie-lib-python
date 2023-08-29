#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2023 Bitcraze AB
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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
Used for sending control setpoints to the Crazyflie
"""
import struct

from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.encoding import compress_quaternion

__author__ = 'Bitcraze AB'
__all__ = ['Commander']

SET_SETPOINT_CHANNEL = 0
META_COMMAND_CHANNEL = 1

TYPE_STOP = 0
TYPE_VELOCITY_WORLD = 1
TYPE_ZDISTANCE = 2
TYPE_HOVER = 5
TYPE_FULL_STATE = 6
TYPE_POSITION = 7

TYPE_META_COMMAND_NOTIFY_SETPOINT_STOP = 0


class Commander():
    """
    Used for sending control setpoints to the Crazyflie
    """

    def __init__(self, crazyflie=None):
        """
        Initialize the commander object. By default the commander is in
        +-mode (not x-mode).
        """
        self._cf = crazyflie
        self._x_mode = False

    def set_client_xmode(self, enabled):
        """
        Enable/disable the client side X-mode. When enabled this recalculates
        the setpoints before sending them to the Crazyflie.
        """
        self._x_mode = enabled

    def send_setpoint(self, roll, pitch, yawrate, thrust):
        """
        Send a new control setpoint for roll/pitch/yaw_Rate/thrust to the copter.

        The meaning of these values is depended on the mode of the RPYT commander in the firmware
        Default settings are Roll, pitch, yawrate and thrust

        roll,  pitch are in degrees
        yawrate is in degrees/s
        thrust is an integer value ranging from 10001 (next to no power) to 60000 (full power)
        """
        if thrust > 0xFFFF or thrust < 0:
            raise ValueError('Thrust must be between 0 and 0xFFFF')

        if self._x_mode:
            roll, pitch = 0.707 * (roll - pitch), 0.707 * (roll + pitch)

        pk = CRTPPacket()
        pk.port = CRTPPort.COMMANDER
        pk.data = struct.pack('<fffH', roll, -pitch, yawrate, thrust)
        self._cf.send_packet(pk)

    def send_notify_setpoint_stop(self, remain_valid_milliseconds=0):
        """
        Sends a packet so that the priority of the current setpoint to the lowest non-disabled value,
        so any new setpoint regardless of source will overwrite it.
        """
        pk = CRTPPacket()
        pk.port = CRTPPort.COMMANDER_GENERIC
        pk.channel = META_COMMAND_CHANNEL
        pk.data = struct.pack('<BI', TYPE_META_COMMAND_NOTIFY_SETPOINT_STOP,
                              remain_valid_milliseconds)
        self._cf.send_packet(pk)

    def send_stop_setpoint(self):
        """
        Send STOP setpoing, stopping the motors and (potentially) falling.
        """
        pk = CRTPPacket()
        pk.port = CRTPPort.COMMANDER_GENERIC
        pk.data = struct.pack('<B', TYPE_STOP)
        self._cf.send_packet(pk)

    def send_velocity_world_setpoint(self, vx, vy, vz, yawrate):
        """
        Send Velocity in the world frame of reference setpoint with yawrate commands

        vx, vy, vz are in m/s
        yawrate is in degrees/s
        """
        pk = CRTPPacket()
        pk.port = CRTPPort.COMMANDER_GENERIC
        pk.channel = SET_SETPOINT_CHANNEL
        pk.data = struct.pack('<Bffff', TYPE_VELOCITY_WORLD,
                              vx, vy, vz, yawrate)
        self._cf.send_packet(pk)

    def send_zdistance_setpoint(self, roll, pitch, yawrate, zdistance):
        """
        Control mode where the height is send as an absolute setpoint (intended
        to be the distance to the surface under the Crazflie), while giving roll,
        pitch and yaw rate commands

        roll, pitch are in degrees
        yawrate is in degrees/s
        zdistance is in meters
        """
        pk = CRTPPacket()
        pk.port = CRTPPort.COMMANDER_GENERIC
        pk.channel = SET_SETPOINT_CHANNEL
        pk.data = struct.pack('<Bffff', TYPE_ZDISTANCE,
                              roll, pitch, yawrate, zdistance)
        self._cf.send_packet(pk)

    def send_hover_setpoint(self, vx, vy, yawrate, zdistance):
        """
        Control mode where the height is send as an absolute setpoint (intended
        to be the distance to the surface under the Crazflie), while giving x, y velocity
        commands in body-fixed coordinates.

        vx,  vy are in m/s
        yawrate is in degrees/s
        zdistance is in meters
        """
        pk = CRTPPacket()
        pk.port = CRTPPort.COMMANDER_GENERIC
        pk.channel = SET_SETPOINT_CHANNEL
        pk.data = struct.pack('<Bffff', TYPE_HOVER,
                              vx, vy, yawrate, zdistance)
        self._cf.send_packet(pk)

    def send_full_state_setpoint(self, pos, vel, acc, orientation, rollrate, pitchrate, yawrate):
        """
        Control mode where the position, velocity, acceleration, orientation and angular
        velocity are sent as absolute (world) values.

        position [x, y, z] are in m
        velocity [vx, vy, vz] are in m/s
        acceleration [ax, ay, az] are in m/s^2
        orientation [qx, qy, qz, qw] are the quaternion components of the orientation
        rollrate, pitchrate, yawrate are in degrees/s
        """
        def vector_to_mm_16bit(vec):
            return int(vec[0] * 1000), int(vec[1] * 1000), int(vec[2] * 1000)

        x, y, z = vector_to_mm_16bit(pos)
        vx, vy, vz = vector_to_mm_16bit(vel)
        ax, ay, az = vector_to_mm_16bit(acc)
        rr, pr, yr = vector_to_mm_16bit([rollrate, pitchrate, yawrate])
        orient_comp = compress_quaternion(orientation)

        pk = CRTPPacket()
        pk.port = CRTPPort.COMMANDER_GENERIC
        pk.data = struct.pack('<BhhhhhhhhhIhhh', TYPE_FULL_STATE,
                              x, y, z,
                              vx, vy, vz,
                              ax, ay, az,
                              orient_comp,
                              rr, pr, yr)
        self._cf.send_packet(pk)

    def send_position_setpoint(self, x, y, z, yaw):
        """
        Control mode where the position is sent as absolute (world) x,y,z coordinate in
        meter and the yaw is the absolute orientation.

        x, y, z are in m
        yaw is in degrees
        """
        pk = CRTPPacket()
        pk.port = CRTPPort.COMMANDER_GENERIC
        pk.channel = SET_SETPOINT_CHANNEL
        pk.data = struct.pack('<Bffff', TYPE_POSITION,
                              x, y, z, yaw)
        self._cf.send_packet(pk)
