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
from unittest.mock import MagicMock

from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie


class TestSwarm(unittest.TestCase):
    URI1 = 'uri1'
    URI2 = 'uri2'
    URI3 = 'uri3'

    def setUp(self):
        self.uris = [self.URI1, self.URI2, self.URI3]
        self.factory = MockFactory()

        self.sut = Swarm(self.uris, factory=self.factory)

    def test_that_instances_are_created(self):
        # Fixture

        # Test

        # Assert
        actual = len(self.factory.mocks)
        expected = len(self.uris)
        self.assertEqual(expected, actual)

    def test_that_all_links_are_opened(self):
        # Fixture

        # Test
        self.sut.open_links()

        # Assert
        for uri, mock in self.factory.mocks.items():
            mock.open_link.assert_called_once_with()

    def test_open_of_already_opened_swarm_raises_exception(self):
        # Fixture
        self.sut.open_links()

        # Test
        # Assert
        with self.assertRaises(Exception):
            self.sut.open_links()

    def test_failed_open_of_one_link_closes_all_and_raises_exception(self):
        # Fixture
        self.factory.mocks[self.URI2].open_link.side_effect = Exception()

        # Test
        # Assert
        with self.assertRaises(Exception):
            self.sut.open_links()

        for uri, mock in self.factory.mocks.items():
            mock.close_link.assert_called_once_with()

    def test_that_all_links_are_closed(self):
        # Fixture
        self.sut.open_links()

        # Test
        self.sut.close_links()

        # Assert
        for uri, mock in self.factory.mocks.items():
            mock.close_link.assert_called_once_with()

    def test_open_with_context_management(self):
        # Fixture

        # Test
        with Swarm(self.uris, factory=self.factory):
            pass

        # Assert
        for uri, mock in self.factory.mocks.items():
            mock.open_link.assert_called_once_with()
            mock.close_link.assert_called_once_with()

    def test_sequential_execution_without_arguments(self):
        # Fixture
        func = MagicMock()

        # Test
        self.sut.sequential(func)

        # Assert
        for uri, mock in self.factory.mocks.items():
            func.assert_any_call(mock)

    def test_sequential_execution(self):
        # Fixture
        func = MagicMock()
        args_dict = {
            self.URI1: ['cf1-arg1'],
            self.URI2: ['cf2-arg1'],
            self.URI3: ['cf3-arg1'],
        }

        cf1 = self.factory.mocks[self.URI1]
        cf2 = self.factory.mocks[self.URI2]
        cf3 = self.factory.mocks[self.URI3]

        # Test
        self.sut.sequential(func, args_dict=args_dict)

        # Assert
        func.assert_any_call(cf1, 'cf1-arg1')
        func.assert_any_call(cf2, 'cf2-arg1')
        func.assert_any_call(cf3, 'cf3-arg1')

    def test_parallel_execution_without_arguments(self):
        # Fixture
        func = MagicMock()

        # Test
        self.sut.parallel(func)

        # Assert
        for uri, mock in self.factory.mocks.items():
            func.assert_any_call(mock)

    def test_parallel_execution(self):
        # Fixture
        func = MagicMock()
        args_dict = {
            self.URI1: ['cf1-arg1'],
            self.URI2: ['cf2-arg1'],
            self.URI3: ['cf3-arg1'],
        }

        cf1 = self.factory.mocks[self.URI1]
        cf2 = self.factory.mocks[self.URI2]
        cf3 = self.factory.mocks[self.URI3]

        # Test
        self.sut.parallel(func, args_dict=args_dict)

        # Assert
        func.assert_any_call(cf1, 'cf1-arg1')
        func.assert_any_call(cf2, 'cf2-arg1')
        func.assert_any_call(cf3, 'cf3-arg1')

    def test_parallel_execution_with_exception(self):
        # Fixture
        func_fail = MagicMock()
        func_fail.side_effect = Exception()
        args_dict = {
            self.URI1: ['cf1-arg1'],
            self.URI2: ['cf2-arg1'],
            self.URI3: ['cf3-arg1'],
        }

        cf1 = self.factory.mocks[self.URI1]
        cf2 = self.factory.mocks[self.URI2]
        cf3 = self.factory.mocks[self.URI3]

        # Test
        self.sut.parallel(func_fail, args_dict=args_dict)

        # Assert
        func_fail.assert_any_call(cf1, 'cf1-arg1')
        func_fail.assert_any_call(cf2, 'cf2-arg1')
        func_fail.assert_any_call(cf3, 'cf3-arg1')

    def test_parallel_safe_execution_with_exception(self):
        # Fixture
        func_fail = MagicMock()
        func_fail.side_effect = Exception()
        args_dict = {
            self.URI1: ['cf1-arg1'],
            self.URI2: ['cf2-arg1'],
            self.URI3: ['cf3-arg1'],
        }

        # Test
        # Assert
        with self.assertRaises(Exception):
            self.sut.parallel_safe(func_fail, args_dict=args_dict)


class MockFactory:

    def __init__(self):
        self.mocks = {}

    def construct(self, uri):
        mock = MagicMock(spec=SyncCrazyflie, name='CF-' + uri)
        self.mocks[uri] = mock
        return mock


if __name__ == '__main__':
    unittest.main()
