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
import unittest

from cflib.utils.callbacks import Caller


class CallerTest(unittest.TestCase):

    def setUp(self):
        self.callback_count = 0
        self.sut = Caller()

    def test_that_callback_is_added(self):
        # Fixture

        # Test
        self.sut.add_callback(self._callback)

        # Assert
        self.sut.call()
        self.assertEqual(1, self.callback_count)

    def test_that_callback_is_added_only_one_time(self):
        # Fixture

        # Test
        self.sut.add_callback(self._callback)
        self.sut.add_callback(self._callback)

        # Assert
        self.sut.call()
        self.assertEqual(1, self.callback_count)

    def test_that_multiple_callbacks_are_added(self):
        # Fixture

        # Test
        self.sut.add_callback(self._callback)
        self.sut.add_callback(self._callback2)

        # Assert
        self.sut.call()
        self.assertEqual(2, self.callback_count)

    def test_that_callback_is_removed(self):
        # Fixture
        self.sut.add_callback(self._callback)

        # Test
        self.sut.remove_callback(self._callback)

        # Assert
        self.sut.call()
        self.assertEqual(0, self.callback_count)

    def test_that_callback_is_called_with_arguments(self):
        # Fixture
        self.sut.add_callback(self._callback_with_args)

        # Test
        self.sut.call('The token')

        # Assert
        self.assertEqual('The token', self.callback_token)

    def _callback(self):
        self.callback_count += 1

    def _callback2(self):
        self.callback_count += 1

    def _callback_with_args(self, token):
        self.callback_token = token
