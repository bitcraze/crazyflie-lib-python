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
import sys
import unittest

from cflib.crazyflie import Crazyflie
from cflib.crazyflie import Log
from cflib.crazyflie.log import LogConfig
from cflib.utils.callbacks import Caller
from cflib.utils.multi_ranger import MultiRanger

if sys.version_info < (3, 3):
    from mock import MagicMock, call, patch
else:
    from unittest.mock import MagicMock, call, patch


class MultiRangerTest(unittest.TestCase):
    FRONT = 'oa.front'
    BACK = 'oa.back'
    LEFT = 'oa.left'
    RIGHT = 'oa.right'
    UP = 'oa.up'

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
        self.log_data = {
            self.FRONT: self.front_data,
            self.BACK: self.back_data,
            self.LEFT: self.left_data,
            self.RIGHT: self.right_data,
            self.UP: self.up_data,
        }

    def test_that_log_configuration_is_added_on_connect(self):
        # Fixture
        with patch('cflib.utils.multi_ranger.LogConfig',
                   return_value=self.log_config_mock):
            sut = MultiRanger(self.cf_mock)

            # Test
            sut.start()

            # Assert
            self.log_mock.add_config.assert_called_once_with(
                self.log_config_mock)

    def test_that_log_configuration_is_correct(self):
        # Fixture
        with patch('cflib.utils.multi_ranger.LogConfig',
                   return_value=self.log_config_mock):
            sut = MultiRanger(self.cf_mock)

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

    def test_that_logging_is_started_on_start(self):
        # Fixture
        with patch('cflib.utils.multi_ranger.LogConfig',
                   return_value=self.log_config_mock):
            sut = MultiRanger(self.cf_mock)

            # Test
            sut.start()

            # Assert
            self.log_config_mock.start.assert_called_once_with()

    def test_that_data_callback_is_set(self):
        # Fixture
        with patch('cflib.utils.multi_ranger.LogConfig',
                   return_value=self.log_config_mock):
            sut = MultiRanger(self.cf_mock)

            # Test
            sut.start()

            # Assert
            self.log_config_mock.start.assert_called_once_with()
            self.assertEqual(1, len(
                self.log_config_mock.data_received_cb.callbacks))

    def test_that_the_log_config_is_deleted_on_stop(self):
        # Fixture
        with patch('cflib.utils.multi_ranger.LogConfig',
                   return_value=self.log_config_mock):
            sut = MultiRanger(self.cf_mock)
            sut.start()

            # Test
            sut.stop()

            # Assert
            self.log_config_mock.delete.assert_called_once_with()

    def test_that_using_context_manager_calls_start_and_stop(self):
        # Fixture
        with patch('cflib.utils.multi_ranger.LogConfig',
                   return_value=self.log_config_mock):

            with MultiRanger(self.cf_mock):
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

    # Helpers ################################################################

    def _validate_distance_from_getter(self, expected, getter_name):
        # Fixture
        with patch('cflib.utils.multi_ranger.LogConfig',
                   return_value=self.log_config_mock):
            sut = MultiRanger(self.cf_mock)

            timestmp = 1234
            logconf = None

            self.log_config_mock.data_received_cb.call(timestmp, self.log_data,
                                                       logconf)

            # Test
            actual = getattr(sut, getter_name)

            # Assert
            self.assertEqual(expected, actual)
