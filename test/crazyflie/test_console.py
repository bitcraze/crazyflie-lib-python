# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2026 Bitcraze AB
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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
import queue
import threading
import unittest

from cflib.crazyflie import Crazyflie
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort

PATIENCE = 2.0


class FakeLink:
    """A link that the test feeds with packets from the Crazyflie."""

    needs_resending = False

    def __init__(self):
        self.downlink = queue.Queue()
        self.uplink = queue.Queue()

    def receive_packet(self, wait=0):
        try:
            return self.downlink.get(timeout=wait if wait > 0 else 0.01)
        except queue.Empty:
            return None

    def send_packet(self, pk):
        self.uplink.put(pk)

    def close(self):
        pass

    def deliver(self, channel, data):
        pk = CRTPPacket()
        pk.set_header(CRTPPort.CONSOLE, channel)
        pk.data = bytearray(data)
        self.downlink.put(pk)


class TextCollector:
    """Collects console text and waits until it contains an expected string."""

    def __init__(self):
        self._text = ''
        self._changed = threading.Condition()

    def __call__(self, text):
        with self._changed:
            self._text += text
            self._changed.notify_all()

    def wait_for(self, expected):
        with self._changed:
            self._changed.wait_for(lambda: expected in self._text, PATIENCE)
            return self._text


class LocalConsoleTest(unittest.TestCase):

    def setUp(self):
        self.link = FakeLink()
        self.cf = Crazyflie(link=self.link)
        self.received = TextCollector()
        self.cf.console.receivedChar.add_callback(self.received)

    def tearDown(self):
        self.cf.incoming.stop()

    def test_that_channel_0_text_is_received(self):
        # Fixture
        self.link.deliver(0, b'Hello Crazyflie\n')

        # Test
        text = self.received.wait_for('\n')

        # Assert
        self.assertEqual('Hello Crazyflie\n', text)

    def test_that_other_channels_are_not_received_as_text(self):
        # Fixture
        self.link.deliver(1, b'\x00camera text')
        self.link.deliver(2, b'\x00\x00\xff\x00')
        self.link.deliver(3, b'\x01\x00\x01\x12\x34\x56\x78')
        self.link.deliver(0, b'end')

        # Test
        text = self.received.wait_for('end')

        # Assert
        self.assertEqual('end', text)

    def test_that_a_character_split_across_packets_is_decoded(self):
        # Fixture
        euro = '\u20ac'.encode('utf-8')
        self.link.deliver(0, b'a' + euro[:1])
        self.link.deliver(0, euro[1:] + b'b')

        # Test
        text = self.received.wait_for('b')

        # Assert
        self.assertEqual('a\u20acb', text)

    def test_that_invalid_utf8_is_replaced(self):
        # Fixture
        self.link.deliver(0, b'a\xffb')

        # Test
        text = self.received.wait_for('b')

        # Assert
        self.assertEqual('a\ufffdb', text)
