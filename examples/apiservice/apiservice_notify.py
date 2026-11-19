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
Print the changes an API Service endpoint reports, until Ctrl-C.

    python3 apiservice_notify.py
        prints the changes of deck:bcCam
    python3 apiservice_notify.py deck:bcCam --set stream.max_mjpeg_quality 60
        also writes a path once subscribed, to show the changes it causes.
        The value is converted to the type the path has now, or to the type
        given with --type (for example --type u8)

The URI comes from --uri, or the CFLIB_URI environment variable.
"""
import argparse
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.apiservice import ApiserviceError
from cflib.crazyflie.apiservice import CrazyflieApiserviceError
from cflib.crazyflie.apiservice import FirmwareErrno
from cflib.crazyflie.apiservice import ValueType
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


def on_change(path, value):
    # Runs on cflib's incoming-packet thread: print only, never block here
    print(f'  {path} = {value!r}')


def on_lost(dropped):
    # The changes printed so far may miss some: a client mirroring values
    # would read them again here, from another thread
    print(f'  {dropped} change(s) lost')


def parse_value(text, value_type):
    """Convert a command-line string to a value of the given type"""
    if value_type == ValueType.NULL:
        return None
    if value_type == ValueType.BOOL:
        if text.lower() in ('1', 'true', 'on', 'yes'):
            return True
        if text.lower() in ('0', 'false', 'off', 'no'):
            return False
        raise ValueError(f'{text!r} is not a bool')
    if value_type == ValueType.STRING:
        return text
    if value_type == ValueType.BYTES:
        return bytes.fromhex(text)
    if value_type == ValueType.IPV4:
        return text
    # Integer types
    return int(text, 0)


def set_path(endpoint, path, text, type_name):
    if type_name is not None:
        value_type = ValueType[type_name.upper()]
    else:
        # Integers need their wire type: read it from the current value
        value_type = endpoint.get_typed(path).type
    print(f'Setting {path} to {text}')
    endpoint.set(path, parse_value(text, value_type), value_type)


def main():
    parser = argparse.ArgumentParser(description='Print the changes an API Service endpoint reports.')
    parser.add_argument('--uri', default=uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7'),
                        help='Crazyflie URI (default: CFLIB_URI or radio://0/80/2M/E7E7E7E7E7)')
    parser.add_argument('--set', nargs=2, metavar=('PATH', 'VALUE'),
                        help='path to write once subscribed, for example stream.max_mjpeg_quality 60')
    parser.add_argument('--type', dest='type_name', choices=[t.name.lower() for t in ValueType],
                        help='wire type of the value to write (default: the type the path has now)')
    parser.add_argument('endpoint', nargs='?', default='deck:bcCam',
                        help='endpoint path (default: deck:bcCam)')
    args = parser.parse_args()

    cflib.crtp.init_drivers()

    with SyncCrazyflie(args.uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        try:
            endpoint = scf.cf.apiservice.endpoint(args.endpoint)

            # Register the callbacks first, then turn forwarding on
            endpoint.notified.add_callback(on_change)
            endpoint.notify_lost.add_callback(on_lost)
            endpoint.set_notify(True)
            print(f'Changes of {endpoint.path} (Ctrl-C to stop):')
        except CrazyflieApiserviceError as e:
            if e.errno == FirmwareErrno.ENOSYS:
                print('This Crazyflie firmware cannot forward API Service notifications')
            else:
                print(f'{type(e).__name__}: {e}')
            return
        except (ApiserviceError, ValueError, TypeError) as e:
            print(f'{type(e).__name__}: {e}')
            return

        if args.set is not None:
            try:
                set_path(endpoint, args.set[0], args.set[1], args.type_name)
            except (ApiserviceError, ValueError, TypeError) as e:
                print(f'{type(e).__name__}: {e}')

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
