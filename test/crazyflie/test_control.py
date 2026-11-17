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
"""
Tests of cf.control against a fake Crazyflie firmware.

The fake firmware runs on its own thread, which also plays the part of cflib's
incoming-packet thread: it runs the Control port callback.
"""
import queue
import struct
import threading
import time
import unittest
import zlib

from cflib.crazyflie.control import Control
from cflib.crazyflie.control import ControlBusyError
from cflib.crazyflie.control import ControlDisconnectedError
from cflib.crazyflie.control import ControlErrorCode
from cflib.crazyflie.control import ControlTimeoutError
from cflib.crazyflie.control import CrazyflieControlError
from cflib.crazyflie.control import EndpointError
from cflib.crazyflie.control import EndpointNotReadyError
from cflib.crazyflie.control import EndpointStatus
from cflib.crazyflie.control import FirmwareErrno
from cflib.crazyflie.control import MessageTooLargeError
from cflib.crazyflie.control import TypedValue
from cflib.crazyflie.control import UnexpectedResponseError
from cflib.crazyflie.control import UnknownEndpointError
from cflib.crazyflie.control import ValueType
from cflib.crazyflie.control_codec import decode_value
from cflib.crazyflie.control_codec import encode_value
from cflib.crazyflie.control_codec import fragment
from cflib.crazyflie.control_codec import Reassembler
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.callbacks import Caller

HOLD = None


def ok(request):
    return bytes((0x80, request[1]))


def value(request, typed_value_tlv):
    return bytes((0x81, request[1])) + typed_value_tlv


def error(request, code, detail=b''):
    return bytes((0x82, request[1], code, len(detail))) + detail


