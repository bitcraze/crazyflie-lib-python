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
import ipaddress
import unittest

from cflib.crazyflie.control_codec import build_cmd
from cflib.crazyflie.control_codec import build_get
from cflib.crazyflie.control_codec import build_set
from cflib.crazyflie.control_codec import ControlError
from cflib.crazyflie.control_codec import ControlErrorCode
from cflib.crazyflie.control_codec import decode_notify
from cflib.crazyflie.control_codec import decode_value
from cflib.crazyflie.control_codec import encode_path
from cflib.crazyflie.control_codec import encode_value
from cflib.crazyflie.control_codec import fragment
from cflib.crazyflie.control_codec import MalformedValueError
from cflib.crazyflie.control_codec import MessageKind
from cflib.crazyflie.control_codec import parse_response
from cflib.crazyflie.control_codec import Reassembler
from cflib.crazyflie.control_codec import TypedValue
from cflib.crazyflie.control_codec import UnknownValue
from cflib.crazyflie.control_codec import ValueType


class ValueRoundTripTest(unittest.TestCase):

    CASES = [
        (ValueType.NULL, None, b'\x00\x00'),
        (ValueType.BOOL, False, b'\x01\x01\x00'),
        (ValueType.BOOL, True, b'\x01\x01\x01'),
        (ValueType.U8, 0, b'\x10\x01\x00'),
        (ValueType.U8, 255, b'\x10\x01\xff'),
        (ValueType.I8, -128, b'\x11\x01\x80'),
        (ValueType.I8, 127, b'\x11\x01\x7f'),
        (ValueType.U16, 0x1234, b'\x12\x02\x34\x12'),
        (ValueType.I16, -2, b'\x13\x02\xfe\xff'),
        (ValueType.U32, 0xdeadbeef, b'\x14\x04\xef\xbe\xad\xde'),
        (ValueType.I32, -(1 << 31), b'\x15\x04\x00\x00\x00\x80'),
        (ValueType.U64, (1 << 64) - 1, b'\x16\x08' + b'\xff' * 8),
        (ValueType.I64, -1, b'\x17\x08' + b'\xff' * 8),
        (ValueType.STRING, '', b'\x20\x00'),
        (ValueType.STRING, 'hé', b'\x20\x03h\xc3\xa9'),
        (ValueType.BYTES, b'', b'\x21\x00'),
        (ValueType.BYTES, b'\x00\xff', b'\x21\x02\x00\xff'),
        (ValueType.IPV4, ipaddress.IPv4Address('192.168.4.1'), b'\x22\x04\xc0\xa8\x04\x01'),
    ]

    def test_every_type_round_trips(self):
        for value_type, value, wire in self.CASES:
            with self.subTest(type=value_type, value=value):
                # Test
                encoded = encode_value(value, value_type)
                decoded = decode_value(encoded)

                # Assert
                self.assertEqual(wire, encoded)
                self.assertEqual(TypedValue(value_type, value), decoded)
                self.assertIs(type(value), type(decoded.value))
                self.assertIsInstance(decoded.type, ValueType)

    def test_inferred_types(self):
        cases = [
            (None, ValueType.NULL),
            (True, ValueType.BOOL),
            ('abc', ValueType.STRING),
            (b'abc', ValueType.BYTES),
            (bytearray(b'abc'), ValueType.BYTES),
            (ipaddress.IPv4Address('10.0.0.1'), ValueType.IPV4),
        ]
        for value, expected_type in cases:
            with self.subTest(value=value):
                self.assertEqual(expected_type, encode_value(value)[0])

    def test_bytes_decode_as_bytes(self):
        self.assertEqual(TypedValue(ValueType.BYTES, b'abc'), decode_value(encode_value(bytearray(b'abc'))))

    def test_ipv4_from_str_with_explicit_type(self):
        self.assertEqual(b'\x22\x04\x0a\x00\x00\x01', encode_value('10.0.0.1', ValueType.IPV4))

    def test_value_type_as_plain_int(self):
        self.assertEqual(b'\x12\x02\x01\x00', encode_value(1, 0x12))

    def test_unknown_value_is_sent_as_is(self):
        self.assertEqual(b'\x30\x02\x01\x02', encode_value(UnknownValue(0x30, b'\x01\x02')))

    def test_unknown_type_decodes_to_unknown_value(self):
        # Test
        actual = decode_value(b'\x30\x03abc')

        # Assert
        self.assertEqual(TypedValue(0x30, UnknownValue(0x30, b'abc')), actual)

    def test_reserved_extension_type_decodes_to_unknown_value(self):
        self.assertEqual(UnknownValue(0x80, b''), decode_value(b'\x80\x00').value)


