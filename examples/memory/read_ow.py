# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2014 Bitcraze AB
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
Simple example that connects to a Crazyflie, looks for
1-wire memories and lists its contents.
"""
import logging
import sys
from threading import Event

import cflib.crtp  # noqa
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.mem import MemoryElement
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

update_event = Event()


def read_ow_mems(cf):
    mems = cf.mem.get_mems(MemoryElement.TYPE_1W)
    print(f'Found {len(mems)} 1-wire memories')

    for m in mems:
        update_event.clear()

        print(f'Reading id={m.id}')
        m.update(data_updated_cb)
        success = update_event.wait(timeout=5.0)
        if not success:
            print(f'Mem read time out for memory {m.id}')
            sys.exit(1)


def data_updated_cb(mem):
    print(f'Got id={mem.id}')
    print(f'\tAddr      : {mem.addr}')
    print(f'\tType      : {mem.type}')
    print(f'\tSize      : {mem.size}')
    print(f'\tValid     : {mem.valid}')
    print(f'\tName      : {mem.name}')
    print(f'\tVID       : 0x{mem.vid:02X}')
    print(f'\tPID       : 0x{mem.pid:02X}')
    print(f'\tPins      : 0x{mem.pins:02X}')
    print('\tElements  : ')

    for key, element in mem.elements.items():
        print(f'\t\t{key}={element}')

    update_event.set()


if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        read_ow_mems(scf.cf)