class FakeFirmware(threading.Thread):
    """The firmware side of CRTP port 10, with endpoints that answer from a dict.

    handler(endpoint_id, request) may replace the endpoints. It returns a list
    of (status, body) answers, or HOLD to keep the request for later.
    """

    def __init__(self, paths):
        super().__init__(name='FakeFirmware', daemon=True)
        self.paths = list(paths)
        self.slots = 4
        self.max_message = 256
        self.ready = {i: True for i in range(len(self.paths))}
        self.limits = {i: (256, 256) for i in range(len(self.paths))}
        self.eagain_count = 0
        self.crc_offset = 0
        self.before_reset_answer = None
        self.values = {}
        self.handler = None
        self.requests = []
        self.held = []
        self.uplink = []
        self.port_callback = None
        self._reassembler = Reassembler()
        self._queue = queue.Queue()

    # Called by the stub Crazyflie, on the caller's thread

    def receive(self, pk, expected_reply):
        self.uplink.append((pk.port, pk.channel, bytes(pk.data), expected_reply))
        self._queue.put(('up', pk.channel, bytes(pk.data)))

    # Called by the tests

    def answer(self, endpoint_id, status, body):
        """Send a tunnel message from the firmware thread"""
        self._queue.put(('answer', endpoint_id, status, bytes(body)))

    def send_raw(self, channel, data):
        self._queue.put(('raw', channel, bytes(data)))

    def run_on_thread(self, fn):
        self._queue.put(('call', fn))

    def stop(self):
        self._queue.put(None)
        self.join(1)

    def tunnel_uplink(self):
        return [data for port, channel, data, _ in self.uplink if channel == 2]

    # Firmware thread

    def run(self):
        while True:
            item = self._queue.get()
            if item is None:
                return
            if item[0] == 'up':
                self._uplink(item[1], item[2])
            elif item[0] == 'answer':
                self._send_message(*item[1:])
            elif item[0] == 'raw':
                self._deliver(item[1], item[2])
            elif item[0] == 'call':
                item[1]()

    def _deliver(self, channel, data):
        pk = CRTPPacket()
        pk.set_header(CRTPPort.CONTROL, channel)
        pk.data = data
        self.port_callback(pk)

    def _send_message(self, endpoint_id, status, body):
        for payload in fragment(bytes((endpoint_id, status)) + body):
            self._deliver(2, payload)

    def _uplink(self, channel, data):
        if channel == 0:
            self._catalog_command(data)
        elif channel == 1:
            self._endpoint_command(data)
        elif channel == 2:
            message = self._reassembler.feed(data)
            if message is not None:
                self._tunnel_request(message[0], message[1:])

    def _catalog_command(self, data):
        if self.eagain_count > 0:
            self.eagain_count -= 1
            self._deliver(0, bytes((data[0], FirmwareErrno.EAGAIN)))
            return
        if data[0] == 0x01:
            crc_data = b''.join(bytes((i,)) + p.encode() for i, p in enumerate(self.paths))
            crc = (zlib.crc32(crc_data) + self.crc_offset) & 0xffffffff
            self._deliver(0, struct.pack('<BBBIBH', 0x01, 0, len(self.paths), crc, self.slots, self.max_message)
                          + b'\xaa')  # a trailing byte from a later version
        elif data[0] == 0x00:
            endpoint_id = data[1]
            if endpoint_id >= len(self.paths):
                self._deliver(0, bytes((0x00, FirmwareErrno.ENOENT)))
            else:
                self._deliver(0, bytes((0x00, 0, endpoint_id)) + self.paths[endpoint_id].encode())
        else:
            self._deliver(0, bytes((data[0], FirmwareErrno.ENOSYS)))

    def _endpoint_command(self, data):
        if data[0] == 0x02:
            self._reassembler.reset()
            if self.before_reset_answer is not None:
                self._deliver(2, self.before_reset_answer)
            self._deliver(1, bytes((0x02, 0)))
        elif data[0] == 0x00:
            endpoint_id = data[1]
            if endpoint_id >= len(self.paths):
                self._deliver(1, bytes((0x00, FirmwareErrno.ENOENT)))
                return
            max_request, max_response = self.limits[endpoint_id]
            self._deliver(1, struct.pack('<BBBBHH', 0x00, 0, endpoint_id, int(self.ready[endpoint_id]),
                                         max_request, max_response) + b'\xbb\xcc')
        else:
            self._deliver(1, bytes((data[0], FirmwareErrno.ENOSYS)))

    def _tunnel_request(self, endpoint_id, request):
        self.requests.append((endpoint_id, request))
        if self.handler is not None:
            answers = self.handler(endpoint_id, request)
        else:
            answers = self._default_endpoint(endpoint_id, request)
        if answers is HOLD:
            self.held.append((endpoint_id, request))
            return
        for status, body in answers:
            self._send_message(endpoint_id, status, body)

    def _default_endpoint(self, endpoint_id, request):
        if not self.ready[endpoint_id]:
            return [(FirmwareErrno.ENOTCONN, request[:2])]
        path_len = request[2]
        path = request[3:3 + path_len].decode()
        key = (endpoint_id, path)
        if request[0] == 0x01:
            if key not in self.values:
                return [(0, error(request, ControlErrorCode.UNKNOWN_PATH, b'no such path'))]
            return [(0, value(request, self.values[key]))]
        if request[0] == 0x02:
            self.values[key] = request[3 + path_len:]
            return [(0, ok(request))]
        return [(0, ok(request))]


class StubCrazyflie:
    """The parts of Crazyflie that cf.control uses"""

    def __init__(self, firmware, protocol_version=14):
        self.firmware = firmware
        self.link = object()
        self.disconnected = Caller()
        self.connection_lost = Caller()
        self.protocol_version = protocol_version
        self.platform = self
        self.control = Control(self)

    def get_protocol_version(self):
        return self.protocol_version

    def add_port_callback(self, port, cb):
        assert port == CRTPPort.CONTROL
        self.firmware.port_callback = cb

    def send_packet(self, pk, expected_reply=(), resend=False, timeout=0.2):
        assert pk.is_data_size_valid()
        self.firmware.receive(pk, expected_reply)

    def is_called_by_incoming_handler_thread(self):
        return threading.current_thread() is self.firmware


