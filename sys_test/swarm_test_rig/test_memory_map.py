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
import time
import unittest

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.mem import MemoryElement
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
from sys_test.swarm_test_rig.rig_support import RigSupport


class TestMemoryMapping(unittest.TestCase):
    def setUp(self):
        cflib.crtp.init_drivers(enable_debug_driver=False)
        self.test_rig_support = RigSupport()

    def test_memory_mapping_with_one_cf(self):
        # Fixture
        uri = self.test_rig_support.all_uris[0]
        self.test_rig_support.restart_devices([uri])
        cf = Crazyflie(rw_cache='./cache')

        # Test and Assert
        with SyncCrazyflie(uri, cf=cf) as scf:
            self.assert_memory_mapping(scf)

    def test_memory_mapping_with_all_cfs(self):
        # Fixture
        uris = self.test_rig_support.all_uris
        self.test_rig_support.restart_devices(uris)
        factory = CachedCfFactory(rw_cache='./cache')

        # Test and Assert
        with Swarm(uris, factory=factory) as swarm:
            swarm.parallel_safe(self.assert_memory_mapping)

    def test_memory_mapping_with_reuse_of_cf_object(self):
        # Fixture
        uri = self.test_rig_support.all_uris[0]
        self.test_rig_support.restart_devices([uri])
        cf = Crazyflie(rw_cache='./cache')

        # Test and Assert
        for connections in range(10):
            with SyncCrazyflie(uri, cf=cf) as scf:
                for mem_ops in range(5):
                    self.assert_memory_mapping(scf)

    # Utils

    def assert_memory_mapping(self, scf):
        mems = scf.cf.mem.get_mems(MemoryElement.TYPE_MEMORY_TESTER)
        count = len(mems)
        self.assertEqual(1, count, 'unexpected number of memories found')

        self.verify_reading_memory_data(mems)
        self.verify_writing_memory_data(mems, scf)

    def verify_writing_memory_data(self, mems, scf):
        self.wrote_data = False
        scf.cf.param.set_value('memTst.resetW', '1')
        time.sleep(0.1)
        mems[0].write_data(5, 1000, self._data_written)
        while not self.wrote_data:
            time.sleep(1)
        log_conf = LogConfig(name='memtester', period_in_ms=100)
        log_conf.add_variable('memTst.errCntW', 'uint32_t')
        with SyncLogger(scf, log_conf) as logger:
            for log_entry in logger:
                errorCount = log_entry[1]['memTst.errCntW']
                self.assertEqual(0, errorCount)
                break

    def verify_reading_memory_data(self, mems):
        self.got_data = False
        mems[0].read_data(5, 1000, self._data_read)
        while not self.got_data:
            time.sleep(1)

    def _data_read(self, mem):
        self.got_data = True

    def _data_written(self, mem, address):
        self.wrote_data = True
