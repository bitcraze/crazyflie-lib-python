# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2016-2020 Bitcraze AB
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
import unittest
from test.support.asyncCallbackCaller import AsyncCallbackCaller
from unittest.mock import call
from unittest.mock import MagicMock

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import Log
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.utils.callbacks import Caller


class SyncLoggerTest(unittest.TestCase):

    def setUp(self):
        self.cf_mock = MagicMock(spec=Crazyflie)
        self.cf_mock.disconnected = Caller()

        self.log_mock = MagicMock(spec=Log)
        self.cf_mock.log = self.log_mock

        self.log_config_mock = MagicMock(spec=LogConfig)
        self.log_config_mock.data_received_cb = Caller()

        self.log_config_mock2 = MagicMock(spec=LogConfig)
        self.log_config_mock2.data_received_cb = Caller()

        self.sut = SyncLogger(self.cf_mock, self.log_config_mock)
        self.sut_multi = SyncLogger(
            self.cf_mock, [self.log_config_mock, self.log_config_mock2])

    def test_that_log_configuration_is_added_on_connect(self):
        # Fixture

        # Test
        self.sut.connect()

        # Assert
        self.log_mock.add_config.assert_called_once_with(self.log_config_mock)

    def test_that_multiple_log_configurations_are_added_on_connect(self):
        # Fixture

        # Test
        self.sut_multi.connect()

        # Assert
        self.log_mock.add_config.assert_has_calls([
            call(self.log_config_mock),
            call(self.log_config_mock2)
        ])

    def test_that_logging_is_started_on_connect(self):
        # Fixture

        # Test
        self.sut.connect()

        # Assert
        self.log_config_mock.start.assert_called_once_with()

    def test_that_logging_is_started_on_connect_for_multiple_log_confs(self):
        # Fixture

        # Test
        self.sut_multi.connect()

        # Assert
        self.log_config_mock.start.assert_called_once_with()
        self.log_config_mock2.start.assert_called_once_with()

    def test_connection_status_after_connect(self):
        # Fixture
        self.sut.connect()

        # Test
        actual = self.sut.is_connected()

        # Assert
        self.assertTrue(actual)

    def test_that_callbacks_are_removed_on_disconnect(self):
        # Fixture

        # Test
        self.sut.connect()
        self.sut.disconnect()

        # Assert
        self.assertEqual(0, len(self.cf_mock.disconnected.callbacks))
        self.assertEqual(0,
                         len(self.log_config_mock.data_received_cb.callbacks))

    def test_that_log_config_is_stopped_on_disconnect(self):
        # Fixture
        self.sut.connect()

        # Test
        self.sut.disconnect()

        # Assert
        self.log_config_mock.stop.assert_called_once_with()
        self.log_config_mock.delete.assert_called_once_with()

    def test_that_multiple_log_configs_are_stopped_on_disconnect(self):
        # Fixture
        self.sut_multi.connect()

        # Test
        self.sut_multi.disconnect()

        # Assert
        self.log_config_mock.stop.assert_called_once_with()
        self.log_config_mock.delete.assert_called_once_with()

        self.log_config_mock2.stop.assert_called_once_with()
        self.log_config_mock2.delete.assert_called_once_with()

    def test_that_data_is_received(self):
        # Fixture
        self.sut.connect()

        expected = ('Some ts', 'Some data', 'Some logblock')
        AsyncCallbackCaller(cb=self.log_config_mock.data_received_cb,
                            args=[expected[0], expected[1], expected[2]]
                            ).trigger()

        # Test
        actual = None
        for log_block in self.sut:
            actual = log_block
            break

        # Assert
        self.assertEqual(expected, actual)

    def test_connection_status_after_disconnect(self):
        # Fixture
        self.sut.connect()
        self.sut.disconnect()

        # Test
        actual = self.sut.is_connected()

        # Assert
        self.assertFalse(actual)

    def test_that_connect_to_connected_instance_raises_exception(self):
        # Fixture
        self.sut.connect()

        # Test
        # Assert
        with self.assertRaises(Exception):
            self.sut.connect()

    def test_connect_to_disconnected_instance(self):
        # Fixture
        self.sut.connect()
        self.sut.disconnect()

        # Test
        self.sut.connect()

        # Assert
        # Nothing here. Just not expecting an exception

    def test_disconnect_from_disconnected_instance(self):
        # Fixture

        # Test
        self.sut.disconnect()

        # Assert
        # Nothing here. Just not expecting an exception

    def test_connect_disconnect_with_context_management(self):
        # Fixture

        # Test
        with(SyncLogger(self.cf_mock, self.log_config_mock)) as sut:
            # Assert
            self.assertTrue(sut.is_connected())

        self.assertFalse(sut.is_connected())

    def test_that_iterator_is_implemented(self):
        # Fixture

        # Test
        actual = self.sut.__iter__()

        # Assert
        self.assertEqual(self.sut, actual)

    def test_construction_with_sync_crazyflie_instance(self):
        # Fixture
        scf_mock = MagicMock(spec=SyncCrazyflie)
        scf_mock.cf = self.cf_mock

        # Test
        sut = SyncLogger(scf_mock, self.log_config_mock)
        sut.connect()

        # Assert
        # Nothing here. Just not expecting an exception

    def test_getting_data_without_conection_raises_exception(self):
        # Fixture

        # Test
        with self.assertRaises(StopIteration):
            self.sut.__next__()

            # Assert

    def test_lost_connection_in_crazyflie_disconnects(self):
        # Fixture
        self.sut.connect()

        # Test
        AsyncCallbackCaller(cb=self.cf_mock.disconnected,
                            args=['Some uri']
                            ).call_and_wait()

        # Assert
        self.assertFalse(self.sut.is_connected())

    def test_lost_connection_in_crazyflie_raises_exception_in_iterator(self):
        # Fixture
        self.sut.connect()

        # Note this is not foolproof, the disconnected callback may be called
        # before we are waiting on data. It will raise the same exception
        # though and will pass
        AsyncCallbackCaller(cb=self.cf_mock.disconnected,
                            delay=0.5,
                            args=['Some uri']
                            ).trigger()

        # Test
        # Assert
        with self.assertRaises(StopIteration):
            self.sut.__next__()
