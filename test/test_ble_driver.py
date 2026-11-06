import asyncio
import struct
import sys
import threading
import unittest
from types import ModuleType
from types import SimpleNamespace as NS
from unittest.mock import patch

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crtp.bledriver import BleDriver
from cflib.crtp.bledriver import FirmwareCompatibilityError
from cflib.crtp.bledriver import parse_uri
from cflib.crtp.blepolicy import bench_allowed
from cflib.crtp.bletransport import DownDecoder
from cflib.crtp.bletransport import fragment_up
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.exceptions import WrongUriType

IDENTIFIER = '00000000-0000-4000-8000-000000000001'
URI = 'ble://' + IDENTIFIER + '?name=Crazyflie-ABCDEF'


class FakePeripheral:
    """A corrected firmware simulator; never touches CoreBluetooth."""
    legacy = False
    create_status = 0
    instances = []

    def __init__(self, device, **kwargs):
        from cflib.crtp.bledriver import SERVICE, CRTP, UP, DOWN
        self.is_connected = True
        self.services = [NS(uuid=SERVICE, characteristics=[
            NS(uuid=CRTP, properties=['write']),
            NS(uuid=UP, properties=['write']), NS(uuid=DOWN, properties=['notify'])])]
        self.callback = None
        self.decoder = DownDecoder()
        self.sent = []
        self.blocks = set()
        self.block_ops = {}
        self.pid = 0
        self.cancel = kwargs.get('disconnected_callback')
        self.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.is_connected = False

    async def start_notify(self, uuid, callback):
        self.callback = callback

    async def stop_notify(self, uuid):
        self.callback = None

    def respond(self, raw):
        if self.legacy:
            self.callback(None, bytes([0x80 | len(raw)]) + raw)
        else:
            for frame in fragment_up(raw, self.pid):
                self.callback(None, frame)
            self.pid = (self.pid + 1) & 3

    async def write_gatt_char(self, uuid, data, response):
        from cflib.crtp.bledriver import UP
        raw = self.decoder.feed(data) if uuid == UP else bytes(data)
        if raw is None:
            return
        self.sent.append(raw)
        h, payload = raw[0] & 0xF3, raw[1:]
        if h == 0xF0:
            self.respond(raw)
        elif raw == b'\xff':
            return
        elif h == 0xF1:
            self.respond(bytes([raw[0]]) + b'Bitcraze Crazyflie' + bytes(12))
        elif h == 0xD1:
            self.respond(bytes([raw[0], payload[0]]) + (b'\x08\0\0\0' if payload[0] == 0 else b'2024.10'))
        elif h in (0x50, 0x20) and payload == b'\x03':
            count = 3 if h == 0x50 else 1
            self.respond(bytes([raw[0], 3]) + struct.pack('<HI', count, 1234 if h == 0x50 else 5678) + b'\x10\x80')
        elif h in (0x50, 0x20) and payload[0] == 2:
            index = int.from_bytes(payload[1:], 'little')
            if h == 0x50:
                fields = [(7, 'pm', 'vbat'), (1, 'pm', 'state'), (7, 'longGroup', 'longVariable')]
                kind, group, name = fields[index]
            else:
                kind, group, name = (8, 'test', 'value')
            self.respond(bytes([raw[0]]) + payload + bytes([kind]) + group.encode() + b'\0' + name.encode() + b'\0')
        elif h == 0x40 and payload == b'\x01':
            self.respond(bytes([raw[0], 1, 0]))
        elif h == 0x21:
            self.respond(bytes([raw[0]]) + payload + b'\0\x07')
        elif h == 0x51:
            cmd, block = payload[:2]
            if cmd == 6 and self.create_status == 0:
                self.blocks.add(block)
                self.block_ops[block] = [payload[i] & 15 for i in range(2, len(payload), 3)]
            elif cmd == 2:
                self.blocks.discard(block)
            self.respond(bytes([raw[0], cmd, block, self.create_status if cmd == 6 else 0]))
            if cmd == 3:
                async def emit():
                    for timestamp in (1000, 2000, 3000):
                        await asyncio.sleep(0.05)
                        if self.callback and self.is_connected and block in self.blocks:
                            values = b''.join(struct.pack('<f', 3.8) if kind ==
                                              7 else b'\0' for kind in self.block_ops[block])
                            self.respond(bytes([0x5E, block]) + timestamp.to_bytes(3, 'little') + values)
                asyncio.create_task(emit())
        else:
            raise AssertionError('Simulator received unexpected packet ' + raw.hex())