class EncodeChecksTest(unittest.TestCase):

    def test_int_without_type_raises_type_error(self):
        with self.assertRaises(TypeError):
            encode_value(80)

    def test_unsupported_python_type_raises_type_error(self):
        with self.assertRaises(TypeError):
            encode_value(1.5)

    def test_range_checks_on_explicit_types(self):
        cases = [
            (ValueType.U8, -1), (ValueType.U8, 256), (ValueType.U8, 300),
            (ValueType.I8, -129), (ValueType.I8, 128),
            (ValueType.U16, 0x10000), (ValueType.I16, -0x8001), (ValueType.I16, 0x8000),
            (ValueType.U32, 1 << 32), (ValueType.I32, 1 << 31),
            (ValueType.U64, -1), (ValueType.U64, 1 << 64), (ValueType.I64, 1 << 63),
            (ValueType.BOOL, 2),
        ]
        for value_type, value in cases:
            with self.subTest(type=value_type, value=value):
                with self.assertRaises(ValueError):
                    encode_value(value, value_type)

    def test_wrong_python_type_for_explicit_type(self):
        cases = [
            (ValueType.U8, '1'), (ValueType.NULL, 0), (ValueType.BOOL, 'yes'),
            (ValueType.STRING, b'abc'), (ValueType.BYTES, 'abc'), (ValueType.IPV4, 1),
        ]
        for value_type, value in cases:
            with self.subTest(type=value_type, value=value):
                with self.assertRaises(TypeError):
                    encode_value(value, value_type)

    def test_string_with_nul_is_refused(self):
        with self.assertRaises(ValueError):
            encode_value('a\x00b')

    def test_value_longer_than_255_bytes_is_refused(self):
        with self.assertRaises(ValueError):
            encode_value(b'x' * 256)

    def test_unknown_explicit_type_code_is_refused(self):
        with self.assertRaises(ValueError):
            encode_value(b'x', 0x30)


class DecodeChecksTest(unittest.TestCase):

    MALFORMED = [
        ('empty', b''),
        ('no len byte', b'\x10'),
        ('len past the message', b'\x21\x05abc'),
        ('null with data', b'\x00\x01\x00'),
        ('bool too long', b'\x01\x02\x00\x00'),
        ('bool empty', b'\x01\x00'),
        ('bool not 0 or 1', b'\x01\x01\x02'),
        ('u8 too long', b'\x10\x02\x00\x00'),
        ('u16 too short', b'\x12\x01\x00'),
        ('i32 too short', b'\x15\x03\x00\x00\x00'),
        ('u64 too short', b'\x16\x04\x00\x00\x00\x00'),
        ('ipv4 too short', b'\x22\x03\x01\x02\x03'),
        ('string not UTF-8', b'\x20\x02\xc3\x28'),
        ('string with NUL', b'\x20\x03a\x00b'),
        ('trailing bytes', b'\x10\x01\x00\x00'),
    ]

    def test_malformed_values_are_rejected(self):
        for name, data in self.MALFORMED:
            with self.subTest(name):
                with self.assertRaises(MalformedValueError):
                    decode_value(data)

    def test_malformed_value_error_is_a_control_error(self):
        self.assertTrue(issubclass(MalformedValueError, ControlError))


class RequestTest(unittest.TestCase):

    def test_get(self):
        # From the worked example
        self.assertEqual(b'\x01\x07\x13meta.schema_modules', build_get(7, 'meta.schema_modules'))

    def test_set(self):
        # From the worked example
        expected = b'\x02\x08\x09wifi.ssid\x20\x20' + b'a' * 32
        actual = build_set(8, 'wifi.ssid', 'a' * 32)
        self.assertEqual(expected, actual)
        self.assertEqual(46, len(actual))

    def test_set_int_needs_type(self):
        with self.assertRaises(TypeError):
            build_set(1, 'a', 3)
        self.assertEqual(b'\x02\x01\x01a\x10\x01\x03', build_set(1, 'a', 3, ValueType.U8))

    def test_cmd_without_and_with_argument(self):
        self.assertEqual(b'\x03\x02\x01a', build_cmd(2, 'a'))
        self.assertEqual(b'\x03\x02\x01a\x00\x00', build_cmd(2, 'a', None))
        self.assertEqual(b'\x03\x02\x01a\x13\x02\xff\xff', build_cmd(2, 'a', -1, ValueType.I16))

    def test_path_rules(self):
        for path in ['', 'café', 'a\x00b', 'a' * 256]:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    encode_path(path)
        self.assertEqual(b'\x03a.b', encode_path('a.b'))


