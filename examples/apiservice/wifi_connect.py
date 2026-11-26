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
Connect the camera deck to a WiFi network.

    python3 wifi_connect.py
    python3 wifi_connect.py --uri usb://0

The URI comes from --uri, or the CFLIB_URI environment variable.

The deck scans for access points, the user picks a network from the list and
enters its password, and the credentials are sent to the deck. The deck then
joins the network, and the script prints the IP settings it got and exits.

The deck stays on the network after the script exits, and rejoins it if it is
lost, until wifi_disconnect.py is run or the deck is powered off. The
credentials are kept in RAM on the deck only.

The WiFi is handled by cf.wifi, which finds the deck with WiFi among the API
Service endpoints of the Crazyflie.
"""
import argparse
import getpass
import logging

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.apiservice import ApiserviceError
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.wifi import WifiAuth
from cflib.crazyflie.wifi import WifiError
from cflib.utils import uri_helper

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 63


def ssid_text(ssid):
    return ssid.decode('utf-8', errors='replace')


def auth_text(auth):
    return auth.name if isinstance(auth, WifiAuth) else f'unknown ({auth})'


def networks(access_points):
    """One access point per SSID, the strongest, without hidden networks.

    The access points are sorted strongest first, so the first one of each
    SSID is kept.
    """
    seen = set()
    result = []
    for ap in access_points:
        if ap.ssid and ap.ssid not in seen:
            seen.add(ap.ssid)
            result.append(ap)
    return result


def print_networks(aps):
    print(f'  {"#":>3}  {"SSID":32}  {"RSSI":>5}  {"Ch":>3}  Security')
    for i, ap in enumerate(aps, start=1):
        print(f'  {i:3}  {ssid_text(ap.ssid):32}  {ap.rssi:5}  {ap.channel:3}  {auth_text(ap.auth)}')


def pick_network(aps):
    """Ask the user for a network in aps, returns None if the user quits"""
    while True:
        answer = input(f'Network to join [1-{len(aps)}, q to quit]: ').strip()
        if answer.lower() == 'q':
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(aps):
            return aps[int(answer) - 1]
        print(f'Enter a number from 1 to {len(aps)}')


def ask_password(ap):
    """Ask for the password of ap, empty for an open network"""
    if ap.auth == WifiAuth.OPEN:
        print(f'{ssid_text(ap.ssid)} is an open network, no password is needed')
        return ''
    while True:
        password = getpass.getpass(f'Password for {ssid_text(ap.ssid)}: ')
        if PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
            return password
        print(f'The password must be {PASSWORD_MIN_LENGTH} to {PASSWORD_MAX_LENGTH} characters')


def main():
    parser = argparse.ArgumentParser(description='Connect the camera deck to a WiFi network.')
    parser.add_argument('--uri', default=uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7'),
                        help='Crazyflie URI (default: CFLIB_URI or radio://0/80/2M/E7E7E7E7E7)')
    parser.add_argument('--scan-timeout', type=float, default=15.0,
                        help='scan timeout in seconds (default: 15)')
    parser.add_argument('--connect-timeout', type=float, default=30.0,
                        help='timeout in seconds to join the network and get an IP address (default: 30)')
    args = parser.parse_args()

    cflib.crtp.init_drivers()

    with SyncCrazyflie(args.uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        wifi = scf.cf.wifi
        try:
            print('Scanning...')
            aps = networks(wifi.scan(timeout=args.scan_timeout))
            if not aps:
                print('No networks found')
                return
            print_networks(aps)

            ap = pick_network(aps)
            if ap is None:
                return
            password = ask_password(ap)

            wifi.set_credentials(ap.ssid, password)
            print(f'Connecting to {ssid_text(ap.ssid)}...')
            wifi.connect(timeout=args.connect_timeout)
            ip_info = wifi.ip_info()
        except (ApiserviceError, WifiError, TimeoutError) as e:
            print(f'{type(e).__name__}: {e}')
            return

        print('Connected')
        print(f'  IP address: {ip_info.ip}')
        print(f'  Netmask:    {ip_info.netmask}')
        print(f'  Gateway:    {ip_info.gateway}')
        print(f'  DNS:        {ip_info.dns}')
        print()
        print('The deck stays on the network, and rejoins it if it is lost, until it is powered off.')
        print('Run wifi_disconnect.py to make it leave the network.')


if __name__ == '__main__':
    main()
