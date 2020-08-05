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
import math
import unittest
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch

from cflib.crazyflie import Crazyflie
from cflib.crazyflie import HighLevelCommander
from cflib.crazyflie import Param
from cflib.positioning.position_hl_commander import PositionHlCommander


@patch('time.sleep')
class TestPositionHlCommander(unittest.TestCase):
    def setUp(self):
        self.commander_mock = MagicMock(spec=HighLevelCommander)
        self.param_mock = MagicMock(spec=Param)
        self.cf_mock = MagicMock(spec=Crazyflie)
        self.cf_mock.high_level_commander = self.commander_mock
        self.cf_mock.param = self.param_mock
        self.cf_mock.is_connected.return_value = True

        self.sut = PositionHlCommander(self.cf_mock)

    def test_that_the_estimator_is_reset_on_take_off(
            self, sleep_mock):
        # Fixture
        sut = PositionHlCommander(self.cf_mock, 1.0, 2.0, 3.0)

        # Test
        sut.take_off()

        # Assert
        self.param_mock.set_value.assert_has_calls([
            call('kalman.initialX', '{:.2f}'.format(1.0)),
            call('kalman.initialY', '{:.2f}'.format(2.0)),
            call('kalman.initialZ', '{:.2f}'.format(3.0)),

            call('kalman.resetEstimation', '1'),
            call('kalman.resetEstimation', '0')
        ])

    def test_that_the_hi_level_commander_is_activated_on_take_off(
            self, sleep_mock):
        # Fixture

        # Test
        self.sut.take_off()

        # Assert
        self.param_mock.set_value.assert_has_calls([
            call('commander.enHighLevel', '1')
        ])

    def test_that_controller_is_selected_on_take_off(
            self, sleep_mock):
        # Fixture
        self.sut.set_controller(PositionHlCommander.CONTROLLER_MELLINGER)

        # Test
        self.sut.take_off()

        # Assert
        self.param_mock.set_value.assert_has_calls([
            call('stabilizer.controller', '2')
        ])

    def test_that_take_off_raises_exception_if_not_connected(
            self, sleep_mock):
        # Fixture
        self.cf_mock.is_connected.return_value = False

        # Test
        # Assert
        with self.assertRaises(Exception):
            self.sut.take_off()

    def test_that_take_off_raises_exception_when_already_flying(
            self, sleep_mock):
        # Fixture
        self.sut.take_off()

        # Test
        # Assert
        with self.assertRaises(Exception):
            self.sut.take_off()

    def test_that_it_goes_up_on_take_off(
            self, sleep_mock):
        # Fixture

        # Test
        self.sut.take_off(height=0.4, velocity=0.6)

        # Assert
        duration = 0.4 / 0.6
        self.commander_mock.takeoff.assert_called_with(0.4, duration)
        sleep_mock.assert_called_with(duration)

    def test_that_it_goes_up_to_default_height(
            self, sleep_mock):
        # Fixture
        sut = PositionHlCommander(self.cf_mock, default_height=0.4)

        # Test
        sut.take_off(velocity=0.6)

        # Assert
        duration = 0.4 / 0.6
        self.commander_mock.takeoff.assert_called_with(0.4, duration)
        sleep_mock.assert_called_with(duration)

    def test_that_it_goes_down_on_landing(
            self, sleep_mock):
        # Fixture
        self.sut.take_off(height=0.4)

        # Test
        self.sut.land(velocity=0.6)

        # Assert
        duration = 0.4 / 0.6
        self.commander_mock.land.assert_called_with(0.0, duration)
        sleep_mock.assert_called_with(duration)

    def test_that_it_takes_off_and_lands_as_context_manager(
            self, sleep_mock):
        # Fixture

        # Test
        with self.sut:
            pass

        # Assert
        duration1 = 0.5 / 0.5
        duration2 = 0.5 / 0.5
        self.commander_mock.takeoff.assert_called_with(0.5, duration1)
        self.commander_mock.land.assert_called_with(0.0, duration2)
        sleep_mock.assert_called_with(duration1)
        sleep_mock.assert_called_with(duration2)

    def test_that_it_returns_current_position(
            self, sleep_mock):
        # Fixture
        self.sut.take_off(height=0.4, velocity=0.6)

        # Test
        actual = self.sut.get_position()

        # Assert
        self.assertEqual(actual, (0.0, 0.0, 0.4))

    def test_that_it_goes_to_position(
            self, sleep_mock):
        # Fixture
        self.sut.take_off()
        initial_pos = self.sut.get_position()

        # Test
        self.sut.go_to(1.0, 2.0, 3.0, 4.0)

        # Assert
        distance = self._distance(initial_pos, (1.0, 2.0, 3.0))
        duration = distance / 4.0
        self.commander_mock.go_to.assert_called_with(
            1.0, 2.0, 3.0, 0.0, duration)
        sleep_mock.assert_called_with(duration)

    def test_that_it_does_not_send_goto_to_same_position(
            self, sleep_mock):
        # Fixture
        self.sut.take_off()
        initial_pos = self.sut.get_position()

        # Test
        self.sut.go_to(initial_pos[0], initial_pos[1], initial_pos[2])

        # Assert
        self.commander_mock.go_to.assert_not_called()

    def test_that_it_moves_distance(
            self, sleep_mock):
        # Fixture
        self.sut.take_off()
        initial_pos = self.sut.get_position()

        # Test
        self.sut.move_distance(1.0, 2.0, 3.0, 4.0)

        # Assert
        distance = self._distance((0.0, 0.0, 0.0), (1.0, 2.0, 3.0))
        duration = distance / 4.0
        final_pos = (
            initial_pos[0] + 1.0,
            initial_pos[1] + 2.0,
            initial_pos[2] + 3.0)
        self.commander_mock.go_to.assert_called_with(
            final_pos[0], final_pos[1], final_pos[2], 0.0, duration)
        sleep_mock.assert_called_with(duration)

    def test_that_it_goes_forward(
            self, sleep_mock):
        # Fixture
        self.sut.take_off()
        initial_pos = self.sut.get_position()

        # Test
        self.sut.forward(1.0, 2.0)

        # Assert
        duration = 1.0 / 2.0
        final_pos = (
            initial_pos[0] + 1.0,
            initial_pos[1],
            initial_pos[2])
        self.commander_mock.go_to.assert_called_with(
            final_pos[0], final_pos[1], final_pos[2], 0.0, duration)
        sleep_mock.assert_called_with(duration)

    def test_that_it_goes_back(
            self, sleep_mock):
        # Fixture
        self.sut.take_off()
        initial_pos = self.sut.get_position()

        # Test
        self.sut.back(1.0, 2.0)

        # Assert
        duration = 1.0 / 2.0
        final_pos = (
            initial_pos[0] - 1.0,
            initial_pos[1],
            initial_pos[2])
        self.commander_mock.go_to.assert_called_with(
            final_pos[0], final_pos[1], final_pos[2], 0.0, duration)
        sleep_mock.assert_called_with(duration)

    def test_that_it_goes_left(
            self, sleep_mock):
        # Fixture
        self.sut.take_off()
        initial_pos = self.sut.get_position()

        # Test
        self.sut.left(1.0, 2.0)

        # Assert
        duration = 1.0 / 2.0
        final_pos = (
            initial_pos[0],
            initial_pos[1] + 1.0,
            initial_pos[2])
        self.commander_mock.go_to.assert_called_with(
            final_pos[0], final_pos[1], final_pos[2], 0.0, duration)
        sleep_mock.assert_called_with(duration)

    def test_that_it_goes_right(
            self, sleep_mock):
        # Fixture
        self.sut.take_off()
        initial_pos = self.sut.get_position()

        # Test
        self.sut.right(1.0, 2.0)

        # Assert
        duration = 1.0 / 2.0
        final_pos = (
            initial_pos[0],
            initial_pos[1] - 1,
            initial_pos[2])
        self.commander_mock.go_to.assert_called_with(
            final_pos[0], final_pos[1], final_pos[2], 0, duration)
        sleep_mock.assert_called_with(duration)

    def test_that_it_goes_up(
            self, sleep_mock):
        # Fixture
        self.sut.take_off()
        initial_pos = self.sut.get_position()

        # Test
        self.sut.up(1.0, 2.0)

        # Assert
        duration = 1.0 / 2.0
        final_pos = (
            initial_pos[0],
            initial_pos[1],
            initial_pos[2] + 1)
        self.commander_mock.go_to.assert_called_with(
            final_pos[0], final_pos[1], final_pos[2], 0, duration)
        sleep_mock.assert_called_with(duration)

    def test_that_it_goes_down(
            self, sleep_mock):
        # Fixture
        self.sut.take_off()
        initial_pos = self.sut.get_position()

        # Test
        self.sut.down(1.0, 2.0)

        # Assert
        duration = 1.0 / 2.0
        final_pos = (
            initial_pos[0],
            initial_pos[1],
            initial_pos[2] - 1)
        self.commander_mock.go_to.assert_called_with(
            final_pos[0], final_pos[1], final_pos[2], 0, duration)
        sleep_mock.assert_called_with(duration)

    def test_that_default_velocity_is_used(
            self, sleep_mock):
        # Fixture
        self.sut.take_off()
        initial_pos = self.sut.get_position()
        self.sut.set_default_velocity(7)

        # Test
        self.sut.go_to(1.0, 2.0, 3.0)

        # Assert
        distance = self._distance(initial_pos, (1.0, 2.0, 3.0))
        duration = distance / 7.0
        self.commander_mock.go_to.assert_called_with(
            1.0, 2.0, 3.0, 0.0, duration)
        sleep_mock.assert_called_with(duration)

    def test_that_default_height_is_used(
            self, sleep_mock):
        # Fixture
        self.sut.take_off()
        initial_pos = self.sut.get_position()
        self.sut.set_default_velocity(7.0)
        self.sut.set_default_height(5.0)

        # Test
        self.sut.go_to(1.0, 2.0)

        # Assert
        distance = self._distance(initial_pos, (1.0, 2.0, 5.0))
        duration = distance / 7.0
        self.commander_mock.go_to.assert_called_with(
            1.0, 2.0, 5.0, 0.0, duration)
        sleep_mock.assert_called_with(duration)

    ######################################################################

    def _distance(self, p1, p2):
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        dz = p1[2] - p2[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)


if __name__ == '__main__':
    unittest.main()