async def fake_discover(**kwargs):
    return {IDENTIFIER: (NS(address=IDENTIFIER, name='Crazyflie-ABCDEF'), NS(local_name='Crazyflie-ABCDEF'))}


class UriAndPolicyTests(unittest.TestCase):
    def test_uri_and_policy(self):
        self.assertEqual(parse_uri(URI)[1], 'Crazyflie-ABCDEF')
        with self.assertRaises(WrongUriType):
            parse_uri('radio://0/80/2M')
        for suffix in ('?name=Crazyflie&flight=true', '?name=other', ''):
            with self.assertRaises(ValueError):
                parse_uri('ble://' + IDENTIFIER + suffix)
        for packet in (b'\x3c\0', b'\x7c\0', b'\x8c\0', b'\x9c\0', b'\xdc\x01',
                       b'\x2e\0', b'\x4e\0', b'\xff\xfe', b'\x5d\x05'):
            self.assertFalse(bench_allowed(packet), packet.hex())
        self.assertTrue(bench_allowed(b'\xdd\0'))


class DriverTests(unittest.TestCase):
    def setUp(self):
        FakePeripheral.legacy = False
        FakePeripheral.create_status = 0
        FakePeripheral.instances.clear()
        # Exercise the transport without an installed Bleak backend or hardware.
        backend = ModuleType('bleak')
        backend.BleakClient = FakePeripheral
        backend.BleakScanner = NS(discover=fake_discover)
        self.backend = patch.dict(sys.modules, {'bleak': backend})
        self.backend.start()
        self.addCleanup(self.backend.stop)
        self.scan = patch('bleak.BleakScanner.discover', fake_discover)
        self.client = patch('bleak.BleakClient', FakePeripheral)
        self.scan.start()
        self.client.start()

    def tearDown(self):
        self.client.stop()
        self.scan.stop()

    def test_driver_lifecycle_and_flight_block(self):
        driver = BleDriver()
        driver.connect(URI)
        driver.send_packet(CRTPPacket(0x30, b'\0' * 14))
        self.assertEqual(driver.stats['blocked'], 1)
        driver.send_packet(CRTPPacket(0xD1, b'\0'))
        response = driver.receive_packet(wait=2)
        self.assertEqual(bytes(response.data), b'\0\x08\0\0\0')
        driver.close()
        self.assertFalse(driver._thread.is_alive())
        self.assertFalse(FakePeripheral.instances[-1].is_connected)
        self.assertTrue(all(bench_allowed(p) for p in FakePeripheral.instances[-1].sent))

    def test_startup_console_and_stale_echo_are_drained_before_probes(self):
        class StartupPeripheral(FakePeripheral):
            async def start_notify(self, uuid, callback):
                await super().start_notify(uuid, callback)
                self.respond(b'\x00startup console fragmented')
                self.respond(b'\xfcOLD_ECHO')
        driver = BleDriver()
        with patch('bleak.BleakClient', StartupPeripheral):
            try:
                driver.connect(URI)
                self.assertTrue(driver._ready.is_set())
                self.assertIsNone(driver._error)
            finally:
                driver.close()
        self.assertFalse(driver._thread.is_alive())

    def test_ble_retry_budget_does_not_change_radio_budget(self):
        cf = Crazyflie()
        packet = CRTPPacket(header=0xdd, data=b'\x00')
        try:
            for name, expected in (('ble', 0.8), ('radio', 0.2)):
                cf.link = NS(get_name=lambda n=name: n, needs_resending=True,
                             send_packet=lambda packet: None)
                with patch('cflib.crazyflie.Timer') as timer:
                    cf.send_packet(packet, expected_reply=(0,))
                    self.assertEqual(timer.call_args.args[0], expected)
                cf._answer_patterns.clear()
        finally:
            cf.link = None

    def test_legacy_fails_before_cflib_setup(self):
        FakePeripheral.legacy = True
        driver = BleDriver()
        with self.assertRaises(FirmwareCompatibilityError):
            driver.connect(URI)
        self.assertFalse(driver._thread.is_alive())
        self.assertFalse(any(p[0] & 0xF3 in (0x20, 0x50) for p in FakePeripheral.instances[-1].sent))

    def test_full_cflib_initialization_downloads_long_toc(self):
        saved = list(cflib.crtp.CLASSES)
        cflib.crtp.CLASSES[:] = [BleDriver]
        cf = Crazyflie()
        ready = threading.Event()
        errors = []
        cf.fully_connected.add_callback(lambda _uri: ready.set())
        cf.connection_failed.add_callback(lambda uri, error: errors.append(error))
        try:
            cf.open_link(URI)
            self.assertTrue(ready.wait(10), errors)
            self.assertEqual(len(cf.log.toc.toc['pm']), 2)
            self.assertIn('longVariable', cf.log.toc.toc['longGroup'])
            self.assertEqual(cf.param.get_value('test.value'), '7')
            from cflib.crazyflie.log import LogConfig
            log = LogConfig('BLE integration battery', 1000)
            log.add_variable('pm.vbat', 'float')
            samples = []
            got_samples = threading.Event()

            def sample(timestamp, data, config):
                samples.append(data['pm.vbat'])
                if len(samples) >= 3:
                    got_samples.set()
            log.data_received_cb.add_callback(sample)
            cf.log.add_config(log)
            log.start()
            self.assertTrue(got_samples.wait(3))
            self.assertAlmostEqual(samples[0], 3.8, places=5)
            driver = cf.link
            cf.close_link()
            self.assertTrue(driver.stats['cleanup'])
            self.assertTrue(all(entry['confirmed'] for entry in driver.stats['cleanup']))
            self.assertFalse(FakePeripheral.instances[-1].blocks)
            self.assertFalse(driver._thread.is_alive())
            self.assertTrue(all(bench_allowed(p) for p in FakePeripheral.instances[-1].sent))
        finally:
            if cf.link:
                cf.close_link()
            cflib.crtp.CLASSES[:] = saved

    def test_unexpected_disconnect_reports_and_stops(self):
        driver = BleDriver()
        error = threading.Event()
        messages = []

        def callback(message):
            messages.append(message)
            driver.close()
            error.set()
        driver.connect(URI, link_error_callback=callback)
        FakePeripheral.instances[-1].cancel(None)
        self.assertTrue(error.wait(3))
        driver.close()
        self.assertIn('disconnected', messages[0])
        self.assertFalse(driver._thread.is_alive())

    def test_refused_create_never_deletes_existing_block(self):
        FakePeripheral.create_status = 17
        driver = BleDriver()
        driver.connect(URI)
        driver.send_packet(CRTPPacket(0x51, b'\x06\x01\x77\0\0'))
        response = driver.receive_packet(wait=2)
        self.assertEqual(response.data[-1], 17)
        driver.close()
        sent = FakePeripheral.instances[-1].sent
        self.assertFalse(any(p[:2] in (b'\x5d\x04', b'\x5d\x02') for p in sent))

    def test_opt_in_registration_keeps_radio_available(self):
        saved = list(cflib.crtp.CLASSES)
        try:
            cflib.crtp.CLASSES.clear()
            cflib.crtp.init_drivers()
            self.assertNotIn(BleDriver, cflib.crtp.CLASSES)
            self.assertTrue(any(c.__name__ == 'RadioDriver' for c in cflib.crtp.CLASSES))
            cflib.crtp.init_drivers(enable_ble_driver=True)
            self.assertEqual(cflib.crtp.CLASSES.count(BleDriver), 1)
        finally:
            cflib.crtp.CLASSES[:] = saved

    def test_receive_forever_unblocks_on_close(self):
        driver = BleDriver()
        driver.connect(URI)
        waiter = threading.Thread(target=lambda: driver.receive_packet(-1))
        waiter.start()
        driver.close()
        waiter.join(timeout=2)
        self.assertFalse(waiter.is_alive())