def wait_until(predicate, timeout=1.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.001)
    return predicate()


class ControlTestBase(unittest.TestCase):

    PATHS = ['cf:stm32', 'deck:bcCam']

    def setUp(self):
        self.fw = FakeFirmware(self.PATHS)
        self.cf = StubCrazyflie(self.fw)
        self.sut = self.cf.control
        self.fw.start()
        self.fw.values[(1, 'stream.mjpeg_quality')] = encode_value(80, ValueType.U8)

    def tearDown(self):
        self.fw.stop()

    def cam(self):
        return self.sut.endpoint('deck:bcCam')


class InitTest(ControlTestBase):

    def test_init_sequence(self):
        # Test
        endpoints = self.sut.endpoints()

        # Assert
        self.assertEqual([(0, 'cf:stm32'), (1, 'deck:bcCam')], [(e.id, e.path) for e in endpoints])
        self.assertEqual([
            (CRTPPort.CONTROL, 1, b'\x02', (0x02,)),
            (CRTPPort.CONTROL, 0, b'\x01', (0x01,)),
            (CRTPPort.CONTROL, 0, b'\x00\x00', (0x00,)),
            (CRTPPort.CONTROL, 0, b'\x00\x01', (0x00,)),
        ], self.fw.uplink)

    def test_catalog_is_read_once_per_connection(self):
        # Fixture
        self.sut.endpoints()
        sent = len(self.fw.uplink)

        # Test
        self.sut.endpoints()
        self.sut.endpoint('cf:stm32')

        # Assert
        self.assertEqual(sent, len(self.fw.uplink))

    def test_info(self):
        info = self.sut.info()
        self.assertEqual((2, 4, 256), (info.count, info.max_in_flight, info.max_message))

    def test_eagain_is_retried(self):
        # Fixture
        self.fw.eagain_count = 3

        # Test
        endpoints = self.sut.endpoints()

        # Assert
        self.assertEqual(2, len(endpoints))
        self.assertEqual(4, sum(1 for _, ch, data, _ in self.fw.uplink if ch == 0 and data == b'\x01'))

    def test_eagain_until_timeout(self):
        self.fw.eagain_count = 1000
        with self.assertRaises(CrazyflieControlError) as cm:
            self.sut.endpoints(timeout=0.1)
        self.assertEqual(FirmwareErrno.EAGAIN, cm.exception.errno)

    def test_crc_mismatch_raises_and_is_not_cached(self):
        # Fixture
        self.fw.crc_offset = 1

        # Test
        with self.assertRaises(UnexpectedResponseError):
            self.sut.endpoints()
        self.fw.crc_offset = 0

        # Assert
        self.assertEqual(2, len(self.sut.endpoints()))

    def test_unknown_endpoint_path(self):
        with self.assertRaises(UnknownEndpointError):
            self.sut.endpoint('deck:nope')

    def test_protocol_13_gives_empty_catalog(self):
        # Fixture
        self.cf.protocol_version = 13

        # Test
        endpoints = self.sut.endpoints()

        # Assert
        self.assertEqual([], endpoints)
        self.assertIsNone(self.sut.info())
        self.assertEqual([], self.fw.uplink)
        with self.assertRaises(UnknownEndpointError):
            self.sut.endpoint('deck:bcCam')

    def test_not_connected(self):
        self.cf.link = None
        with self.assertRaises(ControlDisconnectedError):
            self.sut.endpoints()
        self.assertEqual([], self.fw.uplink)

    def test_tunnel_traffic_before_reset_answer_is_dropped(self):
        # Fixture: an earlier client's response arrives just before the RESET answer
        self.fw.before_reset_answer = b'\x80\x01\x00\x81\x00\x10\x01\x05'

        # Test
        with self.assertLogs('cflib.crazyflie.control', level='DEBUG') as logs:
            self.assertEqual(80, self.cam().get('stream.mjpeg_quality'))

        # Assert
        self.assertTrue(any('before RESET' in line for line in logs.output))

    def test_no_answer_times_out(self):
        self.fw.port_callback = lambda pk: None
        with self.assertRaises(ControlTimeoutError):
            self.sut.endpoints(timeout=0.1)


