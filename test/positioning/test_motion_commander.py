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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
import math
import unittest
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch

from cflib.crazyflie import Commander
from cflib.crazyflie import Crazyflie
from cflib.crazyflie import Param
from cflib.positioning.motion_commander import _SetPointThread
from cflib.positioning.motion_commander import MotionCommander


@patch('time.sleep')
@patch('cflib.positioning.motion_commander._SetPointThread',
       return_value=MagicMock(spec=_SetPointThread))
class TestMotionCommander(unittest.TestCase):
    def setUp(self):
        self.commander_mock = MagicMock(spec=Commander)
        self.param_mock = MagicMock(spec=Param)
        self.cf_mock = MagicMock(spec=Crazyflie)
        self.cf_mock.commander = self.commander_mock
        self.cf_mock.param = self.param_mock
        self.cf_mock.is_connected.return_value = True

        self.sut = MotionCommander(self.cf_mock)

    def test_that_the_estimator_is_reset_on_take_off(
            self, _SetPointThread_mock, sleep_mock):
        # Fixture

        # Test
        self.sut.take_off()

        # Assert
        self.param_mock.set_value.assert_has_calls([
            call('kalman.resetEstimation', '1'),
            call('kalman.resetEstimation', '0')
        ])

    def test_that_take_off_raises_exception_if_not_connected(
            self, _SetPointThread_mock, sleep_mock):
        # Fixture
        self.cf_mock.is_connected.return_value = False

        # Test
        # Assert
        with self.assertRaises(Exception):
            self.sut.take_off()

    def test_that_take_off_raises_exception_when_already_flying(
            self, _SetPointThread_mock, sleep_mock):
        # Fixture
        self.sut.take_off()

        # Test
        # Assert
        with self.assertRaises(Exception):
            self.sut.take_off()

    def test_that_it_goes_up_on_take_off(
            self, _SetPointThread_mock, sleep_mock):
        # Fixture
        thread_mock = _SetPointThread_mock()

        # Test
        self.sut.take_off(height=0.4, velocity=0.5)

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(0.0, 0.0, 0.5, 0.0),
            call(0.0, 0.0, 0.0, 0.0)
        ])
        sleep_mock.assert_called_with(0.4 / 0.5)

    def test_that_it_goes_up_to_default_height(
            self, _SetPointThread_mock, sleep_mock):
        # Fixture
        thread_mock = _SetPointThread_mock()
        sut = MotionCommander(self.cf_mock, default_height=0.4)

        # Test
        sut.take_off(velocity=0.6)

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(0.0, 0.0, 0.6, 0.0),
            call(0.0, 0.0, 0.0, 0.0)
        ])
        sleep_mock.assert_called_with(0.4 / 0.6)

    def test_that_the_thread_is_started_on_takeoff(
            self, _SetPointThread_mock, sleep_mock):
        # Fixture
        thread_mock = _SetPointThread_mock()

        # Test
        self.sut.take_off()

        # Assert
        thread_mock.start.assert_called_with()

    def test_that_it_goes_down_on_landing(
            self, _SetPointThread_mock, sleep_mock):
        # Fixture
        thread_mock = _SetPointThread_mock()
        thread_mock.get_height.return_value = 0.4

        self.sut.take_off()
        thread_mock.reset_mock()

        # Test
        self.sut.land(velocity=0.5)

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(0.0, 0.0, -0.5, 0.0),
            call(0.0, 0.0, 0.0, 0.0)
        ])
        sleep_mock.assert_called_with(0.4 / 0.5)

    def test_that_it_takes_off_and_lands_as_context_manager(
            self, _SetPointThread_mock, sleep_mock):
        # Fixture
        thread_mock = _SetPointThread_mock()
        thread_mock.reset_mock()

        thread_mock.get_height.return_value = 0.3

        # Test
        with self.sut:
            pass

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(0.0, 0.0, 0.2, 0.0),
            call(0.0, 0.0, 0.0, 0.0),
            call(0.0, 0.0, -0.2, 0.0),
            call(0.0, 0.0, 0.0, 0.0)
        ])
        sleep_mock.assert_called_with(0.3 / 0.2)
        sleep_mock.assert_called_with(0.3 / 0.2)

    def test_that_it_starts_moving_multi_dimensional(
            self, _SetPointThread_mock, sleep_mock):
        # Fixture
        thread_mock = _SetPointThread_mock()
        self.sut.take_off()
        thread_mock.reset_mock()

        # Test
        self.sut.start_linear_motion(0.1, 0.2, 0.3)

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(0.1, 0.2, 0.3, 0.0),
        ])

    def test_that_it_starts_moving(
            self, _SetPointThread_mock, sleep_mock):
        # Fixture
        self.sut.take_off()
        vel = 0.3

        data = [
            [self.sut.start_forward, (vel,  0.0, 0.0, 0.0)],
            [self.sut.start_back,    (-vel, 0.0, 0.0, 0.0)],
            [self.sut.start_left,    (0.0, vel, 0.0, 0.0)],
            [self.sut.start_right,   (0.0, -vel, 0.0, 0.0)],
            [self.sut.start_up,      (0.0, 0.0, vel, 0.0)],
            [self.sut.start_down,    (0.0, 0.0, -vel, 0.0)],
        ]
        # Test
        # Assert
        for line in data:
            self._verify_start_motion(line[0], vel, line[1],
                                      _SetPointThread_mock)

    def test_that_it_moves_multi_dimensional_distance(
            self, _SetPointThread_mock, sleep_mock):
        # Fixture
        thread_mock = _SetPointThread_mock()
        x = 0.1
        y = 0.2
        z = 0.3
        vel = 0.2
        distance = math.sqrt(x * x + y * y + z * z)
        expected_time = distance / vel
        expected_vel_x = vel * x / distance
        expected_vel_y = vel * y / distance
        expected_vel_z = vel * z / distance

        self.sut.take_off()
        thread_mock.reset_mock()
        sleep_mock.reset_mock()

        # Test
        self.sut.move_distance(x, y, z)

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(expected_vel_x, expected_vel_y, expected_vel_z, 0.0),
        ])
        sleep_mock.assert_called_with(expected_time)

    def test_that_it_moves(self, _SetPointThread_mock, sleep_mock):
        # Fixture
        vel = 0.3
        self.sut.take_off()

        data = [
            [self.sut.forward, (vel,  0.0, 0.0, 0.0)],
            [self.sut.back,    (-vel, 0.0, 0.0, 0.0)],
            [self.sut.left,    (0.0, vel, 0.0, 0.0)],
            [self.sut.right,   (0.0, -vel, 0.0, 0.0)],
            [self.sut.up,      (0.0, 0.0, vel, 0.0)],
            [self.sut.down,    (0.0, 0.0, -vel, 0.0)],
        ]
        # Test
        # Assert
        for test in data:
            self._verify_move(test[0], vel, test[1],
                              _SetPointThread_mock, sleep_mock)

    def test_that_it_starts_turn_right(self, _SetPointThread_mock, sleep_mock):
        # Fixture
        rate = 20
        thread_mock = _SetPointThread_mock()
        self.sut.take_off()
        thread_mock.reset_mock()

        # Test
        self.sut.start_turn_right(rate)

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(0.0, 0.0, 0.0, rate),
        ])

    def test_that_it_starts_turn_left(self, _SetPointThread_mock, sleep_mock):
        # Fixture
        rate = 20
        thread_mock = _SetPointThread_mock()
        self.sut.take_off()
        thread_mock.reset_mock()

        # Test
        self.sut.start_turn_left(rate)

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(0.0, 0.0, 0.0, -rate),
        ])

    def test_that_it_starts_circle_right(
            self, _SetPointThread_mock, sleep_mock):
        # Fixture
        velocity = 0.5
        radius = 0.9
        expected_rate = 360 * velocity / (2 * radius * math.pi)

        thread_mock = _SetPointThread_mock()
        self.sut.take_off()
        thread_mock.reset_mock()

        # Test
        self.sut.start_circle_right(radius, velocity=velocity)

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(velocity, 0.0, 0.0, expected_rate),
        ])

    def test_that_it_starts_circle_left(
            self, _SetPointThread_mock, sleep_mock):
        # Fixture
        velocity = 0.5
        radius = 0.9
        expected_rate = 360 * velocity / (2 * radius * math.pi)

        thread_mock = _SetPointThread_mock()
        self.sut.take_off()
        thread_mock.reset_mock()

        # Test
        self.sut.start_circle_left(radius, velocity=velocity)

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(velocity, 0.0, 0.0, -expected_rate),
        ])

    def test_that_it_turns_right(self, _SetPointThread_mock, sleep_mock):
        # Fixture
        rate = 20
        angle = 45
        turn_time = angle / rate
        thread_mock = _SetPointThread_mock()
        self.sut.take_off()
        thread_mock.reset_mock()

        # Test
        self.sut.turn_right(angle, rate=rate)

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(0.0, 0.0, 0.0, rate),
            call(0.0, 0.0, 0.0, 0.0)
        ])
        sleep_mock.assert_called_with(turn_time)

    def test_that_it_turns_left(self, _SetPointThread_mock, sleep_mock):
        # Fixture
        rate = 20
        angle = 45
        turn_time = angle / rate
        thread_mock = _SetPointThread_mock()
        self.sut.take_off()
        thread_mock.reset_mock()

        # Test
        self.sut.turn_left(angle, rate=rate)

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(0.0, 0.0, 0.0, -rate),
            call(0.0, 0.0, 0.0, 0.0)
        ])
        sleep_mock.assert_called_with(turn_time)

    def test_that_it_circles_right(self, _SetPointThread_mock, sleep_mock):
        # Fixture
        radius = 0.7
        velocity = 0.3
        angle = 45

        distance = 2 * radius * math.pi * angle / 360.0
        turn_time = distance / velocity
        rate = angle / turn_time

        thread_mock = _SetPointThread_mock()
        self.sut.take_off()
        thread_mock.reset_mock()

        # Test
        self.sut.circle_right(radius, velocity, angle)

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(velocity, 0.0, 0.0, rate),
            call(0.0, 0.0, 0.0, 0.0)
        ])
        sleep_mock.assert_called_with(turn_time)

    def test_that_it_circles_left(self, _SetPointThread_mock, sleep_mock):
        # Fixture
        radius = 0.7
        velocity = 0.3
        angle = 45

        distance = 2 * radius * math.pi * angle / 360.0
        turn_time = distance / velocity
        rate = angle / turn_time

        thread_mock = _SetPointThread_mock()
        self.sut.take_off()
        thread_mock.reset_mock()

        # Test
        self.sut.circle_left(radius, velocity, angle)

        # Assert
        thread_mock.set_vel_setpoint.assert_has_calls([
            call(velocity, 0.0, 0.0, -rate),
            call(0.0, 0.0, 0.0, 0.0)
        ])
        sleep_mock.assert_called_with(turn_time)

    ######################################################################

    def _verify_start_motion(self, function_under_test, velocity, expected,
                             _SetPointThread_mock):
        # Fixture
        thread_mock = _SetPointThread_mock()
        thread_mock.reset_mock()

        # Test
        function_under_test(velocity=velocity)

        # Assert
        try:
            thread_mock.set_vel_setpoint.assert_has_calls([
                call(*expected),
            ])
        except AssertionError as e:
            self._eprint('Failed when testing function ' +
                         function_under_test.__name__)
            raise e

    def _verify_move(self, function_under_test, velocity, expected,
                     _SetPointThread_mock, sleep_mock):
        # Fixture
        thread_mock = _SetPointThread_mock()

        distance = 1.2
        expected_time = distance / velocity

        thread_mock.reset_mock()
        sleep_mock.reset_mock()

        # Test
        function_under_test(distance, velocity=velocity)

        # Assert
        try:
            thread_mock.set_vel_setpoint.assert_has_calls([
                call(*expected),
                call(0.0, 0.0, 0.0, 0.0),
            ])
            sleep_mock.assert_called_with(expected_time)
        except AssertionError as e:
            print('Failed when testing function ' +
                  function_under_test.__name__)
            raise e


class TestSetpointThread(unittest.TestCase):
    def setUp(self):
        self.commander_mock = MagicMock(spec=Commander)
        self.cf_mock = MagicMock(spec=Crazyflie)
        self.cf_mock.commander = self.commander_mock

        self.sut = _SetPointThread(self.cf_mock)

    def test_that_thread_stops(self):
        # Fixture
        self.sut.start()
        self.sut.stop()

        # Test
        actual = self.sut.is_alive()

        # Assert
        self.assertFalse(actual)

    def test_that_x_y_and_yaw_is_set(self):
        # Fixture
        x = 1.0
        y = 2.0
        yaw = 3.0

        self.sut.start()

        # Test
        self.sut.set_vel_setpoint(x, y, 0, yaw)

        # Assert
        self.sut.stop()

        self.commander_mock.send_hover_setpoint.assert_called_once_with(
            x, y, yaw, 0)


if __name__ == '__main__':
    unittest.main()
