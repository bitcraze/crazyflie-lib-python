# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2016 Bitcraze AB
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
from unittest.mock import MagicMock

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils.callbacks import Caller


class SyncCrazyflieTest(unittest.TestCase):

    def setUp(self):
        self.uri = 'radio://0/60/2M'

        self.cf_mock = MagicMock(spec=Crazyflie)
        self.cf_mock.connected = Caller()
        self.cf_mock.connection_failed = Caller()
        self.cf_mock.disconnected = Caller()

        self.cf_mock.open_link = AsyncCallbackCaller(
            cb=self.cf_mock.connected,
            args=[self.uri],
            delay=0.2
        ).trigger

        self.close_link_mock = AsyncCallbackCaller(
            cb=self.cf_mock.disconnected,
            args=[self.uri],
            delay=0.2
        )
        self.cf_mock.close_link = self.close_link_mock.trigger

        self.sut = SyncCrazyflie(self.uri, self.cf_mock)

    def test_different_underlying_cf_instances(self):
        # Fixture

        # Test
        scf1 = SyncCrazyflie('uri 1')
        scf2 = SyncCrazyflie('uri 2')

        # Assert
        actual1 = scf1.cf
        actual2 = scf2.cf
        self.assertNotEqual(actual1, actual2)

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
            cb=self.cf_mock.connection_failed,
            args=[self.uri, expected]).trigger

        # Test
        try:
            self.sut.open_link()
        except Exception as e:
            actual = e.args[0]
        else:
            self.fail('Expect exception')

        # Assert
        self.assertEqual(expected, actual)
        self._assertAllCallbacksAreRemoved()

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
        self.assertEqual(1, self.close_link_mock.call_count)
        self.assertFalse(self.sut.is_link_open())
        self._assertAllCallbacksAreRemoved()

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
        AsyncCallbackCaller(
            cb=self.cf_mock.disconnected,
            args=[self.uri]).call_and_wait()

        # Assert
        self.assertFalse(self.sut.is_link_open())
        self._assertAllCallbacksAreRemoved()

    def test_open_close_with_context_management(self):
        # Fixture

        # Test
        with SyncCrazyflie(self.uri, self.cf_mock) as sut:
            self.assertTrue(sut.is_link_open())

        # Assert
        self.assertEqual(1, self.close_link_mock.call_count)
        self._assertAllCallbacksAreRemoved()

    def test_multiple_open_close_of_link(self):
        # Fixture

        # Test
        self.sut.open_link()
        self.sut.close_link()
        self.sut.open_link()
        self.sut.close_link()

        # Assert
        self.assertEqual(2, self.close_link_mock.call_count)
        self.assertFalse(self.sut.is_link_open())
        self._assertAllCallbacksAreRemoved()

    def _assertAllCallbacksAreRemoved(self):
        self.assertEqual(0, len(self.cf_mock.connected.callbacks))
        self.assertEqual(0, len(self.cf_mock.connection_failed.callbacks))
        self.assertEqual(0, len(self.cf_mock.disconnected.callbacks))
