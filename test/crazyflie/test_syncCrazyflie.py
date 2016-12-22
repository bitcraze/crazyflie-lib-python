# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) Bitcraze AB
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
import sys
import unittest
from threading import Thread

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils.callbacks import Caller

if sys.version_info < (3, 3):
    from mock import MagicMock
else:
    from unittest.mock import MagicMock


class SyncCrazyflieTest(unittest.TestCase):

    def setUp(self):
        self.uri = 'radio://0/60/2M'

        self.cf_mock = MagicMock(spec=Crazyflie)
        self.cf_mock.connected = Caller()
        self.cf_mock.connection_failed = Caller()
        self.cf_mock.disconnected = Caller()

        self.cf_mock.open_link = AsyncCallbackCaller(
            self.cf_mock.connected, self.uri).trigger

        self.sut = SyncCrazyflie(self.uri, self.cf_mock)

    def test_open_link(self):
        # Fixture

        # Test
        self.sut.open_link()

        # Assert
        self.assertTrue(self.sut.is_link_open())

    def test_failed_open_link_raises_exception(self):
        # Fixture
        expected = 'Some error message'
        self.cf_mock.open_link = AsyncCallbackCaller(
            self.cf_mock.connection_failed, self.uri, expected).trigger

        # Test
        try:
            self.sut.open_link()
        except Exception as e:
            actual = e.args[0]
        else:
            self.fail('Expect exception')

        # Assert
        self.assertEqual(expected, actual)

    def test_open_link_of_already_open_link_raises_exception(self):
        # Fixture
        self.sut.open_link()

        # Test
        # Assert
        with self.assertRaises(Exception):
            self.sut.open_link()

    def test_close_link(self):
        # Fixture
        self.sut.open_link()

        # Test
        self.sut.close_link()

        # Assert
        self.cf_mock.close_link.assert_called_once_with()
        self.assertFalse(self.sut.is_link_open())

    def test_close_link_that_is_not_open(self):
        # Fixture

        # Test
        self.sut.close_link()

        # Assert
        self.assertFalse(self.sut.is_link_open())

    def test_closed_if_connection_is_lost(self):
        # Fixture
        self.sut.open_link()

        # Test
        AsyncCallbackCaller(self.cf_mock.disconnected, self.uri).\
            call_and_wait()

        # Assert
        self.assertFalse(self.sut.is_link_open())

    def test_open_close_with_context_mangement(self):
        # Fixture

        # Test
        with SyncCrazyflie(self.uri, self.cf_mock) as sut:
            self.assertTrue(sut.is_link_open())

        # Assert
        self.cf_mock.close_link.assert_called_once_with()


class AsyncCallbackCaller:

    def __init__(self, caller, *args, **kwargs):
        self.caller = caller
        self.args = args
        self.kwargs = kwargs

    def trigger(self, *args, **kwargs):
        Thread(target=self._make_call).start()

    def call_and_wait(self):
        thread = Thread(target=self._make_call)
        thread.start()
        thread.join()

    def _make_call(self):
        self.caller.call(*self.args, **self.kwargs)
