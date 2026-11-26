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
Make the camera deck leave its WiFi network.

    python3 wifi_disconnect.py
    python3 wifi_disconnect.py --uri usb://0

The URI comes from --uri, or the CFLIB_URI environment variable.

After this the deck stops rejoining the network. The credentials stay on the
deck, so the network can be joined again with cf.wifi.connect(), until the
deck is powered off. wifi_connect.py joins a network.
"""
import argparse
import logging

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.apiservice import ApiserviceError
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.wifi import WifiError
from cflib.utils import uri_helper

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


def main():
    parser = argparse.ArgumentParser(description='Make the camera deck leave its WiFi network.')
    parser.add_argument('--uri', default=uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7'),
                        help='Crazyflie URI (default: CFLIB_URI or radio://0/80/2M/E7E7E7E7E7)')
    args = parser.parse_args()

    cflib.crtp.init_drivers()

    with SyncCrazyflie(args.uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        wifi = scf.cf.wifi
        try:
            wifi.disconnect()
            state = wifi.state()
        except (ApiserviceError, WifiError) as e:
            print(f'{type(e).__name__}: {e}')
            return
        state_text = state.name if hasattr(state, 'name') else f'unknown ({state})'
        print(f'Disconnected, WiFi state: {state_text}')


if __name__ == '__main__':
    main()
