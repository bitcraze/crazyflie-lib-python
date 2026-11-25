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
Let the camera deck scan for WiFi access points, and print the ones it found.

    python3 wifi_scan.py
    python3 wifi_scan.py --uri usb://0

The URI comes from --uri, or the CFLIB_URI environment variable.

The deck is asked to scan with the command wifi.scan. The command answers
BUSY while the deck's WiFi cannot start a scan, for example while it scans to
join its network, so it is sent again until the timeout. The deck notifies
wifi.scan_state when the scan is done; the state is also polled, in case the
notification is lost or the Crazyflie cannot forward notifications. The access
points are then read one at a time with the command wifi.scan_result.
"""
import argparse
import logging
import threading
import time
from typing import NamedTuple

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.apiservice import ApiserviceError
from cflib.crazyflie.apiservice import ApiserviceErrorCode
from cflib.crazyflie.apiservice import EndpointError
from cflib.crazyflie.apiservice import ValueType
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

SCAN_STATE_SCANNING = 1
SCAN_STATE_DONE = 2
SCAN_STATE_FAILED = 3

POLL_INTERVAL = 0.5
RETRY_INTERVAL = 0.5

AUTH_NAMES = {
    0: 'open',
    1: 'WEP',
    2: 'WPA-PSK',
    3: 'WPA2-PSK',
    4: 'WPA/WPA2-PSK',
    5: 'WPA-Enterprise',
    6: 'WPA3-SAE',
    7: 'WPA2/WPA3',
}


class AccessPoint(NamedTuple):
    ssid: str
    rssi: int
    channel: int
    auth: int
    bssid: bytes

    @property
    def auth_name(self):
        return AUTH_NAMES.get(self.auth, f'unknown ({self.auth})')

    @property
    def bssid_text(self):
        return ':'.join(f'{b:02x}' for b in self.bssid)


def decode_access_point(data):
    """Decode a wifi.scan_result value: ssid_len, ssid, rssi, channel, auth, bssid"""
    ssid_len = data[0]
    if len(data) != 1 + ssid_len + 3 + 6:
        raise ValueError(f'scan result of {len(data)} bytes, expected {1 + ssid_len + 9}')
    ssid = data[1:1 + ssid_len].decode('utf-8', errors='replace')
    rest = data[1 + ssid_len:]
    rssi = int.from_bytes(rest[0:1], 'little', signed=True)
    return AccessPoint(ssid, rssi, rest[1], rest[2], bytes(rest[3:9]))


def start_scan(endpoint, deadline):
    """Send wifi.scan, again while the deck answers BUSY, until deadline"""
    while True:
        try:
            endpoint.cmd('wifi.scan')
            return
        except EndpointError as e:
            if e.code != ApiserviceErrorCode.BUSY or time.monotonic() + RETRY_INTERVAL >= deadline:
                raise
        time.sleep(RETRY_INTERVAL)


def scan(endpoint, timeout):
    """Run a scan on the deck and return the access points it found"""
    done = threading.Event()

    def on_change(path, value):
        if path == 'wifi.scan_state' and value != SCAN_STATE_SCANNING:
            done.set()

    endpoint.notified.add_callback(on_change)
    try:
        try:
            endpoint.set_notify(True)
        except ApiserviceError:
            pass  # No notifications, polling only

        deadline = time.monotonic() + timeout
        start_scan(endpoint, deadline)

        while True:
            state = endpoint.get('wifi.scan_state')
            if state != SCAN_STATE_SCANNING:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError(f'the scan did not finish within {timeout} s')
            done.wait(POLL_INTERVAL)
    finally:
        endpoint.notified.remove_callback(on_change)

    if state == SCAN_STATE_FAILED:
        raise RuntimeError('the scan failed on the deck')
    if state != SCAN_STATE_DONE:
        raise RuntimeError(f'unexpected scan state {state}')

    count = endpoint.get('wifi.scan_count')
    return [decode_access_point(endpoint.cmd('wifi.scan_result', i, ValueType.U8)) for i in range(count)]


def print_access_points(access_points):
    if not access_points:
        print('No access points found')
        return
    print(f'{len(access_points)} access point(s) found:')
    print(f'  {"SSID":32}  {"RSSI":>5}  {"Ch":>3}  {"Security":14}  BSSID')
    for ap in sorted(access_points, key=lambda ap: ap.rssi, reverse=True):
        ssid = ap.ssid if ap.ssid else '(hidden)'
        print(f'  {ssid:32}  {ap.rssi:5}  {ap.channel:3}  {ap.auth_name:14}  {ap.bssid_text}')


def main():
    parser = argparse.ArgumentParser(description='Scan for WiFi access points with the camera deck.')
    parser.add_argument('--uri', default=uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7'),
                        help='Crazyflie URI (default: CFLIB_URI or radio://0/80/2M/E7E7E7E7E7)')
    parser.add_argument('--endpoint', default='deck:bcCam', help='endpoint path (default: deck:bcCam)')
    parser.add_argument('--timeout', type=float, default=15.0, help='scan timeout in seconds (default: 15)')
    args = parser.parse_args()

    cflib.crtp.init_drivers()

    with SyncCrazyflie(args.uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        try:
            endpoint = scf.cf.apiservice.endpoint(args.endpoint)
            print('Scanning...')
            access_points = scan(endpoint, args.timeout)
        except (ApiserviceError, TimeoutError, RuntimeError, ValueError) as e:
            print(f'{type(e).__name__}: {e}')
            return
        print_access_points(access_points)


if __name__ == '__main__':
    main()
