"""Experimental macOS BLE CRTP driver, bench-only, corrected firmware required.

Copyright (C) 2026. Licensed under GPL-3.0-or-later, as part of cflib.
"""
import asyncio
import logging
import queue
import threading
from urllib.parse import parse_qs
from urllib.parse import urlencode
from urllib.parse import urlsplit
from uuid import UUID

from .blepolicy import bench_allowed
from .bletransport import DownDecoder
from .bletransport import fragment_up
from .bletransport import FrameError
from .crtpdriver import CRTPDriver
from .crtpstack import CRTPPacket
from .exceptions import WrongUriType

logger = logging.getLogger(__name__)
SERVICE = '00000201-1c7f-4f9e-947b-43b7c00a9a08'
CRTP = '00000202-1c7f-4f9e-947b-43b7c00a9a08'
UP = '00000203-1c7f-4f9e-947b-43b7c00a9a08'
DOWN = '00000204-1c7f-4f9e-947b-43b7c00a9a08'
_END = object()
_HEALTH = b'\xfcCFBLE'


class FirmwareCompatibilityError(RuntimeError):
    pass


def parse_uri(uri):
    if not uri.startswith('ble://'):
        raise WrongUriType('Not a BLE URI')
    value = urlsplit(uri)
    if value.path or value.fragment or value.username or value.port:
        raise ValueError('Expected ble://<macOS UUID>?name=<exact name>')
    identifier = str(UUID(value.hostname))
    query = parse_qs(value.query, strict_parsing=True)
    if set(query) != {'name'} or len(query['name']) != 1 or not query['name'][0].startswith('Crazyflie'):
        raise ValueError('An exact Crazyflie name is required; unsupported URI options')
    return identifier, query['name'][0]


def validate_services(services):
    service = next((s for s in services if s.uuid.lower() == SERVICE), None)
    chars = {c.uuid.lower(): set(c.properties) for c in service.characteristics} if service else {}
    for uuid, required in ((CRTP, {'write'}), (UP, {'write'}), (DOWN, {'notify'})):
        if not required <= chars.get(uuid, set()):
            raise FirmwareCompatibilityError('Crazyflie GATT profile not found or incompatible')


