# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2025 Bitcraze AB
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
Simple script that connects to multiple Crazyflies in sequence and uploads
the lighthouse configuration file. The Crazyflies that successfully received
the file are powered off, while the ones that didn't get it remain powered on.
This could be really helpful if you're dealing with a big swarm of Crazyflies.

Make sure that each Crazyflie has a lighthouse deck attached.
"""
import os
import sys
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.localization import LighthouseConfigWriter
from cflib.utils import uri_helper
from cflib.utils.power_switch import PowerSwitch

file_path = 'lighthouse.yaml'  # Add the path to your .yaml file

# Modify the list of Crazyflies according to your setup
uris = [
    'radio://0/80/2M/E7E7E7E7E7',
    'radio://0/80/2M/E7E7E7E7E8',
    'radio://0/80/2M/E7E7E7E7E9',
    'radio://0/80/2M/E7E7E7E7EA',
    'radio://0/80/2M/E7E7E7E7EB',
    'radio://0/80/2M/E7E7E7E7EC',
]


def write_one(file_name, scf: SyncCrazyflie):
    print(f'Writing to \033[92m{uri}\033[97m...', end='', flush=True)
    writer = LighthouseConfigWriter(scf.cf)
    writer.write_and_store_config_from_file(None, file_name)
    print('Success!')
    time.sleep(1)


if __name__ == '__main__':
    if not os.path.exists(file_path):
        print('Error: file not found!')
        sys.exit(1)

    print(f'Using file {file_path}')

    cflib.crtp.init_drivers()

    for uri in uris:
        try:
            Drone = uri_helper.uri_from_env(default=uri)
            with SyncCrazyflie(Drone, cf=Crazyflie(rw_cache='./cache')) as scf:
                print(f'\033[92m{uri} \033[97mFully connected ', end='', flush=True)
                while scf.is_params_updated() is False:
                    print('.', end='', flush=True)
                    time.sleep(0.1)
                print(f'{scf.is_params_updated()}')
                time.sleep(0.5)
                write_one(file_path, scf)
                ps = PowerSwitch(Drone)
                ps.platform_power_down()
                time.sleep(2)

        except (Exception):
            print(f'Couldnt connect to \033[91m{uri}\033[97m')
            continue
