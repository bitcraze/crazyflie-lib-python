# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2018 Bitcraze AB
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
The PositionHlCommander is used to make it easy to write scripts that moves the
Crazyflie around. Some sort of positioning support is required, for
instance the Loco Positioning System. The implementation uses the High Level
Commander and position setpoints.

The API contains a set of primitives that are easy to understand and use, such
as "go forward" or "turn around".

The PositionHlCommander can be used as context manager using the with keyword.
In this mode of operation takeoff and landing is executed when the context is
created/closed.
"""
import math
import time

from cflib.crazyflie.syncCrazyflie import SyncCrazyflie


class PositionHlCommander:
    """The position High Level Commander"""

    CONTROLLER_PID = 1
    CONTROLLER_MELLINGER = 2

    DEFAULT = None

    def __init__(self, crazyflie,
                 x=0.0, y=0.0, z=0.0,
                 default_velocity=0.5,
                 default_height=0.5,
                 controller=CONTROLLER_PID):
        """
        Construct an instance of a PositionHlCommander

        :param crazyflie: a Crazyflie or SyncCrazyflie instance
        :param x: Initial position, x
        :param y: Initial position, y
        :param z: Initial position, z
        :param default_velocity: the default velocity to use
        :param default_height: the default height to fly at
        :param controller: Which underlying controller to use
        """
        if isinstance(crazyflie, SyncCrazyflie):
            self._cf = crazyflie.cf
        else:
            self._cf = crazyflie

        self._default_velocity = default_velocity
        self._default_height = default_height
        self._controller = controller

        self._x = x
        self._y = y
        self._z = z

        self._is_flying = False

    def take_off(self, height=DEFAULT, velocity=DEFAULT):
        """
        Takes off, that is starts the motors, goes straight up and hovers.
        Do not call this function if you use the with keyword. Take off is
        done automatically when the context is created.

        :param height: the height (meters) to hover at. None uses the default
                       height set when constructed.
        :param velocity: the velocity (meters/second) when taking off
        :return:
        """
        if self._is_flying:
            raise Exception('Already flying')

        if not self._cf.is_connected():
            raise Exception('Crazyflie is not connected')

        self._is_flying = True
        self._reset_position_estimator()
        self._activate_controller()
        self._activate_high_level_commander()
        self._hl_commander = self._cf.high_level_commander

        height = self._height(height)

        duration_s = height / self._velocity(velocity)
        self._hl_commander.takeoff(height, duration_s)
        time.sleep(duration_s)
        self._z = height

    def land(self, velocity=DEFAULT):
        """
        Go straight down and turn off the motors.

        Do not call this function if you use the with keyword. Landing is
        done automatically when the context goes out of scope.

        :param velocity: The velocity (meters/second) when going down
        :return:
        """
        if self._is_flying:
            duration_s = self._z / self._velocity(velocity)
            self._hl_commander.land(0, duration_s)
            time.sleep(duration_s)
            self._z = 0.0

            self._hl_commander.stop()
            self._is_flying = False

    def __enter__(self):
        self.take_off()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.land()

    def left(self, distance_m, velocity=DEFAULT):
        """
        Go left

        :param distance_m: the distance to travel (meters)
        :param velocity: the velocity of the motion (meters/second)
        :return:
        """
        self.move_distance(0.0, distance_m, 0.0, velocity)

    def right(self, distance_m, velocity=DEFAULT):
        """
        Go right

        :param distance_m: the distance to travel (meters)
        :param velocity: the velocity of the motion (meters/second)
        :return:
        """
        self.move_distance(0.0, -distance_m, 0.0, velocity)

    def forward(self, distance_m, velocity=DEFAULT):
        """
        Go forward

        :param distance_m: the distance to travel (meters)
        :param velocity: the velocity of the motion (meters/second)
        :return:
        """
        self.move_distance(distance_m, 0.0, 0.0, velocity)

    def back(self, distance_m, velocity=DEFAULT):
        """
        Go backwards

        :param distance_m: the distance to travel (meters)
        :param velocity: the velocity of the motion (meters/second)
        :return:
        """
        self.move_distance(-distance_m, 0.0, 0.0, velocity)

    def up(self, distance_m, velocity=DEFAULT):
        """
        Go up

        :param distance_m: the distance to travel (meters)
        :param velocity: the velocity of the motion (meters/second)
        :return:
        """
        self.move_distance(0.0, 0.0, distance_m, velocity)

    def down(self, distance_m, velocity=DEFAULT):
        """
        Go down

        :param distance_m: the distance to travel (meters)
        :param velocity: the velocity of the motion (meters/second)
        :return:
        """
        self.move_distance(0.0, 0.0, -distance_m, velocity)

    def move_distance(self, distance_x_m, distance_y_m, distance_z_m,
                      velocity=DEFAULT):
        """
        Move in a straight line.
        positive X is forward
        positive Y is left
        positive Z is up

        :param distance_x_m: The distance to travel along the X-axis (meters)
        :param distance_y_m: The distance to travel along the Y-axis (meters)
        :param distance_z_m: The distance to travel along the Z-axis (meters)
        :param velocity: the velocity of the motion (meters/second)
        :return:
        """

        x = self._x + distance_x_m
        y = self._y + distance_y_m
        z = self._z + distance_z_m

        self.go_to(x, y, z, velocity)

    def go_to(self, x, y, z=DEFAULT, velocity=DEFAULT):
        """
        Go to a position

        :param x: X coordinate
        :param y: Y coordinate
        :param z: Z coordinate
        :param velocity: the velocity (meters/second)
        :return:
        """

        z = self._height(z)

        dx = x - self._x
        dy = y - self._y
        dz = z - self._z
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        if distance > 0.0:
            duration_s = distance / self._velocity(velocity)
            self._hl_commander.go_to(x, y, z, 0, duration_s)
            time.sleep(duration_s)

            self._x = x
            self._y = y
            self._z = z

    def set_default_velocity(self, velocity):
        """
        Set the default velocity to use in commands when no velocity is defined
        :param velocity: The default velocity (meters/s)
        :return:
        """
        self._default_velocity = velocity

    def set_default_height(self, height):
        """
        Set the default height to use in commands when no height is defined

        :param height: The default height (meters)
        :return:
        """
        self._default_height = height

    def set_controller(self, controller):
        self._controller = controller

    def get_position(self):
        """
        Get the current position
        :return: (x, y, z)
        """
        return self._x, self._y, self._z

    def _reset_position_estimator(self):
        self._cf.param.set_value('kalman.initialX', '{:.2f}'.format(self._x))
        self._cf.param.set_value('kalman.initialY', '{:.2f}'.format(self._y))
        self._cf.param.set_value('kalman.initialZ', '{:.2f}'.format(self._z))

        self._cf.param.set_value('kalman.resetEstimation', '1')
        time.sleep(0.1)
        self._cf.param.set_value('kalman.resetEstimation', '0')
        time.sleep(2)

    def _activate_high_level_commander(self):
        self._cf.param.set_value('commander.enHighLevel', '1')

    def _activate_controller(self):
        value = str(self._controller)
        self._cf.param.set_value('stabilizer.controller', value)

    def _velocity(self, velocity):
        if velocity is self.DEFAULT:
            return self._default_velocity
        return velocity

    def _height(self, height):
        if height is self.DEFAULT:
            return self._default_height
        return height