class EndpointStatusTest(ControlTestBase):

    def test_status(self):
        # Fixture
        self.fw.limits[1] = (64, 128)

        # Test
        status = self.cam().status()

        # Assert
        self.assertEqual(EndpointStatus(True, 64, 128), status)
        self.assertEqual((CRTPPort.CONTROL, 1, b'\x00\x01', (0x00,)), self.fw.uplink[-1])

    def test_is_ready(self):
        cam = self.cam()
        self.assertTrue(cam.is_ready())
        self.fw.ready[1] = False
        self.assertFalse(cam.is_ready())


class RequestTest(ControlTestBase):

    def test_get(self):
        # Fixture
        cam = self.cam()

        # Test
        typed = cam.get_typed('stream.mjpeg_quality')

        # Assert
        self.assertEqual(TypedValue(ValueType.U8, 80), typed)
        self.assertEqual(80, cam.get('stream.mjpeg_quality'))
        tunnel = self.fw.tunnel_uplink()
        request_id = tunnel[0][3]
        self.assertEqual(b'\x80\x01\x01' + bytes((request_id,)) + b'\x14stream.mjpeg_quality', tunnel[0])
        # Never sent with an expected reply
        self.assertTrue(all(reply == () for _, ch, _, reply in self.fw.uplink if ch == 2))

    def test_set_in_two_fragments(self):
        # Fixture
        cam = self.cam()

        # Test
        cam.set('wifi.ssid', 'a' * 32)

        # Assert
        tunnel = self.fw.tunnel_uplink()
        self.assertEqual(2, len(tunnel))
        self.assertEqual(0x00, tunnel[0][0])
        self.assertEqual(30, len(tunnel[0]))
        self.assertEqual(b'\x81' + b'a' * 18, tunnel[1])
        endpoint_id, request = self.fw.requests[0]
        self.assertEqual(1, endpoint_id)
        self.assertEqual(b'\x02' + request[1:2] + b'\x09wifi.ssid\x20\x20' + b'a' * 32, request)
        self.assertEqual('a' * 32, cam.get('wifi.ssid'))

    def test_set_int_with_type(self):
        cam = self.cam()
        cam.set('stream.mjpeg_quality', 81, ValueType.U8)
        self.assertEqual(TypedValue(ValueType.U8, 81), cam.get_typed('stream.mjpeg_quality'))

    def test_set_int_without_type_sends_nothing(self):
        cam = self.cam()
        with self.assertRaises(TypeError):
            cam.set('stream.mjpeg_quality', 81)
        with self.assertRaises(ValueError):
            cam.set('stream.mjpeg_quality', 300, ValueType.U8)
        self.assertEqual([], self.fw.tunnel_uplink())

    def test_cmd(self):
        # Fixture
        def handler(endpoint_id, request):
            if request[-1:] == b'v':
                return [(0, value(request, encode_value('done')))]
            return [(0, ok(request))]
        self.fw.handler = handler
        cam = self.cam()

        # Test
        # Assert
        self.assertIsNone(cam.cmd('a.go'))
        self.assertEqual('done', cam.cmd('a.v'))
        self.assertEqual(b'\x03', self.fw.requests[0][1][:1])

    def test_request_raw_sets_request_id_and_returns_whole_response(self):
        # Fixture
        cam = self.cam()

        # Test
        response = cam.request_raw(b'\x01\xee\x04nope')

        # Assert
        request = self.fw.requests[0][1]
        self.assertEqual(request[1], response[1])
        self.assertEqual(b'\x82', response[:1])

    def test_ids_walk_forward(self):
        cam = self.cam()
        for _ in range(3):
            cam.get('stream.mjpeg_quality')
        ids = [request[1] for _, request in self.fw.requests]
        self.assertEqual(3, len(set(ids)))

    def test_notify_is_ignored(self):
        # Fixture
        def handler(endpoint_id, request):
            notify = b'\xc0\x03a.b\x10\x01\x01'
            return [(0, notify), (0, value(request, encode_value(None)))]
        self.fw.handler = handler

        # Test
        # Assert
        self.assertIsNone(self.cam().get('a.b'))

    def test_too_large_for_the_bridge(self):
        cam = self.cam()
        with self.assertRaises(MessageTooLargeError):
            cam.set('a', b'x' * 252)
        self.assertEqual([], self.fw.tunnel_uplink())

    def test_too_large_for_the_endpoint_once_its_limits_are_known(self):
        # Fixture
        self.fw.limits[1] = (64, 64)
        cam = self.cam()
        cam.status()

        # Test
        with self.assertRaises(MessageTooLargeError):
            cam.set('a', b'x' * 60)

        # Assert
        self.assertEqual([], self.fw.tunnel_uplink())

    def test_default_timeout_is_3_s_and_global(self):
        self.assertEqual(3.0, self.sut.default_timeout)
        cam = self.cam()
        self.fw.handler = lambda endpoint_id, request: HOLD
        self.sut.default_timeout = 0.05
        start = time.monotonic()
        with self.assertRaises(ControlTimeoutError):
            cam.get('a')
        self.assertLess(time.monotonic() - start, 1.0)


