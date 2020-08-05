# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2017 Bitcraze AB
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
The MotionCommander is used to make it easy to write scripts that moves the
Crazyflie around. Some sort of positioning support is required, for instance
the Flow deck.

The motion commander uses velocity setpoints and does not have a notion of
absolute position, the error in position will accumulate over time.

The API contains a set of primitives that are easy to understand and use, such
as "go forward" or "turn around".

There are two flavors of primitives, one that is blocking and returns when
a motion is completed, while the other starts a motion and returns immediately.
In the second variation the user has to stop or change the motion when
appropriate by issuing new commands.

The MotionCommander can be used as context manager using the with keyword. In
this mode of operation takeoff and landing is executed when the context is
created/closed.
"""
import math
import time
from queue import Empty
from queue import Queue
from threading import Thread

from cflib.crazyflie.syncCrazyflie import SyncCrazyflie


class MotionCommander:
    """The motion commander"""
    VELOCITY = 0.2
    RATE = 360.0 / 5

    def __init__(self, crazyflie, default_height=0.3):
        """
        Construct an instance of a MotionCommander

        :param crazyflie: a Crazyflie or SyncCrazyflie instance
        :param default_height: the default height to fly at
        """
        if isinstance(crazyflie, SyncCrazyflie):
            self._cf = crazyflie.cf
        else:
            self._cf = crazyflie

        self.default_height = default_height

        self._is_flying = False
        self._thread = None

    # Distance based primitives

    def take_off(self, height=None, velocity=VELOCITY):
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

        self._thread = _SetPointThread(self._cf)
        self._thread.start()

        if height is None:
            height = self.default_height

        self.up(height, velocity)

    def land(self, velocity=VELOCITY):
        """
        Go straight down and turn off the motors.

        Do not call this function if you use the with keyword. Landing is
        done automatically when the context goes out of scope.

        :param velocity: The velocity (meters/second) when going down
        :return:
        """
        if self._is_flying:
            self.down(self._thread.get_height(), velocity)

            self._thread.stop()
            self._thread = None

            self._cf.commander.send_stop_setpoint()
            self._is_flying = False

    def __enter__(self):
        self.take_off()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.land()

    def left(self, distance_m, velocity=VELOCITY):
        """
        Go left

        :param distance_m: the distance to travel (meters)
        :param velocity: the velocity of the motion (meters/second)
        :return:
        """
        self.move_distance(0.0, distance_m, 0.0, velocity)

    def right(self, distance_m, velocity=VELOCITY):
        """
        Go right

        :param distance_m: the distance to travel (meters)
        :param velocity: the velocity of the motion (meters/second)
        :return:
        """
        self.move_distance(0.0, -distance_m, 0.0, velocity)

    def forward(self, distance_m, velocity=VELOCITY):
        """
        Go forward

        :param distance_m: the distance to travel (meters)
        :param velocity: the velocity of the motion (meters/second)
        :return:
        """
        self.move_distance(distance_m, 0.0, 0.0, velocity)

    def back(self, distance_m, velocity=VELOCITY):
        """
        Go backwards

        :param distance_m: the distance to travel (meters)
        :param velocity: the velocity of the motion (meters/second)
        :return:
        """
        self.move_distance(-distance_m, 0.0, 0.0, velocity)

    def up(self, distance_m, velocity=VELOCITY):
        """
        Go up

        :param distance_m: the distance to travel (meters)
        :param velocity: the velocity of the motion (meters/second)
        :return:
        """
        self.move_distance(0.0, 0.0, distance_m, velocity)

    def down(self, distance_m, velocity=VELOCITY):
        """
        Go down

        :param distance_m: the distance to travel (meters)
        :param velocity: the velocity of the motion (meters/second)
        :return:
        """
        self.move_distance(0.0, 0.0, -distance_m, velocity)

    def turn_left(self, angle_degrees, rate=RATE):
        """
        Turn to the left, staying on the spot

        :param angle_degrees: How far to turn (degrees)
        :param rate: The turning speed (degrees/second)
        :return:
        """
        flight_time = angle_degrees / rate

        self.start_turn_left(rate)
        time.sleep(flight_time)
        self.stop()

    def turn_right(self, angle_degrees, rate=RATE):
        """
        Turn to the right, staying on the spot

        :param angle_degrees: How far to turn (degrees)
        :param rate: The turning speed (degrees/second)
        :return:
        """
        flight_time = angle_degrees / rate

        self.start_turn_right(rate)
        time.sleep(flight_time)
        self.stop()

    def circle_left(self, radius_m, velocity=VELOCITY, angle_degrees=360.0):
        """
        Go in circle, counter clock wise

        :param radius_m: The radius of the circle (meters)
        :param velocity: The velocity along the circle (meters/second)
        :param angle_degrees: How far to go in the circle (degrees)
        :return:
        """
        distance = 2 * radius_m * math.pi * angle_degrees / 360.0
        flight_time = distance / velocity

        self.start_circle_left(radius_m, velocity)
        time.sleep(flight_time)
        self.stop()

    def circle_right(self, radius_m, velocity=VELOCITY, angle_degrees=360.0):
        """
        Go in circle, clock wise

        :param radius_m: The radius of the circle (meters)
        :param velocity: The velocity along the circle (meters/second)
        :param angle_degrees: How far to go in the circle (degrees)
        :return:
        """
        distance = 2 * radius_m * math.pi * angle_degrees / 360.0
        flight_time = distance / velocity

        self.start_circle_right(radius_m, velocity)
        time.sleep(flight_time)
        self.stop()

    def move_distance(self, distance_x_m, distance_y_m, distance_z_m,
                      velocity=VELOCITY):
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
        distance = math.sqrt(distance_x_m * distance_x_m +
                             distance_y_m * distance_y_m +
                             distance_z_m * distance_z_m)
        flight_time = distance / velocity

        velocity_x = velocity * distance_x_m / distance
        velocity_y = velocity * distance_y_m / distance
        velocity_z = velocity * distance_z_m / distance

        self.start_linear_motion(velocity_x, velocity_y, velocity_z)
        time.sleep(flight_time)
        self.stop()

    # Velocity based primitives

    def start_left(self, velocity=VELOCITY):
        """
        Start moving left. This function returns immediately.

        :param velocity: The velocity of the motion (meters/second)
        :return:
        """
        self.start_linear_motion(0.0, velocity, 0.0)

    def start_right(self, velocity=VELOCITY):
        """
        Start moving right. This function returns immediately.

        :param velocity: The velocity of the motion (meters/second)
        :return:
        """
        self.start_linear_motion(0.0, -velocity, 0.0)

    def start_forward(self, velocity=VELOCITY):
        """
        Start moving forward. This function returns immediately.

        :param velocity: The velocity of the motion (meters/second)
        :return:
        """
        self.start_linear_motion(velocity, 0.0, 0.0)

    def start_back(self, velocity=VELOCITY):
        """
        Start moving backwards. This function returns immediately.

        :param velocity: The velocity of the motion (meters/second)
        :return:
        """
        self.start_linear_motion(-velocity, 0.0, 0.0)

    def start_up(self, velocity=VELOCITY):
        """
        Start moving up. This function returns immediately.

        :param velocity: The velocity of the motion (meters/second)
        :return:
        """
        self.start_linear_motion(0.0, 0.0, velocity)

    def start_down(self, velocity=VELOCITY):
        """
        Start moving down. This function returns immediately.

        :param velocity: The velocity of the motion (meters/second)
        :return:
        """
        self.start_linear_motion(0.0, 0.0, -velocity)

    def stop(self):
        """
        Stop any motion and hover.

        :return:
        """
        self._set_vel_setpoint(0.0, 0.0, 0.0, 0.0)

    def start_turn_left(self, rate=RATE):
        """
        Start turning left. This function returns immediately.

        :param rate: The angular rate (degrees/second)
        :return:
        """
        self._set_vel_setpoint(0.0, 0.0, 0.0, -rate)

    def start_turn_right(self, rate=RATE):
        """
        Start turning right. This function returns immediately.

        :param rate: The angular rate (degrees/second)
        :return:
        """
        self._set_vel_setpoint(0.0, 0.0, 0.0, rate)

    def start_circle_left(self, radius_m, velocity=VELOCITY):
        """
        Start a circular motion to the left. This function returns immediately.

        :param radius_m: The radius of the circle (meters)
        :param velocity: The velocity of the motion (meters/second)
        :return:
        """
        circumference = 2 * radius_m * math.pi
        rate = 360.0 * velocity / circumference

        self._set_vel_setpoint(velocity, 0.0, 0.0, -rate)

    def start_circle_right(self, radius_m, velocity=VELOCITY):
        """
        Start a circular motion to the right. This function returns immediately

        :param radius_m: The radius of the circle (meters)
        :param velocity: The velocity of the motion (meters/second)
        :return:
        """
        circumference = 2 * radius_m * math.pi
        rate = 360.0 * velocity / circumference

        self._set_vel_setpoint(velocity, 0.0, 0.0, rate)

    def start_linear_motion(self, velocity_x_m, velocity_y_m, velocity_z_m):
        """
        Start a linear motion. This function returns immediately.

        positive X is forward
        positive Y is left
        positive Z is up

        :param velocity_x_m: The velocity along the X-axis (meters/second)
        :param velocity_y_m: The velocity along the Y-axis (meters/second)
        :param velocity_z_m: The velocity along the Z-axis (meters/second)
        :return:
        """
        self._set_vel_setpoint(
            velocity_x_m, velocity_y_m, velocity_z_m, 0.0)

    def _set_vel_setpoint(self, velocity_x, velocity_y, velocity_z, rate_yaw):
        if not self._is_flying:
            raise Exception('Can not move on the ground. Take off first!')
        self._thread.set_vel_setpoint(
            velocity_x, velocity_y, velocity_z, rate_yaw)

    def _reset_position_estimator(self):
        self._cf.param.set_value('kalman.resetEstimation', '1')
        time.sleep(0.1)
        self._cf.param.set_value('kalman.resetEstimation', '0')
        time.sleep(2)


class _SetPointThread(Thread):
    TERMINATE_EVENT = 'terminate'
    UPDATE_PERIOD = 0.2
    ABS_Z_INDEX = 3

    def __init__(self, cf, update_period=UPDATE_PERIOD):
        Thread.__init__(self)
        self.update_period = update_period

        self._queue = Queue()
        self._cf = cf

        self._hover_setpoint = [0.0, 0.0, 0.0, 0.0]

        self._z_base = 0.0
        self._z_velocity = 0.0
        self._z_base_time = 0.0

    def stop(self):
        """
        Stop the thread and wait for it to terminate

        :return:
        """
        self._queue.put(self.TERMINATE_EVENT)
        self.join()

    def set_vel_setpoint(self, velocity_x, velocity_y, velocity_z, rate_yaw):
        """Set the velocity setpoint to use for the future motion"""
        self._queue.put((velocity_x, velocity_y, velocity_z, rate_yaw))

    def get_height(self):
        """
        Get the current height of the Crazyflie.

        :return: The height (meters)
        """
        return self._hover_setpoint[self.ABS_Z_INDEX]

    def run(self):
        while True:
            try:
                event = self._queue.get(block=True, timeout=self.update_period)
                if event == self.TERMINATE_EVENT:
                    return

                self._new_setpoint(*event)
            except Empty:
                pass

            self._update_z_in_setpoint()
            self._cf.commander.send_hover_setpoint(*self._hover_setpoint)

    def _new_setpoint(self, velocity_x, velocity_y, velocity_z, rate_yaw):
        self._z_base = self._current_z()
        self._z_velocity = velocity_z
        self._z_base_time = time.time()

        self._hover_setpoint = [velocity_x, velocity_y, rate_yaw, self._z_base]

    def _update_z_in_setpoint(self):
        self._hover_setpoint[self.ABS_Z_INDEX] = self._current_z()

    def _current_z(self):
        now = time.time()
        return self._z_base + self._z_velocity * (now - self._z_base_time)
