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
List the API Service endpoints of a Crazyflie, and read or write a path on one.

    python3 apiservice_endpoints.py
        prints the catalog, with readiness and limits
    python3 apiservice_endpoints.py deck:bcCam stream.mjpeg_quality
        reads a path
    python3 apiservice_endpoints.py deck:bcCam stream.mjpeg_quality 80
        writes a path. The value is converted to the type the path has now,
        or to the type given with --type (for example --type u8)

The URI comes from --uri, or the CFLIB_URI environment variable.
"""
import argparse
import logging

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.apiservice import ApiserviceError
from cflib.crazyflie.apiservice import ValueType
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


def print_catalog(apiservice):
    info = apiservice.info()
    if info is None:
        print('This Crazyflie has no API Service bridge (CRTP protocol 14 or later is needed)')
        return
    print(f'{info.count} endpoint(s), {info.max_in_flight} request(s) in flight, '
          f'messages up to {info.max_message} bytes')
    for endpoint in apiservice.endpoints():
        try:
            status = endpoint.status()
            state = 'ready' if status.ready else 'not ready'
            limits = f'max request {status.max_request} B, max response {status.max_response} B'
        except ApiserviceError as e:
            state = 'unknown'
            limits = str(e)
        print(f'  {endpoint.id:3}  {endpoint.path:20}  {state:9}  {limits}')


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


def get_or_set(apiservice, endpoint_path, path, text=None, type_name=None):
    endpoint = apiservice.endpoint(endpoint_path)
    if text is None:
        typed = endpoint.get_typed(path)
        print(f'{endpoint.path} {path} = {typed.value!r} ({_type_name(typed.type)})')
        return

    if type_name is not None:
        value_type = ValueType[type_name.upper()]
    else:
        # Integers need their wire type: read it from the current value
        value_type = endpoint.get_typed(path).type
    endpoint.set(path, parse_value(text, value_type), value_type)
    typed = endpoint.get_typed(path)
    print(f'{endpoint.path} {path} = {typed.value!r} ({_type_name(typed.type)})')


def _type_name(value_type):
    if isinstance(value_type, ValueType):
        return value_type.name.lower()
    return f'type 0x{value_type:02x}'


def main():
    parser = argparse.ArgumentParser(description='List API Service endpoints, and read or write a path on one.')
    parser.add_argument('--uri', default=uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7'),
                        help='Crazyflie URI (default: CFLIB_URI or radio://0/80/2M/E7E7E7E7E7)')
    parser.add_argument('--type', dest='type_name', choices=[t.name.lower() for t in ValueType],
                        help='wire type of the value to write (default: the type the path has now)')
    parser.add_argument('endpoint', nargs='?', help='endpoint path, for example deck:bcCam')
    parser.add_argument('path', nargs='?', help='path to read or write, for example stream.mjpeg_quality')
    parser.add_argument('value', nargs='?', help='value to write')
    args = parser.parse_args()

    if args.endpoint is not None and args.path is None:
        parser.error('give a path to read on the endpoint')

    cflib.crtp.init_drivers()

    with SyncCrazyflie(args.uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        apiservice = scf.cf.apiservice
        try:
            if args.endpoint is None:
                print_catalog(apiservice)
            else:
                get_or_set(apiservice, args.endpoint, args.path, args.value, args.type_name)
        except (ApiserviceError, ValueError, TypeError) as e:
            print(f'{type(e).__name__}: {e}')


if __name__ == '__main__':
    main()
