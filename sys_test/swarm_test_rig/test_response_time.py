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
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from sys_test.swarm_test_rig.rig_support import RigSupport


class TestResponseTime(unittest.TestCase):
    ECHO = 0

    def setUp(self):
        cflib.crtp.init_drivers()
        self.test_rig_support = RigSupport()

        self.links = []

    def tearDown(self):
        for link in self.links:
            link.close()
        self.links = []

    def test_response_time_to_one_cf(self):
        # Fixture
        uri = self.test_rig_support.all_uris[0]
        self.test_rig_support.restart_devices([uri])
        link = self.connect_link(uri)
        seq_nr = 47
        expected_max_response_time = 0.01

        # Test
        time_send_echo = time.time()
        self.request_echo_with_seq_nr(link, seq_nr)
        response_timestamps = self.assert_wait_for_all_seq_nrs([link], seq_nr)
        response_time = response_timestamps[uri] - time_send_echo

        # Assert
        self.assertLess(response_time, expected_max_response_time)

    def test_response_time_to_all_cfs(self):
        # Fixture
        uris = self.test_rig_support.all_uris
        self.test_rig_support.restart_devices(uris)

        for uri in uris:
            self.connect_link(uri)

        seq_nr = 47
        expected_max_response_time = 0.1
        expected_mean_response_time = 0.05

        # Test
        time_send_echo = time.time()
        for link in self.links:
            self.request_echo_with_seq_nr(link, seq_nr)

        response_timestamps = self.assert_wait_for_all_seq_nrs(
            self.links, seq_nr)

        # Assert
        response_times = {}
        for uri, response_time in response_timestamps.items():
            response_times[uri] = response_time - time_send_echo

        times = response_times.values()
        max_time = max(times)
        mean_time = float(sum(times)) / len(times)

        # print(max_time, mean_time, times)
        self.assertLess(max_time, expected_max_response_time)
        self.assertLess(mean_time, expected_mean_response_time)

    def request_echo_with_seq_nr(self, link, seq_nr):
        pk = CRTPPacket()
        pk.set_header(CRTPPort.LINKCTRL, self.ECHO)
        pk.data = (seq_nr,)
        link.send_packet(pk)

    def assert_wait_for_all_seq_nrs(self, links, seq_nr, timeout=1):
        NO_BLOCKING = -1

        time_end = time.time() + timeout
        response_timestamps = {}
        while time.time() < time_end:
            for link in links:
                if link.uri not in response_timestamps:
                    response = link.receive_packet(wait=NO_BLOCKING)
                    if self._is_response_correct_seq_nr(response, seq_nr):
                        response_timestamps[link.uri] = time.time()

            if len(response_timestamps) == len(self.links):
                return response_timestamps

            time.sleep(0.001)

        self.fail('Time out while waiting for seq nrs.')

    def _is_response_correct_seq_nr(self, response, seq_nr):
        if response is not None:
            if response._get_channel() == self.ECHO and \
                    response._get_port() == CRTPPort.LINKCTRL:
                received_seq = response._get_data_t()[0]
                if received_seq == seq_nr:
                    return True

        return False

    def connect_link(self, uri):
        link = cflib.crtp.get_link_driver(uri, self._link_quality_cb,
                                          self._link_error_cb)
        self.assertIsNotNone(link)
        self.links.append(link)

        return link

    def _link_quality_cb(self, percentage):
        pass

    def _link_error_cb(self, errmsg):
        self.fail(errmsg)
