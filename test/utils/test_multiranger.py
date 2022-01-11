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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
import unittest
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch

from cflib.crazyflie import Crazyflie
from cflib.crazyflie import Log
from cflib.crazyflie.log import LogConfig
from cflib.utils.callbacks import Caller
from cflib.utils.multiranger import Multiranger


class MultirangerTest(unittest.TestCase):
    FRONT = 'range.front'
    BACK = 'range.back'
    LEFT = 'range.left'
    RIGHT = 'range.right'
    UP = 'range.up'
    DOWN = 'range.zrange'

    OUT_OF_RANGE = 8000

    def setUp(self):
        self.cf_mock = MagicMock(spec=Crazyflie)

        self.log_config_mock = MagicMock(spec=LogConfig)
        self.log_config_mock.data_received_cb = Caller()

        self.log_mock = MagicMock(spec=Log)
        self.cf_mock.log = self.log_mock

        self.front_data = 2345
        self.back_data = 2345
        self.left_data = 123
        self.right_data = 5432
        self.up_data = 3456
        self.down_data = 1212
        self.log_data = {
            self.FRONT: self.front_data,
            self.BACK: self.back_data,
            self.LEFT: self.left_data,
            self.RIGHT: self.right_data,
            self.UP: self.up_data,
            self.DOWN: self.down_data,
        }

    def test_that_log_configuration_is_added_on_connect(self):
        # Fixture
        with patch('cflib.utils.multiranger.LogConfig',
                   return_value=self.log_config_mock):
            sut = Multiranger(self.cf_mock)

            # Test
            sut.start()

            # Assert
            self.log_mock.add_config.assert_called_once_with(
                self.log_config_mock)

    def test_that_log_configuration_is_correct(self):
        # Fixture
        with patch('cflib.utils.multiranger.LogConfig',
                   return_value=self.log_config_mock):
            sut = Multiranger(self.cf_mock)

            # Test
            sut.start()

            # Assert
            self.log_config_mock.add_variable.assert_has_calls([
                call(self.FRONT),
                call(self.BACK),
                call(self.LEFT),
                call(self.RIGHT),
                call(self.UP),
            ])

    def test_that_log_configuration_is_correct_with_zranger(self):
        # Fixture
        with patch('cflib.utils.multiranger.LogConfig',
                   return_value=self.log_config_mock):
            sut = Multiranger(self.cf_mock, zranger=True)

            # Test
            sut.start()

            # Assert
            self.log_config_mock.add_variable.assert_has_calls([
                call(self.FRONT),
                call(self.BACK),
                call(self.LEFT),
                call(self.RIGHT),
                call(self.UP),
                call(self.DOWN)
            ])

    # def test_that_rate_configuration_is_applied(self):
    #     # Fixture
    #     with patch('cflib.utils.multiranger.LogConfig',
    #                return_value=self.log_config_mock):
    #
    #         # Test
    #         Multiranger(self.cf_mock, rate_ms=123)
    #
    #         # Assert
    #         self.log_config_mock.assert_called_once_with('multiranger', 123)

    def test_that_logging_is_started_on_start(self):
        # Fixture
        with patch('cflib.utils.multiranger.LogConfig',
                   return_value=self.log_config_mock):
            sut = Multiranger(self.cf_mock)

            # Test
            sut.start()

            # Assert
            self.log_config_mock.start.assert_called_once_with()

    def test_that_data_callback_is_set(self):
        # Fixture
        with patch('cflib.utils.multiranger.LogConfig',
                   return_value=self.log_config_mock):
            sut = Multiranger(self.cf_mock)

            # Test
            sut.start()

            # Assert
            self.log_config_mock.start.assert_called_once_with()
            self.assertEqual(1, len(
                self.log_config_mock.data_received_cb.callbacks))

    def test_that_the_log_config_is_deleted_on_stop(self):
        # Fixture
        with patch('cflib.utils.multiranger.LogConfig',
                   return_value=self.log_config_mock):
            sut = Multiranger(self.cf_mock)
            sut.start()

            # Test
            sut.stop()

            # Assert
            self.log_config_mock.delete.assert_called_once_with()

    def test_that_using_context_manager_calls_start_and_stop(self):
        # Fixture
        with patch('cflib.utils.multiranger.LogConfig',
                   return_value=self.log_config_mock):

            with Multiranger(self.cf_mock):
                pass

            # Assert
            self.log_config_mock.start.assert_called_once_with()
            self.log_config_mock.delete.assert_called_once_with()

    def test_that_data_received_from_log_is_available_from_up_getter(self):
        self._validate_distance_from_getter(self.up_data / 1000.0, 'up')

    def test_that_none_is_returned_if_up_ranging_is_off_limit(self):
        # Fixture
        self.log_data[self.UP] = self.OUT_OF_RANGE
        self._validate_distance_from_getter(None, 'up')

    def test_that_data_received_from_log_is_available_from_front_getter(self):
        self._validate_distance_from_getter(self.front_data / 1000.0,
                                            'front')

    def test_that_none_is_returned_if_front_ranging_is_off_limit(self):
        # Fixture
        self.log_data[self.FRONT] = self.OUT_OF_RANGE
        self._validate_distance_from_getter(None, 'front')

    def test_that_data_received_from_log_is_available_from_back_getter(self):
        self._validate_distance_from_getter(self.back_data / 1000.0,
                                            'back')

    def test_that_none_is_returned_if_back_ranging_is_off_limit(self):
        # Fixture
        self.log_data[self.BACK] = self.OUT_OF_RANGE
        self._validate_distance_from_getter(None, 'back')

    def test_that_data_received_from_log_is_available_from_left_getter(self):
        self._validate_distance_from_getter(self.left_data / 1000.0,
                                            'left')

    def test_that_none_is_returned_if_left_ranging_is_off_limit(self):
        # Fixture
        self.log_data[self.LEFT] = self.OUT_OF_RANGE
        self._validate_distance_from_getter(None, 'left')

    def test_that_data_received_from_log_is_available_from_right_getter(self):
        self._validate_distance_from_getter(self.right_data / 1000.0,
                                            'right')

    def test_that_none_is_returned_if_right_ranging_is_off_limit(self):
        # Fixture
        self.log_data[self.RIGHT] = self.OUT_OF_RANGE
        self._validate_distance_from_getter(None, 'right')

    def test_that_data_received_from_log_is_available_from_down_getter(self):
        self._validate_distance_from_getter(self.down_data / 1000.0,
                                            'down', zranger=True)

    def test_that_none_is_returned_if_down_ranging_is_off_limit(self):
        # Fixture
        self.log_data[self.DOWN] = self.OUT_OF_RANGE
        self._validate_distance_from_getter(None, 'down', zranger=True)

    def test_that_none_is_returned_from_down_if_zranger_is_disabled(self):
        # Fixture
        del self.log_data[self.DOWN]
        self._validate_distance_from_getter(None, 'down', zranger=False)

    # Helpers ################################################################

    def _validate_distance_from_getter(self, expected, getter_name,
                                       zranger=False):
        # Fixture
        with patch('cflib.utils.multiranger.LogConfig',
                   return_value=self.log_config_mock):
            sut = Multiranger(self.cf_mock, zranger=zranger)

            timestmp = 1234
            logconf = None

            self.log_config_mock.data_received_cb.call(timestmp, self.log_data,
                                                       logconf)

            # Test
            actual = getattr(sut, getter_name)

            # Assert
            self.assertEqual(expected, actual)
