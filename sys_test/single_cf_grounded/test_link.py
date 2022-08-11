# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2021 Bitcraze AB
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
import struct
import time
import unittest

import numpy as np
from single_cf_grounded import TestSingleCfGrounded

import cflib.crtp
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort


class TestLink(TestSingleCfGrounded):

    # def test_scan(self):
    #     start_time = time.time()
    #     result = cflib.crtp.scan_interfaces()
    #     end_time = time.time()
    #     uris = [uri for (uri, msg) in result]
    #     self.assertEqual(len(uris), 2)
    #     self.assertIn("radio://*/80/2M/E7E7E7E7E7", uris)
    #     self.assertIn("usb://0", uris)
    #     self.assertLess(end_time - start_time, 2)

    # def test_latency_radio_s4(self):
    #     result = self.latency(self.radioUri, 4)
    #     self.assertLess(result, 8)

    # def test_latency_radio_s28(self):
    #     result = self.latency(self.radioUri, 28)
    #     self.assertLess(result, 8)

    def test_latency_usb_s4(self):
        result = self.latency(self.usbUri, 4, 1000)
        self.assertLess(result, 1)

    def test_latency_usb_s28(self):
        result = self.latency(self.usbUri, 28, 1000)
        self.assertLess(result, 1)

    # def test_bandwidth_radio_s4(self):
    #     result = self.bandwidth(self.radioUri, 4)
    #     self.assertGreater(result, 450)

    # def test_bandwidth_radio_s28(self):
    #     result = self.bandwidth(self.radioUri, 28)
    #     self.assertGreater(result, 450)

    def test_bandwidth_usb_s4(self):
        result = self.bandwidth(self.usbUri, 4, 1000)
        self.assertGreater(result, 1000)

    def test_bandwidth_usb_s28(self):
        result = self.bandwidth(self.usbUri, 28, 1000)
        self.assertGreater(result, 1500)

    def latency(self, uri, packet_size=4, count=500):
        link = cflib.crtp.get_link_driver(uri)
        # # wait until no more packets in queue
        # while True:
        #     pk = link.receive_packet(0.5)
        #     print(pk)
        #     if not pk or pk.header == 0xFF:
        #         break

        pk = CRTPPacket()
        pk.set_header(CRTPPort.LINKCTRL, 0)  # Echo channel

        latencies = []
        for i in range(count):
            pk.data = self.build_data(i, packet_size)

            start_time = time.time()
            link.send_packet(pk)
            while True:
                pk_ack = link.receive_packet(-1)
                if pk_ack.port == CRTPPort.LINKCTRL and pk_ack.channel == 0:
                    break
            end_time = time.time()

            # make sure we actually received the expected value
            i_recv, = struct.unpack('<I', pk_ack.data[0:4])
            self.assertEqual(i, i_recv)
            latencies.append((end_time - start_time) * 1000)
        link.close()
        result = np.min(latencies)
        print('Latency for {} (packet size {} B): {:.2f} ms'.format(uri, packet_size, result))
        return result

    def bandwidth(self, uri, packet_size=4, count=500):
        link = cflib.crtp.get_link_driver(uri, link_error_callback=self.error_cb)
        # # wait until no more packets in queue
        # while True:
        #     pk = link.receive_packet(0.5)
        #     if not pk:
        #         break

        # enqueue packets
        start_time = time.time()
        for i in range(count):
            pk = CRTPPacket()
            pk.set_header(CRTPPort.LINKCTRL, 0)  # Echo channel
            pk.data = self.build_data(i, packet_size)
            link.send_packet(pk)

        # get the result
        for i in range(count):
            while True:
                pk_ack = link.receive_packet(-1)
                if pk_ack.port == CRTPPort.LINKCTRL and pk_ack.channel == 0:
                    break
            # make sure we actually received the expected value
            i_recv, = struct.unpack('<I', pk_ack.data[0:4])
            self.assertEqual(i, i_recv)
        end_time = time.time()
        link.close()
        result = count / (end_time - start_time)
        kbps = (count * packet_size) / 1024 / (end_time - start_time)
        print('Bandwith for {} (packet size {} B): {:.2f} packets/s ({:.2f} kB/s)'.format(
            uri, packet_size, result, kbps))
        return result

    def error_cb(self, error):
        self.assertIsNone(None, error)

    def build_data(self, i, packet_size):
        assert (packet_size % 4 == 0)
        repeats = packet_size // 4
        return struct.pack('<' + 'I'*repeats, *[i]*repeats)


if __name__ == '__main__':
    unittest.main()
