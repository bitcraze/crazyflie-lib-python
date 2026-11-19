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
from cflib.crazyflie.console import ConsoleError
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort

PATIENCE = 2.0
QUIET = 0.1

EAGAIN = 11
EPERM = 1
DISABLE_ALL = [0, 0xff, 0]


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


class FakeFirmware:
    """
    Answers the console catalog and control requests like the firmware does,
    and records them.
    """

    def __init__(self, link, sources, not_ready_answers=0):
        self.link = link
        self.sources = sources
        self.not_ready_answers = not_ready_answers
        self.enable_errno = 0
        self.answer = True
        self.requests = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._stop = threading.Event()
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                pk = self.link.uplink.get(timeout=0.05)
            except queue.Empty:
                continue
            if pk.port != CRTPPort.CONSOLE:
                continue
            request = list(pk.data)
            self.requests.put((pk.channel, request))
            if self.answer:
                self.link.deliver(pk.channel, self._answer(pk.channel, request))

    def _answer(self, channel, request):
        command = request[0]
        if self.not_ready_answers > 0:
            self.not_ready_answers -= 1
            return [command, EAGAIN]
        if channel == 3 and command == 1:
            return [1, 0, len(self.sources), 0x12, 0x34, 0x56, 0x78]
        if channel == 3 and command == 0:
            source_id = request[1]
            return [0, 0, source_id] + list(self.sources[source_id].encode('utf-8'))
        if channel == 2 and command == 0:
            if self.enable_errno:
                return [0, self.enable_errno]
            return [0, 0, request[1], request[2]]
        return [command, 88]

    def next_request(self):
        return self.requests.get(timeout=PATIENCE)

    def assert_no_request(self, test):
        try:
            request = self.requests.get(timeout=QUIET)
        except queue.Empty:
            return
        test.fail(f'Unexpected request {request}')


class ConsoleTestCase(unittest.TestCase):

    PROTOCOL_VERSION = 13
    SOURCES = ['deck:bcCam']

    def setUp(self):
        self.link = FakeLink()
        self.firmware = FakeFirmware(self.link, self.SOURCES)
        self.cf = Crazyflie(link=self.link)
        self.sut = self.cf.console

    def tearDown(self):
        self.cf.incoming.stop()
        self.firmware.stop()

    def connect(self):
        self.sut._connected(self.PROTOCOL_VERSION)
        if self.PROTOCOL_VERSION >= 13:
            self.assertEqual((2, DISABLE_ALL), self.firmware.next_request())

    def wait_for_lines(self, lines, count):
        deadline = threading.Event()
        for _ in range(int(PATIENCE / 0.01)):
            if len(lines) >= count:
                return lines
            deadline.wait(0.01)
        self.fail(f'Expected {count} lines, got {lines}')


class OldFirmwareConsoleTest(ConsoleTestCase):

    PROTOCOL_VERSION = 12

    def test_that_nothing_is_sent_when_connecting(self):
        # Test
        self.connect()

        # Assert
        self.firmware.assert_no_request(self)

    def test_that_only_the_stm32_console_is_listed(self):
        # Fixture
        self.connect()

        # Test
        actual = self.sut.list()

        # Assert
        self.assertEqual(['cf:stm32'], actual)
        self.firmware.assert_no_request(self)

    def test_that_the_stm32_console_can_be_opened_with_its_history(self):
        # Fixture
        received = TextCollector()
        self.cf.console.receivedChar.add_callback(received)
        self.link.deliver(0, b'early\nlater')
        received.wait_for('later')
        self.connect()
        self.link.deliver(0, b'\nnew\n')
        received.wait_for('new\n')
        lines = []

        # Test
        with self.sut.open('cf:stm32', line_cb=lines.append):
            pass

        # Assert
        self.assertEqual(['early', 'later', 'new'], lines)
        self.firmware.assert_no_request(self)

    def test_that_opening_a_sourced_console_fails(self):
        # Fixture
        self.connect()

        # Test
        # Assert
        with self.assertRaises(ConsoleError):
            self.sut.open('deck:bcCam')
        self.firmware.assert_no_request(self)


