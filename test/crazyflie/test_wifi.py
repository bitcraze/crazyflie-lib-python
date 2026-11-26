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
Tests of cf.wifi against a fake WiFi endpoint, which plays the deck.
"""
import unittest
from ipaddress import IPv4Address
from unittest import mock

from cflib.crazyflie import wifi as wifi_module
from cflib.crazyflie.apiservice import ApiserviceErrorCode
from cflib.crazyflie.apiservice import ApiserviceTimeoutError
from cflib.crazyflie.apiservice import CrazyflieApiserviceError
from cflib.crazyflie.apiservice import EndpointError
from cflib.crazyflie.apiservice import FirmwareErrno
from cflib.crazyflie.apiservice import ValueType
from cflib.crazyflie.wifi import AccessPoint
from cflib.crazyflie.wifi import IpInfo
from cflib.crazyflie.wifi import Wifi
from cflib.crazyflie.wifi import WifiAuth
from cflib.crazyflie.wifi import WifiConnectError
from cflib.crazyflie.wifi import WifiFailReason
from cflib.crazyflie.wifi import WifiNotAvailableError
from cflib.crazyflie.wifi import WifiScanError
from cflib.crazyflie.wifi import WifiState
from cflib.utils.callbacks import Caller

BSSID = bytes((1, 2, 3, 4, 5, 6))


def scan_result(ssid, rssi, channel=6, auth=3, bssid=BSSID):
    return bytes((len(ssid),)) + ssid + rssi.to_bytes(1, 'little', signed=True) + bytes((channel, auth)) + bssid


class FakeEndpoint:
    """The wifi.* paths of a deck. Commands run handlers that tests may replace."""

    def __init__(self, path='deck:bcCam'):
        self.path = path
        self.notified = Caller()
        self.notify_supported = True
        self.values = {
            'wifi.state': WifiState.DISCONNECTED,
            'wifi.fail_reason': WifiFailReason.NONE,
            'wifi.scan_state': 0,
            'wifi.scan_count': 0,
            'wifi.ip': bytes(4),
            'wifi.netmask': bytes(4),
            'wifi.gateway': bytes(4),
            'wifi.dns': bytes(4),
        }
        self.scan_results = []
        self.calls = []
        self.sets = []
        # Called on GET of a path, may change the values: models the deck
        # progressing between polls.
        self.on_get = {}
        self.cmd_handlers = {
            'wifi.scan': self._scan,
            'wifi.scan_result': lambda i: self.scan_results[i],
            'wifi.connect': self._connect,
            'wifi.disconnect': self._disconnect,
        }

    def set_notify(self, enabled, timeout=None):
        if not self.notify_supported:
            raise CrazyflieApiserviceError(FirmwareErrno.ENOSYS, True)

    def get(self, path, timeout=None):
        self.calls.append(('get', path))
        handler = self.on_get.get(path)
        if handler is not None:
            handler()
        return self.values[path]

    def set(self, path, value, value_type=None, timeout=None):
        self.sets.append((path, value, value_type))

    def cmd(self, path, arg=None, arg_type=None, timeout=None):
        self.calls.append(('cmd', path))
        handler = self.cmd_handlers[path]
        return handler(arg) if path == 'wifi.scan_result' else handler()

    def _scan(self):
        self.values['wifi.scan_state'] = 1

    def _connect(self):
        self.values['wifi.state'] = WifiState.CONNECTING
        self.values['wifi.fail_reason'] = WifiFailReason.NONE

    def _disconnect(self):
        self.values['wifi.state'] = WifiState.DISCONNECTED

    def finish_scan(self, results, state=2):
        self.scan_results = results
        self.values['wifi.scan_count'] = len(results)
        self.values['wifi.scan_state'] = state
        self.notified.call('wifi.scan_state', state)


class StubApiservice:
    def __init__(self, endpoints):
        self.endpoints_list = endpoints
        self.endpoints_calls = 0

    def endpoints(self, timeout=None):
        self.endpoints_calls += 1
        return list(self.endpoints_list)


class StubCrazyflie:
    def __init__(self, endpoints):
        self.disconnected = Caller()
        self.connection_lost = Caller()
        self.apiservice = StubApiservice(endpoints)


class WifiTestBase(unittest.TestCase):

    def setUp(self):
        self.endpoint = FakeEndpoint()
        self.cf = StubCrazyflie([FakeEndpoint('deck:other'), self.endpoint])
        self.wifi = Wifi(self.cf)
        # Keep the waits short
        patcher = mock.patch.object(wifi_module, 'POLL_INTERVAL', 0.01)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(wifi_module, 'RETRY_INTERVAL', 0.01)
        patcher.start()
        self.addCleanup(patcher.stop)


class EndpointLookupTest(WifiTestBase):

    def test_finds_the_wifi_endpoint(self):
        self.wifi.disconnect()
        self.assertIn(('cmd', 'wifi.disconnect'), self.endpoint.calls)

    def test_lookup_is_done_once_per_connection(self):
        self.wifi.state()
        self.wifi.state()
        self.assertEqual(1, self.cf.apiservice.endpoints_calls)
        self.cf.disconnected.call('uri')
        self.wifi.state()
        self.assertEqual(2, self.cf.apiservice.endpoints_calls)

    def test_no_wifi_endpoint(self):
        self.cf.apiservice.endpoints_list = [FakeEndpoint('deck:other')]
        with self.assertRaises(WifiNotAvailableError):
            self.wifi.state()

    def test_more_than_one_wifi_endpoint(self):
        with mock.patch.object(wifi_module, 'WIFI_ENDPOINTS', ('deck:bcCam', 'deck:other')):
            with self.assertRaises(WifiNotAvailableError):
                self.wifi.state()


class ScanTest(WifiTestBase):

    def test_scan_returns_access_points_sorted_by_rssi(self):
        results = [scan_result(b'weak', -80), scan_result(b'strong', -30, auth=7), scan_result(b'', -50, auth=99)]
        self.endpoint.on_get['wifi.scan_state'] = lambda: self.endpoint.finish_scan(results)

        aps = self.wifi.scan()

        self.assertEqual([b'strong', b'', b'weak'], [ap.ssid for ap in aps])
        self.assertEqual(AccessPoint(b'strong', -30, 6, WifiAuth.WPA2_WPA3, BSSID), aps[0])
        self.assertEqual(99, aps[1].auth)

    def test_ssid_is_kept_as_bytes(self):
        results = [scan_result(b'\xff\x00x', -40)]
        self.endpoint.on_get['wifi.scan_state'] = lambda: self.endpoint.finish_scan(results)
        self.assertEqual(b'\xff\x00x', self.wifi.scan()[0].ssid)

    def test_busy_scan_start_is_retried(self):
        busy = [EndpointError(ApiserviceErrorCode.BUSY, 'WiFi busy, try again')] * 2

        def scan():
            if busy:
                raise busy.pop()
            self.endpoint.finish_scan([])
        self.endpoint.cmd_handlers['wifi.scan'] = scan

        self.assertEqual([], self.wifi.scan())
        self.assertEqual(3, self.endpoint.calls.count(('cmd', 'wifi.scan')))

    def test_busy_until_timeout_raises(self):
        def scan():
            raise EndpointError(ApiserviceErrorCode.BUSY, 'a scan is running')
        self.endpoint.cmd_handlers['wifi.scan'] = scan
        with self.assertRaises(EndpointError):
            self.wifi.scan(timeout=0.05)

    def test_scan_timeout(self):
        with self.assertRaises(TimeoutError):
            self.wifi.scan(timeout=0.05)

    def test_failed_scan(self):
        self.endpoint.on_get['wifi.scan_state'] = lambda: self.endpoint.finish_scan([], state=3)
        with self.assertRaises(WifiScanError):
            self.wifi.scan()

    def test_scan_without_notifications_polls(self):
        self.endpoint.notify_supported = False
        polls = []

        def poll():
            polls.append(1)
            if len(polls) == 3:
                self.endpoint.values['wifi.scan_state'] = 2
        self.endpoint.on_get['wifi.scan_state'] = poll
        self.assertEqual([], self.wifi.scan())
        self.assertEqual(3, len(polls))

    def test_malformed_scan_result(self):
        self.endpoint.on_get['wifi.scan_state'] = lambda: self.endpoint.finish_scan([b'\x05abc'])
        with self.assertRaises(wifi_module.WifiError):
            self.wifi.scan()

    def test_notification_callback_is_removed(self):
        self.endpoint.on_get['wifi.scan_state'] = lambda: self.endpoint.finish_scan([])
        self.wifi.scan()
        self.assertEqual([], self.endpoint.notified.callbacks)


class CredentialsTest(WifiTestBase):

    def test_str_ssid_is_encoded_as_utf8(self):
        self.wifi.set_credentials('kaffe☕', 'password1')
        self.assertEqual([('wifi.ssid', 'kaffe☕'.encode('utf-8'), ValueType.BYTES),
                          ('wifi.password', 'password1', ValueType.STRING)], self.endpoint.sets)

    def test_bytes_ssid_is_sent_as_is(self):
        self.wifi.set_credentials(b'\xff\x01', '')
        self.assertEqual(('wifi.ssid', b'\xff\x01', ValueType.BYTES), self.endpoint.sets[0])
        self.assertEqual(('wifi.password', '', ValueType.STRING), self.endpoint.sets[1])


class ConnectTest(WifiTestBase):

    def got_ip_after(self, polls):
        count = []

        def poll():
            count.append(1)
            if len(count) == polls:
                self.endpoint.values['wifi.ip'] = bytes((192, 168, 1, 5))
                self.endpoint.values['wifi.state'] = WifiState.GOT_IP
                self.endpoint.notified.call('wifi.state', WifiState.GOT_IP)
        self.endpoint.on_get['wifi.state'] = poll

    def fail_with(self, reason):
        def poll():
            if self.endpoint.values['wifi.state'] == WifiState.CONNECTING:
                self.endpoint.values['wifi.fail_reason'] = reason
                self.endpoint.values['wifi.state'] = WifiState.FAILED
        self.endpoint.on_get['wifi.state'] = poll

    def test_connect_returns_the_ip_address(self):
        self.got_ip_after(3)
        self.assertEqual(IPv4Address('192.168.1.5'), self.wifi.connect())
        self.assertNotIn(('cmd', 'wifi.disconnect'), self.endpoint.calls)

    def test_failed_join_raises_with_reason_and_stops_the_deck(self):
        self.fail_with(WifiFailReason.AUTHENTICATION_FAILED)
        with self.assertRaises(WifiConnectError) as ctx:
            self.wifi.connect()
        self.assertEqual(WifiFailReason.AUTHENTICATION_FAILED, ctx.exception.reason)
        self.assertEqual(('cmd', 'wifi.disconnect'), self.endpoint.calls[-1])

    def test_unknown_fail_reason_is_an_int(self):
        self.fail_with(42)
        with self.assertRaises(WifiConnectError) as ctx:
            self.wifi.connect()
        self.assertEqual(42, ctx.exception.reason)

    def test_timeout_raises_and_stops_the_deck(self):
        with self.assertRaises(TimeoutError):
            self.wifi.connect(timeout=0.05)
        self.assertEqual(('cmd', 'wifi.disconnect'), self.endpoint.calls[-1])

    def test_failing_stop_does_not_hide_the_error(self):
        def disconnect():
            raise ApiserviceTimeoutError('link lost')
        self.endpoint.cmd_handlers['wifi.disconnect'] = disconnect
        self.fail_with(WifiFailReason.AP_NOT_FOUND)
        with self.assertRaises(WifiConnectError):
            self.wifi.connect()

    def test_rejected_connect_is_raised_without_stop(self):
        def connect():
            raise EndpointError(ApiserviceErrorCode.COMMAND_REJECTED, 'no SSID set')
        self.endpoint.cmd_handlers['wifi.connect'] = connect
        with self.assertRaises(EndpointError):
            self.wifi.connect()
        self.assertNotIn(('cmd', 'wifi.disconnect'), self.endpoint.calls)


class StateTest(WifiTestBase):

    def test_state(self):
        self.endpoint.values['wifi.state'] = 3
        self.assertIs(WifiState.GOT_IP, self.wifi.state())

    def test_ip_info(self):
        self.endpoint.values.update({
            'wifi.ip': bytes((192, 168, 1, 5)),
            'wifi.netmask': bytes((255, 255, 255, 0)),
            'wifi.gateway': bytes((192, 168, 1, 1)),
        })
        self.assertEqual(IpInfo(IPv4Address('192.168.1.5'), IPv4Address('255.255.255.0'),
                                IPv4Address('192.168.1.1'), IPv4Address('0.0.0.0')), self.wifi.ip_info())

    def test_disconnect(self):
        self.wifi.disconnect()
        self.assertEqual([('cmd', 'wifi.disconnect')], self.endpoint.calls)


if __name__ == '__main__':
    unittest.main()
