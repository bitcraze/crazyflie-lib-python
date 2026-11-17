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
Byte-level code for the Control bridge (CRTP port 10).

This module has no dependency on a Crazyflie, so it can be tested on its own.
It contains:

* the Control value encoding (type, len, data TLV) and its checks,
* builders for GET, SET and CMD requests and a parser for responses,
* a decoder for NOTIFY messages,
* the fragmenter and reassembler used on the tunnel channel (channel 2).
"""
import ipaddress
import struct
from enum import IntEnum
from typing import NamedTuple
from typing import Optional
from typing import Union

__author__ = 'Bitcraze AB'
__all__ = ['ValueType', 'TypedValue', 'UnknownValue', 'MessageKind',
           'ControlErrorCode', 'ControlResponse', 'ControlError',
           'MalformedValueError', 'NO_ARG', 'encode_value', 'decode_value',
           'encode_path', 'build_get', 'build_set', 'build_cmd',
           'parse_response', 'decode_notify', 'fragment', 'Reassembler',
           'FRAGMENT_PAYLOAD_SIZE', 'MAX_FRAGMENTS', 'MAX_TUNNEL_MESSAGE']

# Bytes of message carried by one channel 2 packet, after the header byte
FRAGMENT_PAYLOAD_SIZE = 29
# The fragment index has 7 bits
MAX_FRAGMENTS = 128
# The largest message the fragment format can carry
MAX_TUNNEL_MESSAGE = MAX_FRAGMENTS * FRAGMENT_PAYLOAD_SIZE

_LAST_FRAGMENT = 0x80
_INDEX_MASK = 0x7f


class ControlError(Exception):
    """Base class for every error raised by cf.control"""


class MalformedValueError(ControlError):
    """Bytes received from the Crazyflie break the Control encoding rules"""


class ValueType(IntEnum):
    """Control value type codes"""
    NULL = 0x00
    BOOL = 0x01
    U8 = 0x10
    I8 = 0x11
    U16 = 0x12
    I16 = 0x13
    U32 = 0x14
    I32 = 0x15
    U64 = 0x16
    I64 = 0x17
    STRING = 0x20
    BYTES = 0x21
    IPV4 = 0x22


class MessageKind(IntEnum):
    """Control message kinds"""
    GET = 0x01
    SET = 0x02
    CMD = 0x03
    OK = 0x80
    VALUE = 0x81
    ERROR = 0x82
    NOTIFY = 0xc0


class ControlErrorCode(IntEnum):
    """Error codes carried by a Control ERROR response"""
    MALFORMED_MESSAGE = 0x01
    UNKNOWN_OPERATION = 0x02
    UNKNOWN_PATH = 0x03
    UNSUPPORTED_VALUE_TYPE = 0x04
    INVALID_VALUE = 0x05
    READ_ONLY = 0x06
    COMMAND_REJECTED = 0x07
    BUSY = 0x08
    INTERNAL_ERROR = 0x09


class UnknownValue(NamedTuple):
    """A value whose type code this library does not know"""
    type_code: int
    data: bytes


class TypedValue(NamedTuple):
    """A value with its wire type.

    type is a ValueType, or a plain int for an unknown type code (the value is
    then an UnknownValue).
    """
    type: Union[ValueType, int]
    value: object


class ControlResponse(NamedTuple):
    """A parsed Control response.

    value is set for VALUE, error_code and detail for ERROR. error_code is a
    ControlErrorCode, or a plain int for a code this library does not know.
    """
    kind: int
    request_id: int
    value: Optional[TypedValue] = None
    error_code: Optional[Union[ControlErrorCode, int]] = None
    detail: Optional[str] = None


class _NoArg:
    def __repr__(self):
        return 'NO_ARG'


# Marks a CMD without argument. None is a value: it is sent as null.
NO_ARG = _NoArg()

# struct format and byte length of the integer types
_INT_FORMATS = {
    ValueType.U8: '<B',
    ValueType.I8: '<b',
    ValueType.U16: '<H',
    ValueType.I16: '<h',
    ValueType.U32: '<I',
    ValueType.I32: '<i',
    ValueType.U64: '<Q',
    ValueType.I64: '<q',
}

_INT_RANGES = {}
for _t, _f in _INT_FORMATS.items():
    _bits = struct.calcsize(_f) * 8
    if _f[1].isupper():
        _INT_RANGES[_t] = (0, (1 << _bits) - 1)
    else:
        _INT_RANGES[_t] = (-(1 << (_bits - 1)), (1 << (_bits - 1)) - 1)

_FIXED_LENGTHS = {ValueType.NULL: 0, ValueType.BOOL: 1, ValueType.IPV4: 4}
_FIXED_LENGTHS.update({t: struct.calcsize(f) for t, f in _INT_FORMATS.items()})

_MAX_TLV_DATA = 0xff


def _tlv(type_code, data):
    if len(data) > _MAX_TLV_DATA:
        raise ValueError('Value is {} bytes, a Control value holds at most {}'.format(
            len(data), _MAX_TLV_DATA))
    return bytes((type_code, len(data))) + bytes(data)


def _encode_string(value):
    data = value.encode('utf-8')
    if b'\x00' in data:
        raise ValueError('Control strings cannot contain NUL')
    return data


def _infer_type(value):
    if value is None:
        return ValueType.NULL
    if isinstance(value, bool):
        return ValueType.BOOL
    if isinstance(value, int):
        raise TypeError('An int needs its wire type: pass value_type, for example ValueType.U8')
    if isinstance(value, str):
        return ValueType.STRING
    if isinstance(value, (bytes, bytearray)):
        return ValueType.BYTES
    if isinstance(value, ipaddress.IPv4Address):
        return ValueType.IPV4
    raise TypeError('Cannot send a {} as a Control value'.format(type(value).__name__))


def encode_value(value, value_type=None):
    """Encode one value as a type, len, data TLV.

    Without value_type the wire type is inferred from the Python type: None,
    bool, str, bytes, bytearray, ipaddress.IPv4Address and UnknownValue. An int
    has no inferred type and raises TypeError. With value_type the value must
    fit the type, or ValueError is raised.
    """
    if isinstance(value, UnknownValue):
        if value_type is not None and value_type != value.type_code:
            raise ValueError('UnknownValue has type code {}, not {}'.format(value.type_code, value_type))
        if not 0 <= value.type_code <= 0xff:
            raise ValueError('Type code must be 0..255')
        return _tlv(value.type_code, value.data)

    if value_type is None:
        value_type = _infer_type(value)
    value_type = ValueType(value_type)

    if value_type == ValueType.NULL:
        if value is not None:
            raise TypeError('ValueType.NULL only takes None')
        return _tlv(value_type, b'')

    if value_type == ValueType.BOOL:
        if not isinstance(value, int):
            raise TypeError('ValueType.BOOL takes a bool')
        if value not in (0, 1):
            raise ValueError('{} is not a bool'.format(value))
        return _tlv(value_type, bytes((int(value),)))

    if value_type in _INT_FORMATS:
        if not isinstance(value, int):
            raise TypeError('{} takes an int, not {}'.format(value_type.name, type(value).__name__))
        low, high = _INT_RANGES[value_type]
        if not low <= value <= high:
            raise ValueError('{} does not fit in {} ({}..{})'.format(value, value_type.name, low, high))
        return _tlv(value_type, struct.pack(_INT_FORMATS[value_type], value))

    if value_type == ValueType.STRING:
        if not isinstance(value, str):
            raise TypeError('ValueType.STRING takes a str')
        return _tlv(value_type, _encode_string(value))

    if value_type == ValueType.BYTES:
        if not isinstance(value, (bytes, bytearray)):
            raise TypeError('ValueType.BYTES takes bytes or bytearray')
        return _tlv(value_type, bytes(value))

    # ValueType.IPV4
    if isinstance(value, str):
        value = ipaddress.IPv4Address(value)
    if not isinstance(value, ipaddress.IPv4Address):
        raise TypeError('ValueType.IPV4 takes an ipaddress.IPv4Address')
    return _tlv(value_type, value.packed)


def _decode_tlv(buf, offset):
    """Decode the TLV at offset. Return (TypedValue, offset after it)."""
    if len(buf) - offset < 2:
        raise MalformedValueError('Value is shorter than its type and len bytes')
    type_code = buf[offset]
    length = buf[offset + 1]
    start = offset + 2
    end = start + length
    if end > len(buf):
        raise MalformedValueError('Value len {} extends past the message'.format(length))
    data = bytes(buf[start:end])

    try:
        value_type = ValueType(type_code)
    except ValueError:
        return TypedValue(type_code, UnknownValue(type_code, data)), end

    expected = _FIXED_LENGTHS.get(value_type)
    if expected is not None and length != expected:
        raise MalformedValueError('{} value has len {}, expected {}'.format(value_type.name, length, expected))

    if value_type == ValueType.NULL:
        value = None
    elif value_type == ValueType.BOOL:
        if data[0] > 1:
            raise MalformedValueError('Bool value 0x{:02x} is not 0 or 1'.format(data[0]))
        value = data[0] == 1
    elif value_type in _INT_FORMATS:
        value = struct.unpack(_INT_FORMATS[value_type], data)[0]
    elif value_type == ValueType.STRING:
        if b'\x00' in data:
            raise MalformedValueError('String value contains NUL')
        try:
            value = data.decode('utf-8')
        except UnicodeDecodeError as e:
            raise MalformedValueError('String value is not valid UTF-8: {}'.format(e)) from None
    elif value_type == ValueType.BYTES:
        value = data
    else:  # ValueType.IPV4
        value = ipaddress.IPv4Address(data)

    return TypedValue(value_type, value), end


def decode_value(buf):
    """Decode exactly one TLV. Trailing bytes are malformed."""
    typed, end = _decode_tlv(bytes(buf), 0)
    if end != len(buf):
        raise MalformedValueError('{} bytes after the value'.format(len(buf) - end))
    return typed


def encode_path(path):
    """Encode a path as path_len:u8 followed by its ASCII bytes"""
    if not isinstance(path, str):
        raise TypeError('Path must be a str')
    try:
        data = path.encode('ascii')
    except UnicodeEncodeError:
        raise ValueError('Path must be ASCII: {!r}'.format(path)) from None
    if not data:
        raise ValueError('Path cannot be empty')
    if b'\x00' in data:
        raise ValueError('Path cannot contain NUL')
    if len(data) > 0xff:
        raise ValueError('Path is longer than 255 bytes')
    return bytes((len(data),)) + data


def _decode_path(buf, offset):
    """Decode the path_len and path at offset. Return (path, offset after it)."""
    if offset >= len(buf):
        raise MalformedValueError('Message ends before the path length')
    length = buf[offset]
    start = offset + 1
    end = start + length
    if end > len(buf):
        raise MalformedValueError('Path len {} extends past the message'.format(length))
    data = bytes(buf[start:end])
    if not data:
        raise MalformedValueError('Path is empty')
    if b'\x00' in data:
        raise MalformedValueError('Path contains NUL')
    try:
        path = data.decode('ascii')
    except UnicodeDecodeError:
        raise MalformedValueError('Path is not ASCII: {!r}'.format(data)) from None
    return path, end


def _request(kind, request_id, path):
    if not 0 <= request_id <= 0xff:
        raise ValueError('Request ID must be 0..255')
    return bytes((kind, request_id)) + encode_path(path)


def build_get(request_id, path):
    """Build a GET request"""
    return _request(MessageKind.GET, request_id, path)


def build_set(request_id, path, value, value_type=None):
    """Build a SET request. See encode_value() for value and value_type."""
    return _request(MessageKind.SET, request_id, path) + encode_value(value, value_type)


def build_cmd(request_id, path, arg=NO_ARG, arg_type=None):
    """Build a CMD request, with an argument unless arg is NO_ARG"""
    message = _request(MessageKind.CMD, request_id, path)
    if arg is not NO_ARG:
        message += encode_value(arg, arg_type)
    return message


def parse_response(message):
    """Parse a Control response (OK, VALUE or ERROR).

    Other kinds are returned with only kind and request_id set, so the caller
    can decide what to do with them. Raises MalformedValueError when the bytes
    break the Control rules.
    """
    message = bytes(message)
    if len(message) < 2:
        raise MalformedValueError('Response is shorter than kind and request ID')
    kind = message[0]
    request_id = message[1]

    if kind == MessageKind.OK:
        if len(message) != 2:
            raise MalformedValueError('{} bytes after OK'.format(len(message) - 2))
        return ControlResponse(kind, request_id)

    if kind == MessageKind.VALUE:
        return ControlResponse(kind, request_id, value=decode_value(message[2:]))

    if kind == MessageKind.ERROR:
        if len(message) < 4:
            raise MalformedValueError('ERROR is shorter than its code and detail length')
        code = message[2]
        detail_len = message[3]
        if 4 + detail_len != len(message):
            raise MalformedValueError('ERROR detail_len {} does not match the {} bytes left'.format(
                detail_len, len(message) - 4))
        try:
            code = ControlErrorCode(code)
        except ValueError:
            pass
        # The detail is diagnostic text only: never fail on it
        detail = message[4:].decode('utf-8', errors='replace')
        return ControlResponse(kind, request_id, error_code=code, detail=detail)

    return ControlResponse(kind, request_id)


def decode_notify(message):
    """Decode a NOTIFY message: kind 0xc0, path_len, path, then one value.

    A NOTIFY has no request ID. Returns (path, TypedValue). Raises
    MalformedValueError when the bytes break the Control rules, trailing bytes
    included.
    """
    message = bytes(message)
    if not message or message[0] != MessageKind.NOTIFY:
        raise MalformedValueError('Not a NOTIFY message')
    path, offset = _decode_path(message, 1)
    typed, end = _decode_tlv(message, offset)
    if end != len(message):
        raise MalformedValueError('{} bytes after the NOTIFY value'.format(len(message) - end))
    return path, typed


def fragment(message):
    """Cut a message into channel 2 packet payloads, header byte included"""
    message = bytes(message)
    if not message:
        raise ValueError('Cannot send an empty message')
    if len(message) > MAX_TUNNEL_MESSAGE:
        raise ValueError('Message of {} bytes is over the {} bytes the tunnel can carry'.format(
            len(message), MAX_TUNNEL_MESSAGE))
    chunks = [message[i:i + FRAGMENT_PAYLOAD_SIZE] for i in range(0, len(message), FRAGMENT_PAYLOAD_SIZE)]
    packets = []
    for index, chunk in enumerate(chunks):
        header = index
        if index == len(chunks) - 1:
            header |= _LAST_FRAGMENT
        packets.append(bytes((header,)) + chunk)
    return packets


class Reassembler:
    """Rebuild channel 2 messages from their fragments.

    Index 0 always starts a new message and drops a partial one. Any other
    unexpected index drops the partial message, and packets are ignored until
    the next index 0.
    """

    def __init__(self):
        self._buffer = None
        self._expected = 0
        # Number of partial messages dropped, for diagnostics
        self.dropped = 0

    def reset(self):
        """Drop any partial message"""
        if self._buffer is not None:
            self.dropped += 1
        self._buffer = None
        self._expected = 0

    def feed(self, packet):
        """Feed one packet payload. Return the message when it is complete."""
        packet = bytes(packet)
        if not packet:
            return None
        header = packet[0]
        index = header & _INDEX_MASK

        if index == 0:
            self.reset()
            self._buffer = bytearray()
        elif self._buffer is None:
            return None
        elif index != self._expected:
            self.reset()
            return None

        self._buffer += packet[1:]
        self._expected = index + 1

        if header & _LAST_FRAGMENT:
            message = bytes(self._buffer)
            self._buffer = None
            self._expected = 0
            return message
        return None
