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

from cflib.crtp.crtpstack import CRTPPacket


class CRTPPacketTest(unittest.TestCase):

    def setUp(self):
        self.callback_count = 0
        self.sut = CRTPPacket()

    def test_that_port_and_channle_is_encoded_in_header(self):
        # Fixture
        self.sut.set_header(2, 1)

        # Test
        actual = self.sut.get_header()

        # Assert
        expected = 0x2d
        self.assertEqual(expected, actual)

    def test_that_port_is_truncated_in_header(self):
        # Fixture
        port = 0xff
        self.sut.set_header(port, 0)

        # Test
        actual = self.sut.get_header()

        # Assert
        expected = 0xfc
        self.assertEqual(expected, actual)

    def test_that_channel_is_truncated_in_header(self):
        # Fixture
        channel = 0xff
        self.sut.set_header(0, channel)

        # Test
        actual = self.sut.get_header()

        # Assert
        expected = 0x0f
        self.assertEqual(expected, actual)

    def test_that_port_and_channel_is_encoded_in_header_when_set_separat(self):
        # Fixture
        self.sut.port = 2
        self.sut.channel = 1

        # Test
        actual = self.sut.get_header()

        # Assert
        expected = 0x2d
        self.assertEqual(expected, actual)

    def test_that_default_header_is_set_when_constructed(self):
        # Fixture

        # Test
        actual = self.sut.get_header()

        # Assert
        expected = 0x0c
        self.assertEqual(expected, actual)

    def test_that_header_is_set_when_constructed(self):
        # Fixture
        sut = CRTPPacket(header=0x21)

        # Test
        actual = sut.get_header()

        # Assert
        self.assertEqual(0x2d, actual)
        self.assertEqual(2, sut.port)
        self.assertEqual(1, sut.channel)
