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
WiFi of a deck (cf.wifi), such as the camera deck.

Scans for access points, stores the network to join on the deck, joins it and
leaves it. Each call runs the whole exchange with the deck through
cf.apiservice and returns the result.

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        wifi = scf.cf.wifi
        for ap in wifi.scan():
            print(ap.ssid, ap.rssi)
        wifi.set_credentials('my-network', 'my-password')
        ip = wifi.connect()

The deck is any API Service endpoint that serves the wifi.* paths, from the
list WIFI_ENDPOINTS.
"""
import logging
import time
from enum import IntEnum
from ipaddress import IPv4Address
from threading import Event
from threading import Lock
from typing import List
from typing import NamedTuple
from typing import Union

from .apiservice import ApiserviceError
from .apiservice import ApiserviceErrorCode
from .apiservice import EndpointError
from .apiservice import ValueType

__author__ = 'Bitcraze AB'
__all__ = ['Wifi', 'AccessPoint', 'IpInfo', 'WifiState', 'WifiFailReason', 'WifiAuth', 'WifiError',
           'WifiConnectError', 'WifiScanError', 'WifiNotAvailableError', 'WIFI_ENDPOINTS']

logger = logging.getLogger(__name__)

# The API Service endpoints that serve the wifi.* paths. A new deck with WiFi
# is added here.
WIFI_ENDPOINTS = ('deck:bcCam',)

# Interval of the polls of the deck state, in case a notification is lost
POLL_INTERVAL = 0.5
# Interval between retries of a scan start that the deck answered busy
RETRY_INTERVAL = 0.5

_SCAN_STATE_SCANNING = 1
_SCAN_STATE_DONE = 2
_SCAN_STATE_FAILED = 3


class WifiState(IntEnum):
    """Connection state of the deck, the values of wifi.state"""
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    GOT_IP = 3
    FAILED = 4


class WifiFailReason(IntEnum):
    """Why the last join failed, the values of wifi.fail_reason"""
    NONE = 0
    AP_NOT_FOUND = 1
    AUTHENTICATION_FAILED = 2
    NO_IP_ADDRESS = 3
    OTHER = 4


class WifiAuth(IntEnum):
    """Security of an access point, as the deck reports it in a scan"""
    OPEN = 0
    WEP = 1
    WPA_PSK = 2
    WPA2_PSK = 3
    WPA_WPA2_PSK = 4
    WPA_ENTERPRISE = 5
    WPA3_SAE = 6
    WPA2_WPA3 = 7


class AccessPoint(NamedTuple):
    """An access point found by a scan.

    ssid is bytes, since an SSID is not guaranteed to be UTF-8, and empty for
    a hidden network. auth is a WifiAuth, or a plain int for an unknown value.
    """
    ssid: bytes
    rssi: int
    channel: int
    auth: Union[WifiAuth, int]
    bssid: bytes


class IpInfo(NamedTuple):
    """IPv4 settings of the deck, each 0.0.0.0 without one"""
    ip: IPv4Address
    netmask: IPv4Address
    gateway: IPv4Address
    dns: IPv4Address


class WifiError(Exception):
    """Base class of the errors raised by cf.wifi for a failure on the deck"""


class WifiNotAvailableError(WifiError):
    """No WiFi endpoint, or more than one, in the catalog of the connection"""


class WifiScanError(WifiError):
    """The deck reported a failed scan"""


class WifiConnectError(WifiError):
    """The deck failed to join the network. reason is a WifiFailReason."""

    def __init__(self, reason):
        self.reason = reason
        name = reason.name if isinstance(reason, WifiFailReason) else 'reason {}'.format(reason)
        super().__init__('Joining the network failed: {}'.format(name))


def _enum_or_int(enum, value):
    try:
        return enum(value)
    except ValueError:
        return value


def _decode_access_point(data):
    """Decode a wifi.scan_result value: ssid_len, ssid, rssi, channel, auth, bssid"""
    if len(data) < 1 or len(data) != 1 + data[0] + 9:
        raise WifiError('Malformed scan result of {} bytes'.format(len(data)))
    ssid_len = data[0]
    rest = data[1 + ssid_len:]
    rssi = int.from_bytes(rest[0:1], 'little', signed=True)
    return AccessPoint(bytes(data[1:1 + ssid_len]), rssi, rest[1], _enum_or_int(WifiAuth, rest[2]),
                       bytes(rest[3:9]))


class Wifi:
    """WiFi of a deck (cf.wifi).

    The calls block, and must not be made from a cflib callback. Errors of the
    API Service, such as a lost connection, are raised as they are, see
    cflib.crazyflie.apiservice.
    """

    def __init__(self, crazyflie):
        self._cf = crazyflie
        self._lock = Lock()
        self._endpoint_cache = None
        self._cf.disconnected.add_callback(self._disconnected)
        self._cf.connection_lost.add_callback(self._disconnected)

    def scan(self, timeout=15.0) -> List[AccessPoint]:
        """Scan for access points. Returns them sorted by RSSI, strongest first.

        Raises TimeoutError if the scan does not finish within timeout seconds,
        and WifiScanError if the deck reports a failed scan.
        """
        endpoint = self._endpoint()
        deadline = time.monotonic() + timeout

        def start():
            # The deck answers BUSY while it cannot scan, for example while it
            # scans to join its network.
            while True:
                try:
                    endpoint.cmd('wifi.scan')
                    return
                except EndpointError as e:
                    if e.code != ApiserviceErrorCode.BUSY or time.monotonic() + RETRY_INTERVAL >= deadline:
                        raise
                time.sleep(RETRY_INTERVAL)

        state = self._wait(endpoint, 'wifi.scan_state', lambda s: s != _SCAN_STATE_SCANNING, start, deadline,
                           'The scan did not finish within {} s'.format(timeout))
        if state == _SCAN_STATE_FAILED:
            raise WifiScanError('The scan failed on the deck')
        if state != _SCAN_STATE_DONE:
            raise WifiScanError('Unexpected scan state {}'.format(state))

        count = endpoint.get('wifi.scan_count')
        access_points = [_decode_access_point(endpoint.cmd('wifi.scan_result', i, ValueType.U8))
                         for i in range(count)]
        return sorted(access_points, key=lambda ap: ap.rssi, reverse=True)

    def set_credentials(self, ssid: Union[bytes, str], password: str) -> None:
        """Store the network to join on the deck.

        ssid is bytes, or a str that is encoded as UTF-8, 1 to 32 bytes.
        password is 8 to 63 characters, or empty for an open network. The
        deck keeps them in RAM only, and never returns the password.
        """
        if isinstance(ssid, str):
            ssid = ssid.encode('utf-8')
        endpoint = self._endpoint()
        endpoint.set('wifi.ssid', bytes(ssid), ValueType.BYTES)
        endpoint.set('wifi.password', password, ValueType.STRING)

    def connect(self, timeout=30.0) -> IPv4Address:
        """Join the stored network and wait until the deck has an IP address.

        Returns the IP address. On a failed join, or at the timeout, the deck
        is stopped with disconnect(), since it would otherwise keep retrying,
        and WifiConnectError or TimeoutError is raised.
        """
        endpoint = self._endpoint()
        deadline = time.monotonic() + timeout
        done = (WifiState.GOT_IP, WifiState.FAILED)
        try:
            state = self._wait(endpoint, 'wifi.state', lambda s: s in done, lambda: endpoint.cmd('wifi.connect'),
                               deadline, 'No IP address within {} s'.format(timeout))
            if state == WifiState.FAILED:
                raise WifiConnectError(_enum_or_int(WifiFailReason, endpoint.get('wifi.fail_reason')))
        except (WifiError, TimeoutError):
            self._stop(endpoint)
            raise
        return IPv4Address(endpoint.get('wifi.ip'))

    def disconnect(self) -> None:
        """Leave the network. The deck stops rejoining it."""
        self._endpoint().cmd('wifi.disconnect')

    def state(self) -> WifiState:
        """The current connection state"""
        return _enum_or_int(WifiState, self._endpoint().get('wifi.state'))

    def ip_info(self) -> IpInfo:
        """The current IP address, netmask, gateway and DNS server"""
        endpoint = self._endpoint()
        return IpInfo(*(IPv4Address(endpoint.get(path))
                        for path in ('wifi.ip', 'wifi.netmask', 'wifi.gateway', 'wifi.dns')))

    def _endpoint(self):
        """The WiFi endpoint of this connection, looked up on first use"""
        with self._lock:
            if self._endpoint_cache is not None:
                return self._endpoint_cache
        found = [e for e in self._cf.apiservice.endpoints() if e.path in WIFI_ENDPOINTS]
        if not found:
            raise WifiNotAvailableError('No WiFi endpoint found, looked for {}'.format(', '.join(WIFI_ENDPOINTS)))
        if len(found) > 1:
            raise WifiNotAvailableError(
                'More than one WiFi endpoint found: {}'.format(', '.join(e.path for e in found)))
        with self._lock:
            self._endpoint_cache = found[0]
        logger.info('WiFi endpoint: %s', found[0].path)
        return found[0]

    def _disconnected(self, *args):
        with self._lock:
            self._endpoint_cache = None

    @staticmethod
    def _wait(endpoint, path, is_done, start, deadline, timeout_message):
        """Run start(), then wait until is_done(value of path), and return the value.

        Waits for a notification of path, and polls it in case the
        notification is lost or the Crazyflie cannot forward notifications.
        """
        changed = Event()

        def on_change(changed_path, value):
            if changed_path == path:
                changed.set()

        endpoint.notified.add_callback(on_change)
        try:
            try:
                endpoint.set_notify(True)
            except ApiserviceError:
                pass  # No notifications: polling only
            start()
            while True:
                changed.clear()
                value = endpoint.get(path)
                if is_done(value):
                    return value
                if time.monotonic() >= deadline:
                    raise TimeoutError(timeout_message)
                changed.wait(max(0.0, min(POLL_INTERVAL, deadline - time.monotonic())))
        finally:
            endpoint.notified.remove_callback(on_change)

    @staticmethod
    def _stop(endpoint):
        """Stop a join, without hiding the error that caused it"""
        try:
            endpoint.cmd('wifi.disconnect')
        except ApiserviceError as e:
            logger.warning('Could not stop the join: %s', e)