class ResponseTest(unittest.TestCase):

    def test_ok(self):
        self.assertEqual((MessageKind.OK, 8, None, None, None), parse_response(b'\x80\x08'))

    def test_value(self):
        # From the worked example: an empty schema table
        actual = parse_response(b'\x81\x07\x21\x01\x00')
        self.assertEqual(MessageKind.VALUE, actual.kind)
        self.assertEqual(7, actual.request_id)
        self.assertEqual(TypedValue(ValueType.BYTES, b'\x00'), actual.value)

    def test_error(self):
        actual = parse_response(b'\x82\x03\x03\x04nope')
        self.assertEqual(ControlErrorCode.UNKNOWN_PATH, actual.error_code)
        self.assertIsInstance(actual.error_code, ControlErrorCode)
        self.assertEqual('nope', actual.detail)

    def test_error_with_unknown_code_keeps_int(self):
        actual = parse_response(b'\x82\x03\x42\x00')
        self.assertEqual(0x42, actual.error_code)
        self.assertNotIsInstance(actual.error_code, ControlErrorCode)
        self.assertEqual('', actual.detail)

    def test_error_detail_is_never_fatal(self):
        self.assertEqual('�', parse_response(b'\x82\x03\x09\x01\xff').detail)

    def test_other_kind_is_returned_without_body(self):
        self.assertEqual((0x83, 1, None, None, None), parse_response(b'\x83\x01\x00'))

    def test_malformed_responses(self):
        cases = [b'', b'\x80', b'\x80\x01\x00', b'\x81\x01', b'\x81\x01\x10\x02\x00',
                 b'\x81\x01\x10\x01\x00\x00', b'\x82\x01\x01', b'\x82\x01\x01\x03ab', b'\x82\x01\x01\x00x']
        for data in cases:
            with self.subTest(data=data):
                with self.assertRaises(MalformedValueError):
                    parse_response(data)


class NotifyTest(unittest.TestCase):

    def test_worked_example(self):
        # NOTIFY stream.fps_max u8 15
        actual = decode_notify(b'\xc0\x0estream.fps_max\x10\x01\x0f')
        self.assertEqual(('stream.fps_max', TypedValue(ValueType.U8, 15)), actual)
        self.assertIsInstance(actual[0], str)

    def test_every_value_type(self):
        for value_type, value, wire in ValueRoundTripTest.CASES:
            with self.subTest(type=value_type, value=value):
                self.assertEqual(('a.b', TypedValue(value_type, value)), decode_notify(b'\xc0\x03a.b' + wire))

    def test_unknown_value_type(self):
        self.assertEqual(('a', TypedValue(0x30, UnknownValue(0x30, b'xy'))), decode_notify(b'\xc0\x01a\x30\x02xy'))

    def test_accepts_bytearray(self):
        self.assertEqual(('a', TypedValue(ValueType.NULL, None)), decode_notify(bytearray(b'\xc0\x01a\x00\x00')))

    MALFORMED = [
        ('empty', b''),
        ('not a NOTIFY', b'\x81\x01a\x00\x00'),
        ('unknown notification kind', b'\xc1\x01a\x00\x00'),
        ('no path length', b'\xc0'),
        ('empty path', b'\xc0\x00\x00\x00'),
        ('path past the end', b'\xc0\x05a.b'),
        ('path not ASCII', b'\xc0\x02a\xe9\x00\x00'),
        ('path with NUL', b'\xc0\x03a\x00b\x00\x00'),
        ('no value', b'\xc0\x03a.b'),
        ('value without len', b'\xc0\x03a.b\x10'),
        ('value truncated', b'\xc0\x03a.b\x12\x02\x01'),
        ('value with bad length', b'\xc0\x03a.b\x10\x02\x01\x00'),
        ('bool not 0 or 1', b'\xc0\x03a.b\x01\x01\x02'),
        ('trailing bytes', b'\xc0\x03a.b\x10\x01\x01\x00'),
        ('two values', b'\xc0\x03a.b\x00\x00\x00\x00'),
    ]

    def test_malformed_notify_is_rejected(self):
        for name, data in self.MALFORMED:
            with self.subTest(name):
                with self.assertRaises(MalformedValueError):
                    decode_notify(data)


