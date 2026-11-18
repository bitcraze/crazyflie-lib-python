#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2026 Bitcraze AB
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
Crazyflie console is used to receive characters printed using printf
from the firmware.

The Crazyflie can have several consoles. Each one has a path, such as
`cf:stm32` for the Crazyflie's own STM32 or `deck:bcCam` for the Camera Deck.
`Console.list()` returns the paths of the connected Crazyflie and
`Console.open()` starts receiving one of them:

```python
print(cf.console.list())   # ['cf:stm32', 'deck:bcCam']

with cf.console.open('deck:bcCam', line_cb=print):
    time.sleep(10)
```

Consoles other than `cf:stm32` are only sent while they are open. When
connecting, the library asks the Crazyflie to stop sending them, in case an
earlier connection left them open.
"""
import codecs
import collections
import logging
import queue
import threading
import time
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeoutError

from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.callbacks import Caller

__author__ = 'Bitcraze AB'
__all__ = ['Console', 'ConsoleHandle', 'ConsoleError']

logger = logging.getLogger(__name__)

SOURCED_CONSOLE_PROTOCOL_VERSION = 13

LOCAL_CHANNEL = 0
SOURCED_CHANNEL = 1
CONTROL_CHANNEL = 2
CATALOG_CHANNEL = 3

CONTROL_SET_ENABLED = 0
CATALOG_GET_ITEM = 0
CATALOG_GET_INFO = 1
ALL_SOURCES = 0xff

STM32_PATH = 'cf:stm32'

# Firmware errno values are part of the wire protocol and can differ from the
# host's errno module (macOS EAGAIN is 35, for example).
_FIRMWARE_EAGAIN = 11
_FIRMWARE_ENOENT = 2

# Time to wait for one response from the Crazyflie
RESPONSE_TIMEOUT = 2.0
# The firmware answers EAGAIN until its startup is complete
NOT_READY_RETRY_DELAY = 0.01
NOT_READY_TIMEOUT = 10.0
# Default time a blocking call waits for its result
DEFAULT_TIMEOUT = 5.0

# Output received before the console list is known, from consoles an earlier
# connection left open
EARLY_OUTPUT_LIMIT = 64 * 1024
# Characters of history kept per console
HISTORY_LIMIT = 256 * 1024


class ConsoleError(Exception):
    """
    Error from a console operation.

    `errno` holds the firmware's error number when the Crazyflie rejected the
    request, and is None otherwise.
    """

    def __init__(self, message, errno=None):
        super().__init__(message)
        self.errno = errno


def _new_decoder():
    """
    Return an incremental UTF-8 decoder. It keeps a character split across
    packets until its last byte arrives, and replaces invalid bytes instead of
    raising.
    """
    return codecs.getincrementaldecoder('utf-8')(errors='replace')


class _ConsoleState:
    """
    Output of one console since connection: the decoder, the history and the
    open handles. Bytes are only pushed from one thread at a time.
    """

    def __init__(self, path):
        self.path = path
        self._decoder = _new_decoder()
        self._history = collections.deque()
        self._history_size = 0
        self._handles = []
        self._lock = threading.Lock()

    def push_bytes(self, data):
        """Decode and store data, then pass it to the open handles. Returns the text."""
        with self._lock:
            text = self._decoder.decode(bytes(data))
            if not text:
                return text
            self._history.append(text)
            self._history_size += len(text)
            while self._history_size > HISTORY_LIMIT:
                self._history_size -= len(self._history.popleft())
            handles = list(self._handles)

        # User callbacks run without the lock, so they cannot block the
        # incoming packet thread on it
        for handle in handles:
            handle._deliver(text)
        return text

    def attach(self, handle, replay_history):
        with self._lock:
            history = ''.join(self._history) if replay_history else ''
            handle._start_replay()
            self._handles.append(handle)
        handle._finish_replay(history)

    def detach(self, handle):
        with self._lock:
            if handle in self._handles:
                self._handles.remove(handle)

    def detach_all(self):
        with self._lock:
            handles = self._handles
            self._handles = []
        return handles


class _Session:
    """
    State of one connection. A new session replaces it on every connection so
    that nothing from an earlier connection is mixed into the new one.
    """

    def __init__(self, protocol_version):
        self.protocol_version = protocol_version
        self.stm32 = _ConsoleState(STM32_PATH)
        self.closed = False

        # Guards the fields below, used by both the incoming packet thread
        # and the request worker
        self.lock = threading.Lock()
        self.catalog = None       # list of paths, index is the source ID
        self.sources = {}         # source ID -> _ConsoleState
        self.early_output = []    # (source ID, bytes) before the catalog is known
        self.early_output_size = 0

        # Only used by the request worker
        self.open_counts = collections.Counter()

    @property
    def supports_sources(self):
        return self.protocol_version >= SOURCED_CONSOLE_PROTOCOL_VERSION

    def route_sourced(self, source_id, data):
        """Return the console state for source_id, or hold data until the catalog is known."""
        with self.lock:
            if self.catalog is None:
                self.early_output.append((source_id, bytes(data)))
                self.early_output_size += len(data)
                while self.early_output_size > EARLY_OUTPUT_LIMIT:
                    _, dropped = self.early_output.pop(0)
                    self.early_output_size -= len(dropped)
                return None
            return self.sources.get(source_id)

    def set_catalog(self, paths):
        with self.lock:
            self.sources = {source_id: _ConsoleState(path) for source_id, path in enumerate(paths)}
            # Held output enters the history before any packet received after
            # this point, as the incoming thread waits for the lock
            for source_id, data in self.early_output:
                state = self.sources.get(source_id)
                if state is not None:
                    state.push_bytes(data)
            self.early_output = []
            self.early_output_size = 0
            self.catalog = list(paths)

    def all_states(self):
        with self.lock:
            return [self.stm32] + list(self.sources.values())


class ConsoleHandle:
    """
    An open console, returned by `Console.open()`.

    Output is passed to the callbacks given to `Console.open()` until the
    handle is closed or the Crazyflie disconnects. Close it with `close()` or
    use it in a `with` statement.
    """

    def __init__(self, console, session, state, text_cb, line_cb):
        self._console = console
        self._session = session
        self._state = state
        self._text_cb = text_cb
        self._line_cb = line_cb
        self._line = ''
        self._lock = threading.Lock()
        self._replaying = False
        self._pending = []
        self._closed = False

    @property
    def path(self):
        """The path of this console, for example `deck:bcCam`."""
        return self._state.path

    @property
    def closed(self):
        """True after `close()` or when the Crazyflie has disconnected."""
        return self._closed

    def close(self, timeout=DEFAULT_TIMEOUT):
        """
        Stop receiving this console.

        When this is the last open handle of a console other than `cf:stm32`,
        the Crazyflie is asked to stop sending it and this waits for its
        answer. Closing does not lose output: the console keeps buffering on
        its side and a later `Console.open()` replays the history.

        Raises ConsoleError if the Crazyflie rejects the request or does not
        answer within timeout seconds.
        """
        if self._closed:
            return
        self._closed = True
        self._state.detach(self)
        self._console._release(self._session, self.path, timeout)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _start_replay(self):
        with self._lock:
            self._replaying = True

    def _finish_replay(self, history):
        """
        Pass the history to the callbacks, then any output that arrived while
        doing so, until the incoming packet thread can deliver directly.
        """
        chunk = history
        while True:
            if chunk:
                self._emit(chunk)
            with self._lock:
                if not self._pending:
                    self._replaying = False
                    return
                chunk = ''.join(self._pending)
                self._pending = []

    def _deliver(self, text):
        with self._lock:
            if self._replaying:
                self._pending.append(text)
                return
        self._emit(text)

    def _emit(self, text):
        if self._closed:
            return
        if self._text_cb is not None:
            self._text_cb(text)
        if self._line_cb is not None:
            self._line += text
            *lines, self._line = self._line.split('\n')
            for line in lines:
                # Lines can end with '\r\n' or '\n\r', which leaves the '\r'
                # at the start of the next line
                self._line_cb(line.strip('\r'))

    def _disconnected(self):
        self._closed = True


class Console:
    """
    Crazyflie console is used to receive characters printed using printf
    from the firmware.
    """

    def __init__(self, crazyflie):
        """
        Initialize the console and register it to receive data from the copter.
        """

        self.receivedChar = Caller()
        """
        This member variable is used to setup a callback that will be called
        when text is received from the Crazyflie's own console (CRTP port 0,
        channel 0). This works with every firmware version.

        The text arrives in chunks of up to 30 bytes. A chunk can end in the
        middle of a line, so do not add a newline after each one.

        Example:
        ```python
        [...]

        def log_console(self, text):
            self.log_file.write(text)

        [...]

        self.cf.console.receivedChar.add_callback(self.log_console)
        ```
        """

        self.cf = crazyflie
        self._session = _Session(protocol_version=-1)
        self._session.closed = True
        self._responses = queue.Queue()
        self._requests = queue.Queue()
        self._worker = None
        self._worker_lock = threading.Lock()

        self.cf.add_header_callback(self._incoming, CRTPPort.CONSOLE, LOCAL_CHANNEL)
        self.cf.add_header_callback(self._incoming_sourced, CRTPPort.CONSOLE, SOURCED_CHANNEL)
        self.cf.add_header_callback(self._incoming_response, CRTPPort.CONSOLE, CONTROL_CHANNEL)
        self.cf.add_header_callback(self._incoming_response, CRTPPort.CONSOLE, CATALOG_CHANNEL)
        self.cf.disconnected.add_callback(self._disconnected)

    def list(self, timeout=DEFAULT_TIMEOUT):
        """
        Return the paths of the consoles of the connected Crazyflie, for
        example `['cf:stm32', 'deck:bcCam']`.

        `cf:stm32` is always first. Other consoles require CRTP protocol
        version 13; with older firmware only `cf:stm32` is returned. The list
        is read from the Crazyflie once per connection.

        This blocks, so do not call it from a cflib callback. Raises
        ConsoleError if the list cannot be read within timeout seconds.
        """
        session = self._connected_session()
        return [STM32_PATH] + self._run(session, lambda: self._ensure_catalog(session), timeout)

    def open(self, path, text_cb=None, line_cb=None, history=True, timeout=DEFAULT_TIMEOUT):
        """
        Start receiving the console with this path and return its
        ConsoleHandle.

        text_cb is called with text as it arrives, in chunks that can end in
        the middle of a line. line_cb is called with each complete line,
        without its line ending. Both are called from a cflib thread.

        With history=True, the output received since connection is passed to
        the callbacks before this returns, followed by new output. This shows
        startup messages. With history=False, only new output is passed.

        This blocks, so do not call it from a cflib callback. Raises
        ConsoleError if the Crazyflie has no console with this path, rejects
        the request, or does not answer within timeout seconds.
        """
        session = self._connected_session()
        if path == STM32_PATH:
            state = session.stm32
        else:
            # If the caller stops waiting and the console opens later, close it
            # again so that it does not stay open without a handle
            def release_late(_state):
                self._submit(session, lambda: self._release_on_worker(session, path))

            state = self._run(session, lambda: self._acquire(session, path), timeout, release_late)

        handle = ConsoleHandle(self, session, state, text_cb, line_cb)
        state.attach(handle, history)
        return handle

    def _connected(self, protocol_version):
        """
        Called by the Crazyflie when the protocol version is known. The
        session keeps the output received before this point.
        """
        session = self._session
        session.protocol_version = protocol_version
        session.closed = False
        if session.supports_sources:
            # Stop consoles that an earlier connection left open. The request
            # worker runs requests in order, so this goes before any open().
            self._submit(session, lambda: self._disable_all(session))

    def _disconnected(self, link_uri):
        session = self._session
        session.closed = True
        # Wake the request worker if it waits for a response
        self._responses.put(None)
        for state in session.all_states():
            for handle in state.detach_all():
                handle._disconnected()
        # Do not complete a character with bytes from another connection
        self._session = _Session(protocol_version=-1)
        self._session.closed = True

    def _connected_session(self):
        if self.cf.is_called_by_incoming_handler_thread():
            raise RuntimeError('Console calls block and cannot be made from a cflib callback')
        return self._session

    def _incoming(self, packet):
        """
        Callback for data received from the copter.
        """
        console_text = self._session.stm32.push_bytes(packet.data)
        if console_text:
            self.receivedChar.call(console_text)

    def _incoming_sourced(self, packet):
        if len(packet.data) < 1:
            return
        session = self._session
        state = session.route_sourced(packet.data[0], packet.data[1:])
        if state is not None:
            state.push_bytes(packet.data[1:])

    def _incoming_response(self, packet):
        self._responses.put((packet.channel, bytes(packet.data)))

    # Requests to the Crazyflie run on a worker thread, which sends one request
    # at a time and waits for its response. _run() and _submit() hand requests
    # to it; the methods after _work() run on it.

    def _run(self, session, request, timeout, on_late_result=None):
        future = self._submit(session, request)
        try:
            return future.result(timeout)
        except FutureTimeoutError:
            if on_late_result is not None:
                def late(f):
                    if not f.cancelled() and f.exception() is None:
                        on_late_result(f.result())
                future.add_done_callback(late)
            raise ConsoleError('Timeout waiting for the Crazyflie console') from None

    def _submit(self, session, request):
        future = Future()
        if session.closed:
            future.set_exception(ConsoleError('The Crazyflie is not connected'))
            return future
        with self._worker_lock:
            if self._worker is None:
                self._worker = threading.Thread(target=self._work, name='ConsoleRequestThread', daemon=True)
                self._worker.start()
        self._requests.put((session, request, future))
        return future

    def _work(self):
        while True:
            session, request, future = self._requests.get()
            if not future.set_running_or_notify_cancel():
                continue
            try:
                if session.closed:
                    raise ConsoleError('The Crazyflie is not connected')
                future.set_result(request())
            except Exception as e:
                future.set_exception(e)

    def _release(self, session, path, timeout):
        if path == STM32_PATH or session.closed:
            return
        self._run(session, lambda: self._release_on_worker(session, path), timeout)

    def _disable_all(self, session):
        try:
            self._set_enabled(session, ALL_SOURCES, False)
        except ConsoleError as e:
            logger.warning('Could not stop the consoles left open by an earlier connection: %s', e)

    def _ensure_catalog(self, session):
        if session.catalog is not None:
            return list(session.catalog)
        if not session.supports_sources:
            session.set_catalog([])
            return []

        info = self._request(session, CATALOG_CHANNEL, [CATALOG_GET_INFO],
                             lambda r: r[0] == CATALOG_GET_INFO)
        if len(info) < 3:
            raise ConsoleError('Malformed console list response from the Crazyflie')

        paths = []
        for source_id in range(info[2]):
            item = self._request(session, CATALOG_CHANNEL, [CATALOG_GET_ITEM, source_id],
                                 lambda r: r[0] == CATALOG_GET_ITEM and (len(r) == 2 or r[2] == source_id))
            if len(item) < 4:
                raise ConsoleError('Malformed console list response from the Crazyflie')
            paths.append(item[3:].decode('utf-8', errors='replace'))

        session.set_catalog(paths)
        return list(paths)

    def _acquire(self, session, path):
        paths = self._ensure_catalog(session)
        if path not in paths:
            raise ConsoleError(f'The Crazyflie has no console named {path!r}', _FIRMWARE_ENOENT)
        source_id = paths.index(path)
        if session.open_counts[source_id] == 0:
            self._set_enabled(session, source_id, True)
        session.open_counts[source_id] += 1
        return session.sources[source_id]

    def _release_on_worker(self, session, path):
        source_id = session.catalog.index(path)
        session.open_counts[source_id] -= 1
        if session.open_counts[source_id] == 0:
            self._set_enabled(session, source_id, False)

    def _set_enabled(self, session, source_id, enabled):
        enabled = int(enabled)

        def matches(response):
            # An error response has no source ID; with one request in flight
            # it belongs to this request
            return response[0] == CONTROL_SET_ENABLED and \
                (len(response) == 2 or response[2:4] == bytes([source_id, enabled]))

        self._request(session, CONTROL_CHANNEL, [CONTROL_SET_ENABLED, source_id, enabled], matches)

    def _request(self, session, channel, data, matches):
        """
        Send a request and return its successful response. Retries while the
        firmware has not completed its startup.
        """
        not_ready_deadline = time.monotonic() + NOT_READY_TIMEOUT
        while True:
            response = self._transact(session, channel, data, matches)
            status = response[1]
            if status == 0:
                return response
            if status == _FIRMWARE_EAGAIN and time.monotonic() < not_ready_deadline:
                time.sleep(NOT_READY_RETRY_DELAY)
                continue
            raise ConsoleError(f'The Crazyflie rejected a console request (error {status})', status)

    def _transact(self, session, channel, data, matches):
        # Discard late answers to earlier requests
        while True:
            try:
                self._responses.get_nowait()
            except queue.Empty:
                break

        pk = CRTPPacket()
        pk.set_header(CRTPPort.CONSOLE, channel)
        pk.data = data
        self.cf.send_packet(pk, expected_reply=(data[0],))

        deadline = time.monotonic() + RESPONSE_TIMEOUT
        while True:
            remaining = deadline - time.monotonic()
            if session.closed:
                raise ConsoleError('The Crazyflie is not connected')
            if remaining <= 0:
                raise ConsoleError('No answer from the Crazyflie console')
            try:
                response = self._responses.get(timeout=remaining)
            except queue.Empty:
                continue
            if response is None:
                continue
            response_channel, response_data = response
            if response_channel == channel and len(response_data) >= 2 and matches(response_data):
                return response_data
