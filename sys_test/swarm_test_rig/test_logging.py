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
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
import unittest

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
from sys_test.swarm_test_rig.rig_support import RigSupport


class TestLogging(unittest.TestCase):
    def setUp(self):
        cflib.crtp.init_drivers(enable_debug_driver=False)
        self.test_rig_support = RigSupport()

    def test_that_requested_logging_is_received_properly_from_one_cf(self):
        # Fixture
        uri = self.test_rig_support.all_uris[0]
        self.test_rig_support.restart_devices([uri])
        cf = Crazyflie(rw_cache='./cache')

        # Test and Assert
        with SyncCrazyflie(uri, cf=cf) as scf:
            self.assert_add_logging_and_get_non_zero_value(scf)

    def test_that_requested_logging_is_received_properly_from_all_cfs(self):
        # Fixture
        uris = self.test_rig_support.all_uris
        self.test_rig_support.restart_devices(uris)
        factory = CachedCfFactory(rw_cache='./cache')

        # Test and Assert
        with Swarm(uris, factory=factory) as swarm:
            swarm.parallel_safe(self.assert_add_logging_and_get_non_zero_value)

    def assert_add_logging_and_get_non_zero_value(self, scf):
        log_name = 'stabilizer.roll'
        expected = 0.0

        lg_conf = LogConfig(name='SysTest', period_in_ms=10)
        lg_conf.add_variable(log_name, 'float')

        with SyncLogger(scf, lg_conf) as logger:
            for log_entry in logger:
                actual = log_entry[1][log_name]
                break

        self.assertNotAlmostEqual(expected, actual, places=4)