class ErrorMappingTest(ControlTestBase):

    def _fail_with(self, status):
        self.fw.handler = lambda endpoint_id, request: [(status, request[:2])]

    def test_endpoint_not_ready(self):
        self.fw.ready[1] = False
        with self.assertRaises(EndpointNotReadyError):
            self.cam().get('stream.mjpeg_quality')

    def test_unknown_endpoint(self):
        self._fail_with(FirmwareErrno.ENOENT)
        with self.assertRaises(UnknownEndpointError):
            self.cam().get('a')

    def test_errno_outcome(self):
        cases = [
            (FirmwareErrno.EINVAL, True),
            (FirmwareErrno.EBADMSG, True),
            (FirmwareErrno.EIO, True),
            (FirmwareErrno.EMSGSIZE, False),
            (FirmwareErrno.EPROTO, False),
            (FirmwareErrno.ECONNRESET, False),
            (FirmwareErrno.ETIMEDOUT, False),
            (99, False),
        ]
        cam = self.cam()
        for status, outcome_known in cases:
            with self.subTest(status=status):
                self._fail_with(status)
                with self.assertRaises(CrazyflieControlError) as cm:
                    cam.get('a')
                self.assertEqual(status, cm.exception.errno)
                self.assertEqual(outcome_known, cm.exception.outcome_known)

    def test_control_error(self):
        with self.assertRaises(EndpointError) as cm:
            self.cam().get('no.such.path')
        self.assertEqual(ControlErrorCode.UNKNOWN_PATH, cm.exception.code)
        self.assertEqual('no such path', cm.exception.detail)

    def test_unknown_control_error_code_stays_int(self):
        self.fw.handler = lambda endpoint_id, request: [(0, error(request, 0x42))]
        with self.assertRaises(EndpointError) as cm:
            self.cam().get('a')
        self.assertEqual(0x42, cm.exception.code)

    def test_unexpected_response(self):
        self.fw.handler = lambda endpoint_id, request: [(0, ok(request))]
        with self.assertRaises(UnexpectedResponseError):
            self.cam().get('a')
        self.fw.handler = lambda endpoint_id, request: [(0, value(request, encode_value(None)))]
        with self.assertRaises(UnexpectedResponseError):
            self.cam().set('a', None)