class FragmentTest(unittest.TestCase):

    def _message(self, length):
        return bytes(i & 0xff for i in range(length))

    def test_one_byte(self):
        self.assertEqual([b'\x80\x00'], fragment(self._message(1)))

    def test_29_bytes_is_one_packet(self):
        packets = fragment(self._message(29))
        self.assertEqual(1, len(packets))
        self.assertEqual(30, len(packets[0]))
        self.assertEqual(0x80, packets[0][0])

    def test_30_bytes_is_two_packets(self):
        packets = fragment(self._message(30))
        self.assertEqual([0x00, 0x81], [p[0] for p in packets])
        self.assertEqual([30, 2], [len(p) for p in packets])

    def test_300_bytes(self):
        packets = fragment(self._message(300))
        self.assertEqual(11, len(packets))
        self.assertEqual(list(range(10)) + [0x8a], [p[0] for p in packets])
        self.assertTrue(all(len(p) <= 30 for p in packets))
        self.assertEqual(self._message(300), b''.join(p[1:] for p in packets))

    def test_worked_example_two_packet_set(self):
        # Tunnel message: endpoint 1, then the Control request
        message = b'\x01' + build_set(8, 'wifi.ssid', 'a' * 32)
        packets = fragment(message)
        self.assertEqual(b'\x00\x01\x02\x08\x09wifi.ssid\x20\x20' + b'a' * 14, packets[0])
        self.assertEqual(b'\x81' + b'a' * 18, packets[1])

    def test_limits(self):
        with self.assertRaises(ValueError):
            fragment(b'')
        self.assertEqual(128, len(fragment(bytes(128 * 29))))
        with self.assertRaises(ValueError):
            fragment(bytes(128 * 29 + 1))


class ReassemblerTest(unittest.TestCase):

    def setUp(self):
        self.sut = Reassembler()

    def _feed_all(self, packets):
        out = []
        for p in packets:
            message = self.sut.feed(p)
            if message is not None:
                out.append(message)
        return out

    def test_round_trip(self):
        for length in [1, 29, 30, 300]:
            with self.subTest(length=length):
                message = bytes(i & 0xff for i in range(length))
                self.assertEqual([message], self._feed_all(fragment(message)))

    def test_gap_drops_the_message(self):
        packets = fragment(bytes(100))
        del packets[1]
        self.assertEqual([], self._feed_all(packets))
        self.assertEqual(1, self.sut.dropped)

    def test_packets_after_gap_are_ignored_until_index_0(self):
        first = fragment(bytes(100))
        second = fragment(b'\x01' * 40)
        self.assertEqual([b'\x01' * 40], self._feed_all([first[0], first[2], first[3], second[0], second[1]]))

    def test_index_0_drops_partial_message(self):
        first = fragment(bytes(100))
        second = fragment(b'\x02' * 5)
        self.assertEqual([b'\x02' * 5], self._feed_all([first[0], first[1], second[0]]))
        self.assertEqual(1, self.sut.dropped)

    def test_continuation_without_start_is_ignored(self):
        self.assertEqual([], self._feed_all([b'\x81abc', b'\x01abc']))

    def test_repeated_fragment_drops_message(self):
        packets = fragment(bytes(60))
        self.assertEqual([], self._feed_all([packets[0], packets[1], packets[1], packets[2]]))

    def test_empty_packet_is_ignored(self):
        self.assertEqual([b'a'], self._feed_all([b'', b'\x80a']))

    def test_reset_drops_partial_message(self):
        packets = fragment(bytes(60))
        self.sut.feed(packets[0])
        self.sut.reset()
        self.assertEqual([], self._feed_all(packets[1:]))


if __name__ == '__main__':
    unittest.main()
