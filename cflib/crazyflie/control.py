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
Control endpoints (cf.control), carried by the Control bridge on CRTP port 10.

A Control endpoint is a device, such as a deck, that serves the
bitcraze.control request/response protocol. The Crazyflie lists its endpoints
in a catalog and tunnels Control requests to them.

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        cam = scf.cf.control.endpoint('deck:bcCam')
        quality = cam.get_typed('stream.mjpeg_quality')
        cam.set('stream.mjpeg_quality', 80, quality.type)

The calls block and raise, with a timeout on each of them. submit() is a
non-blocking primitive for code that runs in callbacks.

An endpoint can also report changes of its values. Callbacks are registered on
ControlEndpoint.notified and ControlEndpoint.notify_lost, and the Crazyflie
forwards the changes once set_notify(True) is called on the connection.
"""
import logging
import struct
import time
import zlib
from enum import IntEnum
from ipaddress import IPv4Address
from threading import Event
from threading import Lock
from threading import Semaphore
from typing import NamedTuple
from typing import Union

from .control_codec import build_cmd
from .control_codec import build_get
from .control_codec import build_set
from .control_codec import ControlError
from .control_codec import ControlErrorCode
from .control_codec import decode_notify
from .control_codec import fragment
from .control_codec import MalformedValueError
from .control_codec import MessageKind
from .control_codec import NO_ARG
from .control_codec import parse_response
from .control_codec import Reassembler
from .control_codec import TypedValue
from .control_codec import UnknownValue
from .control_codec import ValueType
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.callbacks import Caller

__author__ = 'Bitcraze AB'
__all__ = ['Control', 'ControlEndpoint', 'EndpointStatus', 'BridgeInfo', 'FirmwareErrno',
           'DEFAULT_TIMEOUT', 'NO_ARG', 'ValueType', 'TypedValue', 'UnknownValue',
           'ControlErrorCode', 'ControlError', 'UnknownEndpointError', 'EndpointNotReadyError',
           'CrazyflieControlError', 'EndpointError', 'ControlTimeoutError', 'ControlBusyError',
           'ControlDisconnectedError', 'MessageTooLargeError', 'UnexpectedResponseError',
           'MalformedValueError']

logger = logging.getLogger(__name__)

# Timeout of the blocking calls, in seconds. Change it for all calls with
# cf.control.default_timeout, or per call with timeout=.
DEFAULT_TIMEOUT = 3.0

# Interval between retries while the bridge answers EAGAIN, ENOBUFS or EBUSY
RETRY_INTERVAL = 0.01

# First CRTP protocol version with the Control bridge
MIN_PROTOCOL_VERSION = 14

CHANNEL_CATALOG = 0
CHANNEL_ENDPOINT = 1
CHANNEL_TUNNEL = 2
CHANNEL_EVENT = 3

CMD_GET_ITEM = 0x00
CMD_GET_INFO = 0x01
CMD_GET_STATUS = 0x00
CMD_SET_NOTIFY = 0x01
CMD_RESET = 0x02

EVENT_NOTIFY_LOST = 0x01

_ENDPOINT_READY = 1

ValueTypes = Union[None, bool, int, str, bytes, IPv4Address, UnknownValue]


class FirmwareErrno(IntEnum):
    """Status numbers of the Control bridge.

    These are the firmware's newlib numbers, part of the wire protocol. They
    can differ from the host's errno module.
    """
    ENOENT = 2
    EIO = 5
    EAGAIN = 11
    EBUSY = 16
    EINVAL = 22
    EPROTO = 71
    EBADMSG = 77
    ENOSYS = 88
    ECONNRESET = 104
    ENOBUFS = 105
    ETIMEDOUT = 116
    EMSGSIZE = 122
    ENOTCONN = 128


# Statuses that say the request was never applied by the endpoint
_NOT_APPLIED = frozenset((
    FirmwareErrno.ENOENT, FirmwareErrno.EIO, FirmwareErrno.EAGAIN, FirmwareErrno.EBUSY,
    FirmwareErrno.EINVAL, FirmwareErrno.EBADMSG, FirmwareErrno.ENOBUFS, FirmwareErrno.ENOTCONN,
))

_BUSY = frozenset((FirmwareErrno.ENOBUFS, FirmwareErrno.EBUSY))


def _errno_name(number):
    try:
        return FirmwareErrno(number).name
    except ValueError:
        return 'errno {}'.format(number)


class UnknownEndpointError(ControlError):
    """The path or ID is not in the catalog"""


class EndpointNotReadyError(ControlError):
    """The endpoint is not ready (ENOTCONN)"""


class CrazyflieControlError(ControlError):
    """The bridge failed the request with a status (errno).

    outcome_known is True when the status says the request never reached the
    endpoint, so it was not applied.
    """

    def __init__(self, errno, outcome_known, message=None):
        self.errno = errno
        self.outcome_known = outcome_known
        if message is None:
            message = 'Crazyflie answered {} ({})'.format(_errno_name(errno), errno)
        super().__init__(message)


class EndpointError(ControlError):
    """The endpoint answered with a Control ERROR.

    code is a ControlErrorCode, or a plain int for an unknown code.
    """

    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        name = code.name if isinstance(code, ControlErrorCode) else 'error 0x{:02x}'.format(code)
        super().__init__('{}: {}'.format(name, detail) if detail else name)


class ControlTimeoutError(ControlError, TimeoutError):
    """No answer within the timeout. A request was sent: its outcome is unknown."""


class ControlBusyError(ControlError):
    """Still busy at the timeout. The request was never applied and is safe to resend."""


class ControlDisconnectedError(ControlError):
    """The Crazyflie is not connected, or the connection ended during the call"""


class MessageTooLargeError(ControlError):
    """The request is larger than the bridge or the endpoint accepts. Nothing was sent."""


class UnexpectedResponseError(ControlError):
    """The answer is not the one the call expects, for example OK when VALUE was expected"""


class EndpointStatus(NamedTuple):
    """Status of an endpoint, from GET_STATUS"""
    ready: bool
    max_request: int
    max_response: int


class BridgeInfo(NamedTuple):
    """Catalog and limits of the Control bridge, from GET_INFO"""
    count: int
    catalog_crc: int
    max_in_flight: int
    max_message: int


class _Pending:
    """A tunnel request waiting for its terminal message"""

    def __init__(self, endpoint, callback=None):
        self.endpoint = endpoint
        self.callback = callback
        self.event = Event()
        self.status = None
        self.body = None
        self.disconnected = False


class _Command:
    """A channel 0 or 1 command waiting for its answer"""

    def __init__(self, channel, cmd, match):
        self.channel = channel
        self.cmd = cmd
        self.match = match
        self.event = Event()
        self.data = None
        self.disconnected = False


class _Session:
    """State of cf.control for one connection"""

    def __init__(self):
        self.closed = False
        self.closed_event = Event()
        self.init_lock = Lock()
        self.info = None
        self.catalog = None
        self.in_flight = None
        self.reset_done = False
        self.reassembler = Reassembler()
        self.command = None
        self.pending = {}
        self.abandoned = set()
        self.next_id = {}
        self.limits = {}


def _remaining(deadline):
    return deadline - time.monotonic()


class ControlEndpoint:
    """One endpoint of the catalog, valid for the connection it was read on"""

    def __init__(self, control, session, endpoint_id, path):
        self._control = control
        self._session = session
        self.id = endpoint_id
        self.path = path

    def __repr__(self):
        return 'ControlEndpoint(id={}, path={!r})'.format(self.id, self.path)

    @property
    def notified(self):
        """Caller of the change notifications of this endpoint.

        callback(path, value) runs on the incoming-packet thread, with value
        the plain Python value as get() returns it. The Caller is shared by
        every ControlEndpoint with this path, so its callbacks survive a
        reconnect. Adding a callback does not enable forwarding: see
        set_notify().
        """
        return self._control._notified_caller(self.path)

    @property
    def notify_lost(self):
        """Caller of the lost notification reports of this endpoint.

        callback(dropped) runs on the incoming-packet thread: at least dropped
        notifications were lost since the last report, so the values mirrored
        from notifications should be read again (from another thread).
        Shared like notified.
        """
        return self._control._notify_lost_caller(self.path)

    def set_notify(self, enabled, timeout=None):
        """Enable or disable the forwarding of this endpoint's notifications.

        Forwarding is off on every new connection: call this again after a
        reconnect. Raises CrazyflieControlError with errno ENOSYS when the
        Crazyflie has no notification support.
        """
        self._control._set_notify(self, enabled, timeout)

    def is_ready(self, timeout=None):
        """True when the endpoint can take requests (GET_STATUS)"""
        return self.status(timeout).ready

    def status(self, timeout=None):
        """Readiness and the endpoint's own size limits (GET_STATUS)"""
        return self._control._endpoint_status(self, timeout)

    def get(self, path, timeout=None):
        """Read a path. Returns the plain Python value."""
        return self.get_typed(path, timeout).value

    def get_typed(self, path, timeout=None):
        """Read a path. Returns a TypedValue, which also holds the wire type."""
        response = self._call(build_get(0, path), timeout)
        if response.kind != MessageKind.VALUE:
            raise UnexpectedResponseError('GET {} answered kind 0x{:02x}, expected VALUE'.format(path, response.kind))
        return response.value

    def set(self, path, value, value_type=None, timeout=None):
        """Write a path.

        The wire type is inferred from the value, except for int, which needs
        value_type (TypeError otherwise). See the Values section of the docs.
        """
        response = self._call(build_set(0, path, value, value_type), timeout)
        if response.kind != MessageKind.OK:
            raise UnexpectedResponseError('SET {} answered kind 0x{:02x}, expected OK'.format(path, response.kind))

    def cmd(self, path, arg=NO_ARG, arg_type=None, timeout=None):
        """Run a command, with an optional argument. Returns its value, or None for OK."""
        response = self._call(build_cmd(0, path, arg, arg_type), timeout)
        if response.kind == MessageKind.OK:
            return None
        if response.kind == MessageKind.VALUE:
            return response.value.value
        raise UnexpectedResponseError('CMD {} answered kind 0x{:02x}, expected OK or VALUE'.format(path, response.kind))

    def request_raw(self, message, timeout=None):
        """Send any Control request. The library sets byte 1. Returns the whole response."""
        return self._control._transact(self, message, timeout)

    def submit(self, message, callback):
        """Send a Control request without blocking.

        callback(error, response) runs once, on the incoming-packet thread
        (or on the thread that reports a disconnect), with error a ControlError
        or None and response the whole response bytes or None. There is no
        timeout and no retry: a busy bridge gives ControlBusyError at once.

        Errors found before anything is sent are raised by submit() itself,
        and the callback is then never called.
        """
        self._control._submit(self, message, callback)

    def _call(self, message, timeout):
        response = parse_response(self.request_raw(message, timeout))
        if response.kind == MessageKind.ERROR:
            raise EndpointError(response.error_code, response.detail)
        return response