class BleDriver(CRTPDriver):
    """Dedicated BLE event-loop thread; no flight-enable switch is provided."""

    def __init__(self):
        super().__init__()
        self.needs_resending = True
        self._thread = None
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._rx = queue.Queue(maxsize=512)
        self._tx = queue.Queue(maxsize=128)
        self._error = None
        self._callback = None
        self._closed = True
        self._owned_blocks = set()
        self._pending_blocks = set()
        self.stats = {'sent': 0, 'received': 0, 'nulls': 0, 'blocked': 0, 'cleanup': []}

    def connect(self, uri, radio_link_statistics_callback=None, link_error_callback=None):
        identifier, name = parse_uri(uri)
        if self._thread:
            raise RuntimeError('BLE driver already used; create a new instance')
        self._callback = link_error_callback
        self._closed = False
        self._thread = threading.Thread(target=self._worker, args=(identifier, name), name='CrazyflieBLE', daemon=True)
        self._thread.start()
        if not self._ready.wait(60):
            self.close()
            raise TimeoutError('BLE discovery/connection/probe timed out')
        if self._error:
            self.close()
            raise self._error

    def _worker(self, identifier, name):
        connected = False
        try:
            asyncio.run(self._session(identifier, name))
            connected = self._ready.is_set()
        except Exception as exc:
            connected = self._ready.is_set()
            self._error = exc
            logger.error('BLE: %s', exc)
        finally:
            self._closed = True
            self._ready.set()
            try:
                self._rx.put_nowait(_END)
            except queue.Full:
                pass
            # Callback after event-loop cleanup, not from a Bleak delegate.
            if connected and self._error and not self._stop.is_set() and self._callback:
                self._callback(str(self._error))

    async def _session(self, identifier, name):
        from bleak import BleakClient, BleakScanner
        found = await BleakScanner.discover(timeout=5, return_adv=True, scanning_mode='active')
        selected = [d for d, a in found.values() if d.address.lower() == identifier.lower()
                    and (a.local_name or d.name) == name]
        if len(selected) != 1:
            raise RuntimeError('Selected UUID and exact name were not discovered')
        fault = None

        def disconnected(_client):
            nonlocal fault
            if not self._stop.is_set():
                fault = RuntimeError('BLE disconnected unexpectedly')
        async with BleakClient(selected[0], timeout=12, disconnected_callback=disconnected) as client:
            validate_services(client.services)
            raw_frames = asyncio.Queue(maxsize=128)

            def notify(_characteristic, data):
                nonlocal fault
                try:
                    raw_frames.put_nowait(bytes(data))
                except asyncio.QueueFull:
                    fault = RuntimeError('BLE notification queue overflow')
            await asyncio.wait_for(client.start_notify(DOWN, notify), 5)
            try:
                decoder = DownDecoder()
                # Drain startup console and replies left by a previous session
                # before issuing fresh integrity probes. Still validate framing.
                warm_deadline = asyncio.get_running_loop().time() + 20
                last_frame = asyncio.get_running_loop().time()
                while asyncio.get_running_loop().time() < warm_deadline:
                    await self._write(client, b'\xff', 0)
                    await asyncio.sleep(0.04)
                    while not raw_frames.empty():
                        try:
                            decoder.feed(raw_frames.get_nowait())
                        except FrameError as exc:
                            raise FirmwareCompatibilityError('Unsupported BLE framing during startup drain') from exc
                        last_frame = asyncio.get_running_loop().time()
                    if decoder.pid is None and asyncio.get_running_loop().time() - last_frame >= 0.5:
                        break
                else:
                    raise TimeoutError('BLE startup stream did not become quiet')
                # Test exact bytes across the fragmentation boundary before
                # cflib downloads any TOC or initializes subsystems.
                for size in (8, 20, 31):
                    expected = bytes([0xFC]) + bytes(range(0x40, 0x40 + size - 1))
                    await self._write(client, expected, size & 3)
                    matched = False
                    for _ in range(250 if size == 8 else 25):
                        await asyncio.sleep(0.04)
                        await self._write(client, b'\xff', 0)
                        while not raw_frames.empty():
                            frame = raw_frames.get_nowait()
                            if (size == 8 and len(frame) == 9 and frame[0] == 0x88 and frame[1:] == expected):
                                raise FirmwareCompatibilityError(
                                    'Legacy BLE framing detected; corrected nRF firmware is required. '
                                    'See the experimental BLE driver documentation.')
                            packet = decoder.feed(frame)
                            if packet is not None:
                                if packet[0] & 0xF3 != 0xF0:
                                    continue
                                if packet != expected:
                                    raise FirmwareCompatibilityError('BLE echo failed byte-for-byte integrity check')
                                matched = True
                        if matched:
                            break
                    if not matched:
                        raise FirmwareCompatibilityError('BLE integrity probe did not receive a complete echo')
                decoder.reset()
                pid = 0
                self._ready.set()
                last_rx = asyncio.get_running_loop().time()
                last_health = last_rx
                while not self._stop.is_set():
                    if fault:
                        raise fault
                    while not raw_frames.empty():
                        packet = decoder.feed(raw_frames.get_nowait())
                        if packet is not None:
                            last_rx = asyncio.get_running_loop().time()
                            if packet == _HEALTH:
                                continue
                            self._track_reply(packet)
                            self._rx.put_nowait(CRTPPacket(header=packet[0], data=packet[1:]))
                            self.stats['received'] += 1
                    try:
                        packet = self._tx.get_nowait()
                    except queue.Empty:
                        if asyncio.get_running_loop().time() - last_health >= 2:
                            packet = _HEALTH
                            last_health = asyncio.get_running_loop().time()
                        else:
                            packet = b'\xff'
                    await self._write(client, packet, pid)
                    pid = (pid + 1) & 3
                    if packet == b'\xff':
                        self.stats['nulls'] += 1
                    else:
                        self.stats['sent'] += 1
                    if asyncio.get_running_loop().time() - last_rx > 10:
                        raise TimeoutError('BLE did not receive packets or health echoes for 10 seconds')
                    await asyncio.sleep(0.02)
            finally:
                if client.is_connected:
                    await self._cleanup(client, raw_frames, decoder)
                    await asyncio.wait_for(client.stop_notify(DOWN), 3)

    def _track_reply(self, packet):
        if len(packet) == 4 and packet[0] & 0xF3 == 0x51:
            command, block, status = packet[1:]
            if command == 6 and block in self._pending_blocks:
                self._pending_blocks.discard(block)
                if status == 0:
                    self._owned_blocks.add(block)
            elif command == 2 and status == 0:
                self._owned_blocks.discard(block)

    async def _cleanup(self, client, frames, decoder):
        for block in list(self._owned_blocks):
            for command in (4, 2):
                confirmed = False
                await self._write(client, bytes([0x5D, command, block]), 0)
                for _ in range(10):
                    await asyncio.sleep(0.04)
                    await self._write(client, b'\xff', 0)
                    while not frames.empty():
                        try:
                            packet = decoder.feed(frames.get_nowait())
                        except FrameError:
                            decoder.reset()
                            continue
                        if packet:
                            self._track_reply(packet)
                            if packet[0] & 0xF3 == 0x51 and packet[1:] == bytes([command, block, 0]):
                                confirmed = True
                    if confirmed:
                        break
                self.stats['cleanup'].append({'block': block, 'command': command, 'confirmed': confirmed})

    async def _write(self, client, packet, pid):
        if len(packet) <= 20:
            await asyncio.wait_for(client.write_gatt_char(CRTP, packet, response=True), 3)
        else:
            for frame in fragment_up(packet, pid):
                await asyncio.wait_for(client.write_gatt_char(UP, frame, response=True), 3)

    def send_packet(self, pk):
        packet = bytes([pk.get_header()]) + bytes(pk.data)
        allowed = bench_allowed(packet)
        if packet[0] & 0xF3 == 0x51 and len(packet) >= 3:
            command, block = packet[1:3]
            if command in (2, 3, 4, 7, 8) and block not in self._owned_blocks:
                allowed = False
            if (command == 6 and len(self._owned_blocks | self._pending_blocks) >= 4
                    and block not in self._pending_blocks):
                allowed = False
        if not allowed:
            self.stats['blocked'] += 1
            if self.stats['blocked'] == 1:
                logger.warning('BLE bench mode blocked a flight/control/persistent-write packet')
            return  # Do not deadlock cflib's send lock on its close-time setpoint.
        if self._closed:
            return
        try:
            if packet[0] & 0xF3 == 0x51 and packet[1] == 6:
                self._pending_blocks.add(packet[2])
            self._tx.put_nowait(packet)
        except queue.Full:
            self._error = RuntimeError('BLE transmit queue overflow; closing link')
            self._stop.set()
            if self._callback:
                threading.Thread(target=self._callback, args=(str(self._error),), daemon=True).start()

    def receive_packet(self, wait=0):
        if self._closed and self._rx.empty():
            return None
        try:
            value = self._rx.get(block=wait != 0, timeout=None if wait < 0 or wait == 0 else wait)
            return None if value is _END else value
        except queue.Empty:
            return None

    def close(self):
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=15)
        self._closed = True

    def get_name(self):
        return 'ble'

    def get_status(self):
        return 'Experimental BLE bench mode; flight and persistent writes blocked'

    def get_help(self):
        return 'ble://<macOS UUID>?name=<exact Crazyflie name>; corrected nRF required'

    def scan_interface(self, address=None):
        async def scan():
            from bleak import BleakScanner
            devices = await BleakScanner.discover(timeout=5, return_adv=True, scanning_mode='active')
            results = []
            for device, advertisement in devices.values():
                name = advertisement.local_name or device.name or ''
                if name.startswith('Crazyflie'):
                    try:
                        identifier = str(UUID(device.address))
                    except ValueError:
                        continue
                    results.append(['ble://' + identifier + '?' + urlencode({'name': name}), ''])
            return results
        # CLI callers may already have an event loop; isolate scan as well.
        result, error = [], []

        def worker():
            try:
                result.extend(asyncio.run(scan()))
            except Exception as exc:
                error.append(exc)
        thread = threading.Thread(target=worker, name='CrazyflieBLEScan', daemon=True)
        thread.start()
        thread.join(timeout=10)
        if thread.is_alive():
            raise TimeoutError('BLE scan did not terminate')
        if error:
            raise RuntimeError('BLE unavailable: check macOS Bluetooth permission and power: ' + str(error[0]))
        return result
