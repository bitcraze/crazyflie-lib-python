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
from unittest.mock import MagicMock

import struct

from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.localization import Localization


class LocalizationTest(unittest.TestCase):

    def setUp(self):
        self.cf_mock = MagicMock(spec=Crazyflie)
        self.sut = Localization(crazyflie=self.cf_mock)

    def test_that_checks_if_data_package_is_correctly_decoded(self):
        
        # fixture
        geo_bs_list = [0, 2, 4, 6, 8, 10, 12, 14]
        calib_bs_list = [1, 3, 5, 7, 9, 11, 13, 15]

        # test
        actual = self.sut.send_lh_persit_data_packet(geo_bs_list, calib_bs_list)

        # assert
        data_check = 2863289685
        expected = CRTPPacket()
        expected.port = CRTPPort.LOCALIZATION
        expected.channel = self.sut.GENERIC_CH
        expected.data = struct.pack('<I', data_check)
        
        actual_object = self.cf_mock.send_packet.call_args
        actual = actual_object[0][0]
        self.assertEqual(expected.port, actual.port)
        self.assertEqual(expected.channel, actual.channel)
        self.assertEqual(expected.data, actual.data)






