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
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crtp import RadioDriver
from cflib.drivers.crazyradio import Crazyradio


class TestSwarmConnection(unittest.TestCase):
    def setUp(self):
        cflib.crtp.init_drivers(enable_debug_driver=False)

        self.all_uris = [
            'radio://0/42/2M/E7E7E74201',
            'radio://0/42/2M/E7E7E74202',
            'radio://0/42/2M/E7E7E74203',
            'radio://0/42/2M/E7E7E74204',
            'radio://0/42/2M/E7E7E74205',
            'radio://0/42/2M/E7E7E74206',
            'radio://0/42/2M/E7E7E74207',
            'radio://0/42/2M/E7E7E74208',
            'radio://0/42/2M/E7E7E74209',
            'radio://0/42/2M/E7E7E7420A',
        ]

    def test_that_connection_time_scales_with_more_devices_without_cache(self):
        # Fixture
        self.restart_devices(self.all_uris)

        EXPECTED_CONNECTION_TIME = 5

        for nr_of_devices in range(1, len(self.all_uris)):
            # Test
            uris = self.all_uris[:nr_of_devices]

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
        self.restart_devices(self.all_uris)

        # Fill caches first by connecting to all devices
        factory = CachedCfFactory(rw_cache='./cache')
        with Swarm(self.all_uris, factory=factory):
            pass

        EXPECTED_CONNECTION_TIME = 1.5

        for nr_of_devices in range(1, len(self.all_uris)):
            # Test
            uris = self.all_uris[:nr_of_devices]

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
        # Test
        # Assert
        self.restart_devices(self.all_uris)

    def test_that_the_same_cf_object_can_be_connected_multiple_times(self):
        # Fixture
        cf = Crazyflie(rw_cache='./cache')

        lg_conf = LogConfig(name='SysTest', period_in_ms=10)
        lg_conf.add_variable('stabilizer.roll', 'float')

        # Test
        for uri in self.all_uris:
            with SyncCrazyflie(uri, cf=cf):
                pass

    # Utility functions ---------------------------------------------

    def restart_devices(self, uris):
        def send_packets(uris, value):
            for uri in uris:
                devid, channel, datarate, address = RadioDriver.parse_uri(uri)
                radio.set_channel(channel)
                radio.set_data_rate(datarate)
                radio.set_address(address)

                received_packet = False
                for i in range(100):
                    result = radio.send_packet((0xf3, 0xfe, value))
                    if result.ack is True:
                        received_packet = True
                        break

                self.assertTrue(received_packet)

        print('Restarting devices')

        BOOTLOADER_CMD_SYSOFF = 0x02
        BOOTLOADER_CMD_SYSON = 0x03

        radio = Crazyradio()
        send_packets(uris, BOOTLOADER_CMD_SYSOFF)
        time.sleep(0.1)
        send_packets(uris, BOOTLOADER_CMD_SYSON)
        radio.close()
        time.sleep(5)