class TimeoutAndBusyTest(ControlTestBase):

    def test_timeout_then_late_answer(self):
        # Fixture
        cam = self.cam()
        self.fw.handler = lambda endpoint_id, request: HOLD

        # Test
        with self.assertRaises(ControlTimeoutError):
            cam.get('stream.mjpeg_quality', timeout=0.1)
        late_id = self.fw.held[0][1][1]

        # The next request does not reuse the abandoned ID
        self.fw.handler = None
        self.assertEqual(80, cam.get('stream.mjpeg_quality'))
        self.assertNotEqual(late_id, self.fw.requests[1][1][1])

        # The late answer is dropped and clears the abandoned ID
        self.fw.answer(1, 0, bytes((0x81, late_id)) + encode_value(1, ValueType.U8))
        self.assertTrue(wait_until(lambda: (1, late_id) not in self.sut._session.abandoned))
        self.assertEqual(80, cam.get('stream.mjpeg_quality'))

    def test_enobufs_is_retried(self):
        # Fixture
        answers = [FirmwareErrno.ENOBUFS, FirmwareErrno.ENOBUFS]

        def handler(endpoint_id, request):
            if answers:
                return [(answers.pop(), request[:2])]
            return [(0, value(request, encode_value(7, ValueType.U8)))]
        self.fw.handler = handler

        # Test
        actual = self.cam().get('a')

        # Assert
        self.assertEqual(7, actual)
        self.assertEqual(3, len(self.fw.requests))

    def test_ebusy_is_retried_with_a_new_id(self):
        # Fixture
        def handler(endpoint_id, request):
            if len(self.fw.requests) == 1:
                return [(FirmwareErrno.EBUSY, request[:2])]
            return [(0, ok(request))]
        self.fw.handler = handler

        # Test
        self.cam().set('a', True)

        # Assert
        self.assertEqual(2, len(self.fw.requests))
        self.assertNotEqual(self.fw.requests[0][1][1], self.fw.requests[1][1][1])

    def test_busy_at_the_timeout(self):
        self.fw.handler = lambda endpoint_id, request: [(FirmwareErrno.ENOBUFS, request[:2])]
        with self.assertRaises(ControlBusyError):
            self.cam().get('a', timeout=0.1)
        self.assertGreater(len(self.fw.requests), 1)


class SubmitTest(ControlTestBase):

    def _submit(self, endpoint, message):
        done = threading.Event()
        result = {}

        def callback(error, response):
            result['error'] = error
            result['response'] = response
            result['thread'] = threading.current_thread()
            done.set()
        endpoint.submit(message, callback)
        return done, result

    def test_submit(self):
        # Test
        done, result = self._submit(self.cam(), b'\x01\x00\x14stream.mjpeg_quality')

        # Assert
        self.assertTrue(done.wait(1))
        self.assertIsNone(result['error'])
        self.assertEqual(b'\x81', result['response'][:1])
        self.assertIs(self.fw, result['thread'])

    def test_submit_reports_busy_at_once(self):
        # Fixture
        self.fw.handler = lambda endpoint_id, request: [(FirmwareErrno.ENOBUFS, request[:2])]

        # Test
        done, result = self._submit(self.cam(), b'\x01\x00\x01a')

        # Assert
        self.assertTrue(done.wait(1))
        self.assertIsInstance(result['error'], ControlBusyError)
        time.sleep(0.05)
        self.assertEqual(1, len(self.fw.requests))

    def test_submit_raises_busy_when_all_slots_are_in_flight(self):
        # Fixture
        self.fw.handler = lambda endpoint_id, request: HOLD
        cam = self.cam()
        for _ in range(4):
            self._submit(cam, b'\x01\x00\x01a')

        # Test
        # Assert
        with self.assertRaises(ControlBusyError):
            self._submit(cam, b'\x01\x00\x01a')

    def test_out_of_order_responses(self):
        # Fixture
        self.fw.handler = lambda endpoint_id, request: HOLD
        cam = self.cam()
        first = self._submit(cam, b'\x01\x00\x05first')
        second = self._submit(cam, b'\x01\x00\x06second')
        self.assertTrue(wait_until(lambda: len(self.fw.held) == 2))

        # Test
        for endpoint_id, request in reversed(self.fw.held):
            path = request[3:].decode()
            self.fw.answer(endpoint_id, 0, value(request, encode_value(path)))

        # Assert
        for (done, result), path in [(first, 'first'), (second, 'second')]:
            self.assertTrue(done.wait(1))
            self.assertEqual(path, decode_value(result['response'][2:]).value)

    def test_blocking_calls_from_threads_out_of_order(self):
        # Fixture
        self.fw.handler = lambda endpoint_id, request: HOLD
        cam = self.cam()
        results = {}

        def get(path):
            results[path] = cam.get(path)
        threads = [threading.Thread(target=get, args=(p,)) for p in ('a.one', 'a.two')]
        for t in threads:
            t.start()
        self.assertTrue(wait_until(lambda: len(self.fw.held) == 2))

        # Test
        for endpoint_id, request in reversed(self.fw.held):
            self.fw.answer(endpoint_id, 0, value(request, encode_value(request[3:].decode())))
        for t in threads:
            t.join(1)

        # Assert
        self.assertEqual({'a.one': 'a.one', 'a.two': 'a.two'}, results)

    def test_blocking_call_from_incoming_thread_raises(self):
        # Fixture
        cam = self.cam()
        result = {}
        done = threading.Event()

        def on_incoming_thread():
            try:
                cam.get('stream.mjpeg_quality')
            except Exception as e:
                result['error'] = e
            done.set()

        # Test
        self.fw.run_on_thread(on_incoming_thread)

        # Assert
        self.assertTrue(done.wait(1))
        self.assertIsInstance(result['error'], RuntimeError)