class SourcedConsoleTest(ConsoleTestCase):

    def test_that_consoles_left_open_are_stopped_when_connecting(self):
        # Test
        # Assert
        self.connect()

    def test_that_all_consoles_are_listed(self):
        # Fixture
        self.connect()

        # Test
        actual = self.sut.list()

        # Assert
        self.assertEqual(['cf:stm32', 'deck:bcCam'], actual)
        self.assertEqual((3, [1]), self.firmware.next_request())
        self.assertEqual((3, [0, 0]), self.firmware.next_request())

    def test_that_the_list_is_read_once(self):
        # Fixture
        self.connect()
        self.sut.list()
        self.firmware.next_request()
        self.firmware.next_request()

        # Test
        self.sut.list()

        # Assert
        self.firmware.assert_no_request(self)

    def test_that_requests_are_retried_until_the_firmware_is_ready(self):
        # Fixture
        self.firmware.not_ready_answers = 3

        # Test
        self.connect()
        actual = self.sut.list()

        # Assert
        self.assertEqual(['cf:stm32', 'deck:bcCam'], actual)

    def test_that_opening_enables_and_closing_disables_the_source(self):
        # Fixture
        self.connect()

        # Test
        handle = self.sut.open('deck:bcCam')
        self.firmware.next_request()
        self.firmware.next_request()
        enable = self.firmware.next_request()
        handle.close()
        disable = self.firmware.next_request()

        # Assert
        self.assertEqual((2, [0, 0, 1]), enable)
        self.assertEqual((2, [0, 0, 0]), disable)
        self.assertTrue(handle.closed)

    def test_that_output_is_passed_as_lines_and_text(self):
        # Fixture
        self.connect()
        lines = []
        text = TextCollector()
        handle = self.sut.open('deck:bcCam', text_cb=text, line_cb=lines.append)

        # Test
        self.link.deliver(1, b'\x00first li')
        self.link.deliver(1, b'\x00ne\r\nsecond\n')

        # Assert
        self.assertEqual(['first line', 'second'], self.wait_for_lines(lines, 2))
        self.assertEqual('first line\r\nsecond\n', text.wait_for('second\n'))
        handle.close()

    def test_that_lines_ending_with_newline_and_carriage_return_are_passed_without_it(self):
        # Fixture
        self.connect()
        lines = []
        handle = self.sut.open('deck:bcCam', line_cb=lines.append)

        # Test
        self.link.deliver(1, b'\x00get sta mac\n\rRead slot:0\n\r')
        self.link.deliver(1, b'\x00[WIFI] Init done\n')

        # Assert
        self.assertEqual(['get sta mac', 'Read slot:0', '[WIFI] Init done'], self.wait_for_lines(lines, 3))
        handle.close()

    def test_that_output_from_other_sources_is_not_passed(self):
        # Fixture
        self.connect()
        lines = []
        handle = self.sut.open('deck:bcCam', line_cb=lines.append)

        # Test
        self.link.deliver(1, b'\x05other\n')
        self.link.deliver(1, b'\x00mine\n')

        # Assert
        self.assertEqual(['mine'], self.wait_for_lines(lines, 1))
        handle.close()

    def test_that_output_received_before_opening_is_replayed(self):
        # Fixture
        self.link.deliver(1, b'\x00left open\n')
        self.connect()
        self.sut.list()
        self.link.deliver(1, b'\x00after list\n')
        received = TextCollector()
        self.cf.console.receivedChar.add_callback(received)
        self.link.deliver(0, b'sync')
        received.wait_for('sync')
        lines = []

        # Test
        handle = self.sut.open('deck:bcCam', line_cb=lines.append)

        # Assert
        self.assertEqual(['left open', 'after list'], lines)
        handle.close()

    def test_that_history_can_be_skipped(self):
        # Fixture
        self.connect()
        self.sut.list()
        self.link.deliver(1, b'\x00old\n')
        received = TextCollector()
        self.cf.console.receivedChar.add_callback(received)
        self.link.deliver(0, b'sync')
        received.wait_for('sync')
        lines = []

        # Test
        handle = self.sut.open('deck:bcCam', line_cb=lines.append, history=False)
        self.link.deliver(1, b'\x00new\n')

        # Assert
        self.assertEqual(['new'], self.wait_for_lines(lines, 1))
        handle.close()

    def test_that_the_source_stays_enabled_until_the_last_handle_is_closed(self):
        # Fixture
        self.connect()
        first = self.sut.open('deck:bcCam')
        second = self.sut.open('deck:bcCam')
        for _ in range(3):
            self.firmware.next_request()

        # Test
        first.close()
        self.firmware.assert_no_request(self)
        second.close()

        # Assert
        self.assertEqual((2, [0, 0, 0]), self.firmware.next_request())

    def test_that_an_unknown_console_cannot_be_opened(self):
        # Fixture
        self.connect()
        self.sut.list()
        self.firmware.next_request()
        self.firmware.next_request()

        # Test
        with self.assertRaises(ConsoleError):
            self.sut.open('deck:unknown')

        # Assert
        self.firmware.assert_no_request(self)

    def test_that_a_rejected_enable_raises_with_the_firmware_errno(self):
        # Fixture
        self.connect()
        self.firmware.enable_errno = EPERM

        # Test
        with self.assertRaises(ConsoleError) as context:
            self.sut.open('deck:bcCam')

        # Assert
        self.assertEqual(EPERM, context.exception.errno)

    def test_that_a_missing_answer_raises(self):
        # Fixture
        self.connect()
        self.firmware.answer = False

        # Test
        # Assert
        with self.assertRaises(ConsoleError):
            self.sut.list(timeout=PATIENCE + 1)

    def test_that_disconnecting_closes_handles(self):
        # Fixture
        self.connect()
        handle = self.sut.open('deck:bcCam')

        # Test
        self.cf.disconnected.call('uri')

        # Assert
        self.assertTrue(handle.closed)
        handle.close()
        with self.assertRaises(ConsoleError):
            self.sut.list()

    def test_that_blocking_calls_are_refused_from_cflib_callbacks(self):
        # Fixture
        self.connect()
        errors = []
        done = threading.Event()

        def callback(text):
            try:
                self.sut.list()
            except RuntimeError as e:
                errors.append(e)
            done.set()

        self.cf.console.receivedChar.add_callback(callback)

        # Test
        self.link.deliver(0, b'x')
        done.wait(PATIENCE)

        # Assert
        self.assertEqual(1, len(errors))