class Control:
    """Access to the Control endpoints of a Crazyflie (cf.control)"""

    def __init__(self, crazyflie):
        self._cf = crazyflie
        self.default_timeout = DEFAULT_TIMEOUT

        # Protects the session pointer and the pending tables
        self._lock = Lock()
        # One channel 0 or 1 command at a time
        self._command_lock = Lock()
        # Keeps the fragments of one tunnel message together
        self._tunnel_lock = Lock()
        self._session = None
        # Notification callers by endpoint path, kept across connections
        self._notified = {}
        self._notify_lost = {}

        self._cf.add_port_callback(CRTPPort.CONTROL, self._incoming)
        self._cf.disconnected.add_callback(self._disconnected)
        self._cf.connection_lost.add_callback(self._disconnected)

    def endpoints(self, timeout=None):
        """The catalog for this connection.

        The first call on a connection sends RESET, GET_INFO and GET_ITEM. The
        catalog is empty when the Crazyflie has no Control bridge.
        """
        session = self._ensure_catalog(timeout)
        return list(session.catalog) if session is not None else []

    def endpoint(self, path, timeout=None):
        """The endpoint with this path. Raises UnknownEndpointError."""
        for endpoint in self.endpoints(timeout):
            if endpoint.path == path:
                return endpoint
        raise UnknownEndpointError('No Control endpoint {!r}'.format(path))

    def info(self, timeout=None):
        """Catalog size and bridge limits, or None without a Control bridge"""
        session = self._ensure_catalog(timeout)
        return session.info if session is not None else None

    # Blocking machinery

    def _check_thread(self):
        if self._cf.is_called_by_incoming_handler_thread():
            raise RuntimeError('Blocking cf.control calls would deadlock on the incoming-packet thread. '
                               'Use ControlEndpoint.submit() there.')

    def _deadline(self, timeout):
        if timeout is None:
            timeout = self.default_timeout
        return time.monotonic() + timeout

    def _open_session(self):
        with self._lock:
            if self._cf.link is None:
                raise ControlDisconnectedError('The Crazyflie is not connected')
            if self._session is None:
                self._session = _Session()
            return self._session

    @staticmethod
    def _check_open(session):
        if session.closed:
            raise ControlDisconnectedError('The connection this endpoint was read on has ended')

    def _ensure_catalog(self, timeout):
        """Return the session with its catalog, or None without a bridge"""
        self._check_thread()
        deadline = self._deadline(timeout)
        session = self._open_session()

        if not session.init_lock.acquire(timeout=max(0.0, _remaining(deadline))):
            raise ControlTimeoutError('Timed out waiting for the Control catalog')
        try:
            self._check_open(session)
            if session.catalog is not None:
                return session
            if self._cf.platform.get_protocol_version() < MIN_PROTOCOL_VERSION:
                return None
            self._read_catalog(session, deadline)
            return session
        finally:
            session.init_lock.release()

    def _read_catalog(self, session, deadline):
        self._command(session, CHANNEL_ENDPOINT, bytes((CMD_RESET,)), None, deadline)

        data = self._command(session, CHANNEL_CATALOG, bytes((CMD_GET_INFO,)), None, deadline)
        if len(data) < 10:
            raise UnexpectedResponseError('GET_INFO answer is {} bytes, expected 10'.format(len(data)))
        count = data[2]
        crc, max_in_flight, max_message = struct.unpack_from('<IBH', data, 3)
        info = BridgeInfo(count, crc, max_in_flight, max_message)

        catalog = []
        crc_data = bytearray()
        for endpoint_id in range(count):
            data = self._command(session, CHANNEL_CATALOG, bytes((CMD_GET_ITEM, endpoint_id)),
                                 self._id_matcher(endpoint_id), deadline)
            if len(data) < 3:
                raise UnexpectedResponseError('GET_ITEM answer is {} bytes'.format(len(data)))
            raw_path = bytes(data[3:])
            try:
                path = raw_path.decode('ascii')
            except UnicodeDecodeError:
                raise UnexpectedResponseError('Endpoint {} path is not ASCII'.format(endpoint_id)) from None
            catalog.append(ControlEndpoint(self, session, endpoint_id, path))
            crc_data += bytes((endpoint_id,)) + raw_path

        if zlib.crc32(crc_data) != crc:
            raise UnexpectedResponseError('Control catalog CRC mismatch: got 0x{:08x}, expected 0x{:08x}'.format(
                zlib.crc32(crc_data), crc))

        session.info = info
        session.in_flight = Semaphore(max_in_flight)
        session.catalog = catalog
        logger.info('Control catalog: %s', ', '.join(e.path for e in catalog) or 'empty')

    @staticmethod
    def _id_matcher(endpoint_id):
        # An error answer has no ID. A success answer echoes the ID in byte 2.
        return lambda data: len(data) < 3 or data[2] == endpoint_id

    def _command(self, session, channel, payload, match, deadline):
        """Send a channel 0 or 1 command and return its successful answer.

        EAGAIN is retried until the deadline.
        """
        cmd = payload[0]
        while True:
            if not self._command_lock.acquire(timeout=max(0.0, _remaining(deadline))):
                raise ControlTimeoutError('Timed out waiting to send a Control command')
            try:
                waiter = _Command(channel, cmd, match)
                with self._lock:
                    self._check_open(session)
                    session.command = waiter
                pk = CRTPPacket()
                pk.set_header(CRTPPort.CONTROL, channel)
                pk.data = payload
                self._cf.send_packet(pk, expected_reply=(cmd,))
                answered = waiter.event.wait(max(0.0, _remaining(deadline)))
                with self._lock:
                    if session.command is waiter:
                        session.command = None
            finally:
                self._command_lock.release()

            if waiter.disconnected:
                raise ControlDisconnectedError('Disconnected during a Control command')
            if not answered and waiter.data is None:
                raise ControlTimeoutError('No answer to Control command {}/0x{:02x}'.format(channel, cmd))

            status = waiter.data[1]
            if status == 0:
                return waiter.data
            if status == FirmwareErrno.EAGAIN and _remaining(deadline) > RETRY_INTERVAL:
                if session.closed_event.wait(RETRY_INTERVAL):
                    raise ControlDisconnectedError('Disconnected during a Control command')
                continue
            if status == FirmwareErrno.ENOENT:
                raise UnknownEndpointError('The Crazyflie does not know this endpoint ID')
            raise CrazyflieControlError(status, True)

    def _endpoint_status(self, endpoint, timeout):
        self._check_thread()
        deadline = self._deadline(timeout)
        session = endpoint._session
        self._check_open(session)
        data = self._command(session, CHANNEL_ENDPOINT, bytes((CMD_GET_STATUS, endpoint.id)),
                             self._id_matcher(endpoint.id), deadline)
        if len(data) < 8:
            raise UnexpectedResponseError('GET_STATUS answer is {} bytes, expected 8'.format(len(data)))
        max_request, max_response = struct.unpack_from('<HH', data, 4)
        status = EndpointStatus(data[3] == _ENDPOINT_READY, max_request, max_response)
        with self._lock:
            session.limits[endpoint.id] = status
        return status

    def _set_notify(self, endpoint, enabled, timeout):
        self._check_thread()
        deadline = self._deadline(timeout)
        session = endpoint._session
        self._check_open(session)
        flag = 1 if enabled else 0

        def match(data):
            # An error answer has no ID. A success answer echoes ID and flag.
            return len(data) < 3 or (data[2] == endpoint.id and (len(data) < 4 or data[3] == flag))

        try:
            data = self._command(session, CHANNEL_ENDPOINT, bytes((CMD_SET_NOTIFY, endpoint.id, flag)),
                                 match, deadline)
        except CrazyflieControlError as e:
            if e.errno == FirmwareErrno.ENOSYS:
                raise CrazyflieControlError(e.errno, True, 'The Crazyflie has no Control notification '
                                            'support (ENOSYS)') from None
            raise
        if len(data) < 4:
            raise UnexpectedResponseError('SET_NOTIFY answer is {} bytes, expected 4'.format(len(data)))

    def _check_request(self, session, endpoint, message):
        if len(message) < 2:
            raise ValueError('A Control request holds at least a kind and a request ID')
        if message[0] & 0x80:
            raise ValueError('Request kind 0x{:02x} has bit 7 set'.format(message[0]))
        if len(message) > session.info.max_message:
            raise MessageTooLargeError('Request is {} bytes, the bridge carries at most {}'.format(
                len(message), session.info.max_message))
        limits = session.limits.get(endpoint.id)
        if limits is not None and len(message) > limits.max_request:
            raise MessageTooLargeError('Request is {} bytes, {} takes at most {}'.format(
                len(message), endpoint.path, limits.max_request))

    def _allocate_id(self, session, endpoint_id):
        start = session.next_id.get(endpoint_id, 0)
        for offset in range(256):
            request_id = (start + offset) & 0xff
            key = (endpoint_id, request_id)
            if key not in session.pending and key not in session.abandoned:
                session.next_id[endpoint_id] = (request_id + 1) & 0xff
                return request_id
        raise ControlBusyError('No free request ID for endpoint {}'.format(endpoint_id))

    def _send_request(self, session, endpoint, message, callback=None):
        """Register a pending request and send it. Returns (key, pending)."""
        pending = _Pending(endpoint, callback)
        with self._lock:
            self._check_open(session)
            request_id = self._allocate_id(session, endpoint.id)
            key = (endpoint.id, request_id)
            session.pending[key] = pending

        tunnel_message = bytes((endpoint.id, message[0], request_id)) + message[2:]
        try:
            with self._tunnel_lock:
                for payload in fragment(tunnel_message):
                    pk = CRTPPacket()
                    pk.set_header(CRTPPort.CONTROL, CHANNEL_TUNNEL)
                    pk.data = payload
                    # Never resent: a repeated fragment breaks reassembly
                    self._cf.send_packet(pk)
        except Exception:
            with self._lock:
                if session.pending.get(key) is pending:
                    del session.pending[key]
            raise
        return key, pending

    def _transact(self, endpoint, message, timeout):
        """Blocking tunnel request. Returns the response bytes."""
        self._check_thread()
        deadline = self._deadline(timeout)
        session = endpoint._session
        self._check_open(session)
        message = bytes(message)
        self._check_request(session, endpoint, message)

        if not session.in_flight.acquire(timeout=max(0.0, _remaining(deadline))):
            raise ControlBusyError('{} requests already in flight'.format(session.info.max_in_flight))
        try:
            while True:
                key, pending = self._send_request(session, endpoint, message)
                answered = pending.event.wait(max(0.0, _remaining(deadline)))
                if not answered:
                    with self._lock:
                        if session.pending.get(key) is pending:
                            del session.pending[key]
                            session.abandoned.add(key)
                            raise ControlTimeoutError('No answer from {} within the timeout, outcome unknown'.format(
                                endpoint.path))

                if pending.disconnected:
                    raise ControlDisconnectedError('Disconnected while waiting for {}'.format(endpoint.path))
                if pending.status in _BUSY:
                    if _remaining(deadline) <= RETRY_INTERVAL:
                        raise ControlBusyError('{} still busy ({}) at the timeout'.format(
                            endpoint.path, _errno_name(pending.status)))
                    if session.closed_event.wait(RETRY_INTERVAL):
                        raise ControlDisconnectedError('Disconnected while waiting for {}'.format(endpoint.path))
                    continue
                if pending.status != 0:
                    raise self._tunnel_error(endpoint, pending.status)
                return pending.body
        finally:
            session.in_flight.release()

    def _submit(self, endpoint, message, callback):
        session = endpoint._session
        self._check_open(session)
        message = bytes(message)
        self._check_request(session, endpoint, message)
        if not session.in_flight.acquire(blocking=False):
            raise ControlBusyError('{} requests already in flight'.format(session.info.max_in_flight))
        try:
            self._send_request(session, endpoint, message, callback)
        except Exception:
            session.in_flight.release()
            raise

    @staticmethod
    def _tunnel_error(endpoint, status):
        if status == FirmwareErrno.ENOTCONN:
            return EndpointNotReadyError('{} is not ready'.format(endpoint.path))
        if status == FirmwareErrno.ENOENT:
            return UnknownEndpointError('The Crazyflie does not know endpoint {}'.format(endpoint.id))
        if status in _BUSY:
            return ControlBusyError('{} is busy ({})'.format(endpoint.path, _errno_name(status)))
        return CrazyflieControlError(status, status in _NOT_APPLIED)

    def _finish(self, session, pending):
        """Wake the blocking caller, or run the submit() callback"""
        if pending.callback is None:
            pending.event.set()
            return
        session.in_flight.release()
        if pending.disconnected:
            error, response = ControlDisconnectedError('Disconnected before the answer'), None
        elif pending.status != 0:
            error, response = self._tunnel_error(pending.endpoint, pending.status), None
        else:
            error, response = None, pending.body
        try:
            pending.callback(error, response)
        except Exception:
            logger.exception('Exception in a cf.control submit() callback')

    # Notifications

    def _notified_caller(self, path):
        with self._lock:
            return self._notified.setdefault(path, Caller())

    def _notify_lost_caller(self, path):
        with self._lock:
            return self._notify_lost.setdefault(path, Caller())

    @staticmethod
    def _endpoint_path(session, endpoint_id):
        catalog = session.catalog
        if catalog is None or endpoint_id >= len(catalog):
            return None
        return catalog[endpoint_id].path

    @staticmethod
    def _call_each(caller, *args):
        # One failing callback must not stop the others, nor the dispatcher
        for callback in list(caller.callbacks):
            try:
                callback(*args)
            except Exception:
                logger.exception('Exception in a cf.control notification callback')

    def _notification(self, session, endpoint_id, body):
        endpoint_path = self._endpoint_path(session, endpoint_id)
        if endpoint_path is None:
            logger.debug('Control: notification for unknown endpoint %d dropped', endpoint_id)
            return
        if body[0] != MessageKind.NOTIFY:
            logger.debug('Control: notification kind 0x%02x from %s ignored', body[0], endpoint_path)
            return
        try:
            path, typed = decode_notify(body)
        except MalformedValueError as e:
            logger.warning('Control: malformed NOTIFY from %s skipped: %s (%s)', endpoint_path, e, body.hex())
            return
        with self._lock:
            caller = self._notified.get(endpoint_path)
        if caller is not None:
            self._call_each(caller, path, typed.value)

    def _event(self, session, data):
        if not session.reset_done:
            logger.debug('Control: event before RESET dropped')
            return
        if not data:
            return
        if data[0] != EVENT_NOTIFY_LOST:
            logger.debug('Control: unknown event 0x%02x ignored', data[0])
            return
        # Trailing bytes are for later versions
        if len(data) < 3:
            logger.debug('Control: short NOTIFY_LOST dropped: %s', data.hex())
            return
        endpoint_id, dropped = data[1], data[2]
        endpoint_path = self._endpoint_path(session, endpoint_id)
        if endpoint_path is None:
            logger.debug('Control: NOTIFY_LOST for unknown endpoint %d dropped', endpoint_id)
            return
        with self._lock:
            caller = self._notify_lost.get(endpoint_path)
        if caller is not None:
            self._call_each(caller, dropped)

    # Incoming packets and connection events

    def _incoming(self, pk):
        with self._lock:
            session = self._session
        if session is None:
            return
        data = bytes(pk.data)
        if pk.channel in (CHANNEL_CATALOG, CHANNEL_ENDPOINT):
            self._command_answer(session, pk.channel, data)
        elif pk.channel == CHANNEL_TUNNEL:
            if not session.reset_done:
                logger.debug('Control: tunnel packet before RESET dropped')
                return
            message = session.reassembler.feed(data)
            if message is not None:
                self._dispatch(session, message)
        elif pk.channel == CHANNEL_EVENT:
            self._event(session, data)

    def _command_answer(self, session, channel, data):
        if len(data) < 2:
            return
        with self._lock:
            waiter = session.command
            if waiter is None or waiter.channel != channel or waiter.cmd != data[0]:
                logger.debug('Control: unexpected answer on channel %d: %s', channel, data.hex())
                return
            if data[1] == 0 and waiter.match is not None and not waiter.match(data):
                logger.debug('Control: stale answer on channel %d: %s', channel, data.hex())
                return
            session.command = None
            waiter.data = data
            if channel == CHANNEL_ENDPOINT and data[0] == CMD_RESET and data[1] == 0:
                # Every tunnel message after this belongs to this client
                session.reset_done = True
                session.reassembler.reset()
        waiter.event.set()

    def _dispatch(self, session, message):
        if len(message) < 3:
            logger.debug('Control: short tunnel message dropped: %s', message.hex())
            return
        endpoint_id, status, body = message[0], message[1], message[2:]
        if status == 0 and body[0] >= MessageKind.NOTIFY:
            self._notification(session, endpoint_id, body)
            return
        if len(body) < 2:
            logger.debug('Control: short tunnel message dropped: %s', message.hex())
            return
        key = (endpoint_id, body[1])
        with self._lock:
            pending = session.pending.pop(key, None)
            if pending is None:
                if key in session.abandoned:
                    session.abandoned.discard(key)
                    logger.debug('Control: late answer for endpoint %d, request %d', *key)
                else:
                    logger.debug('Control: unmatched tunnel message: %s', message.hex())
                return
            pending.status = status
            pending.body = body
        self._finish(session, pending)

    def _disconnected(self, *args):
        with self._lock:
            session = self._session
            self._session = None
            if session is None:
                return
            session.closed = True
            waiter = session.command
            session.command = None
            pendings = list(session.pending.values())
            session.pending.clear()
        session.closed_event.set()
        if waiter is not None:
            waiter.disconnected = True
            waiter.event.set()
        for pending in pendings:
            pending.disconnected = True
            self._finish(session, pending)
