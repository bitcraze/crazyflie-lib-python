# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2019 Bitcraze AB
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
import time
import unittest

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from sys_test.swarm_test_rig.rig_support import RigSupport


class TestConnection(unittest.TestCase):
    def setUp(self):
        cflib.crtp.init_drivers()
        self.test_rig_support = RigSupport()

    def test_that_connection_time_scales_with_more_devices_without_cache(self):
        # Fixture
        self.test_rig_support.restart_devices(self.test_rig_support.all_uris)

        EXPECTED_CONNECTION_TIME = 5

        for nr_of_devices in range(1, len(self.test_rig_support.all_uris)):
            # Test
            uris = self.test_rig_support.all_uris[:nr_of_devices]

            start_time = time.time()
            with Swarm(uris):
                connected_time = time.time()

            actual = connected_time - start_time
            max_expected = EXPECTED_CONNECTION_TIME * nr_of_devices
            print('Connection time for', nr_of_devices, ':', actual,
                  ', per device:', actual / nr_of_devices)

            # Assert
            self.assertLess(actual, max_expected)

    def test_that_connection_time_scales_with_more_devices_with_cache(self):
        # Fixture
        self.test_rig_support.restart_devices(self.test_rig_support.all_uris)

        # Fill caches first by connecting to all devices
        factory = CachedCfFactory(rw_cache='./cache')
        with Swarm(self.test_rig_support.all_uris, factory=factory):
            pass

        EXPECTED_CONNECTION_TIME = 1.5

        for nr_of_devices in range(1, len(self.test_rig_support.all_uris)):
            # Test
            uris = self.test_rig_support.all_uris[:nr_of_devices]

            start_time = time.time()
            with Swarm(uris, factory=factory):
                connected_time = time.time()

            actual = connected_time - start_time
            max_expected = EXPECTED_CONNECTION_TIME * nr_of_devices
            print('Connection time for', nr_of_devices, ':', actual,
                  ', per device:', actual / nr_of_devices)

            # Assert
            self.assertLess(actual, max_expected)

    def test_that_all_devices_are_restarted(self):
        # Fixture
        uris = self.test_rig_support.all_uris

        # Test
        # Assert
        self.test_rig_support.restart_devices(uris)

    def test_that_all_devices_are_restarted_multiple_times(self):
        # Fixture
        uris = self.test_rig_support.all_uris

        # Test
        # Assert
        for i in range(10):
            self.test_rig_support.restart_devices(uris)

    def test_that_the_same_cf_object_can_be_connected_multiple_times(self):
        # Fixture
        self.test_rig_support.restart_devices(self.test_rig_support.all_uris)
        cf = Crazyflie(rw_cache='./cache')

        # Test
        for uri in self.test_rig_support.all_uris:
            with SyncCrazyflie(uri, cf=cf):
                pass