class DisconnectTest(ControlTestBase):

    def test_disconnect_wakes_waiting_calls(self):
        # Fixture
        cam = self.cam()
        self.fw.handler = lambda endpoint_id, request: HOLD
        errors = []

        def get():
            try:
                cam.get('a', timeout=5)
            except Exception as e:
                errors.append(e)
        thread = threading.Thread(target=get)
        thread.start()
        submitted = threading.Event()
        submit_errors = []
        cam.submit(b'\x01\x00\x01b', lambda error, response: (submit_errors.append(error), submitted.set()))
        self.assertTrue(wait_until(lambda: len(self.fw.held) == 2))

        # Test
        start = time.monotonic()
        self.cf.disconnected.call('radio://0/80/2M')
        thread.join(1)

        # Assert
        self.assertLess(time.monotonic() - start, 1)
        self.assertEqual(1, len(errors))
        self.assertIsInstance(errors[0], ControlDisconnectedError)
        self.assertTrue(submitted.wait(1))
        self.assertIsInstance(submit_errors[0], ControlDisconnectedError)

    def test_disconnect_clears_the_catalog(self):
        # Fixture
        cam = self.cam()

        # Test
        self.cf.connection_lost.call('radio://0/80/2M', 'lost')

        # Assert
        with self.assertRaises(ControlDisconnectedError):
            cam.get('stream.mjpeg_quality')
        self.fw.uplink.clear()
        self.assertEqual(2, len(self.sut.endpoints()))
        self.assertEqual(b'\x02', self.fw.uplink[0][2])

    def test_disconnect_wakes_catalog_read(self):
        # Fixture
        self.fw.port_callback = lambda pk: None
        errors = []

        def endpoints():
            try:
                self.sut.endpoints(timeout=5)
            except Exception as e:
                errors.append(e)
        thread = threading.Thread(target=endpoints)
        thread.start()
        self.assertTrue(wait_until(lambda: len(self.fw.uplink) == 1))

        # Test
        self.cf.disconnected.call('radio://0/80/2M')
        thread.join(1)

        # Assert
        self.assertIsInstance(errors[0], ControlDisconnectedError)


if __name__ == '__main__':
    unittest.main()
