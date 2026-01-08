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
Simple, non-flying example demonstrating how to read the Crazyflie's state
through the supervisor. Hold the Crazyflie in your hand and tilt it upside
down to observe the state changes. Once the tilt exceeds ~90°, the can_fly
state becomes False and the is_tumbled state becomes True.
"""
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.supervisor import SupervisorState
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

logging.basicConfig(level=logging.INFO)

# URI to the Crazyflie to connect to
uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')


if __name__ == '__main__':
    cflib.crtp.init_drivers()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        time.sleep(1)
        supervisor = SupervisorState(scf)
        time.sleep(1)
        try:
            while True:
                print('==============================================================================')
                print(f'Can fly: {supervisor.can_fly}')
                print(f'Is tumbled: {supervisor.is_tumbled}')
                print(f'Bitfield: {supervisor.read_bitfield()}')
                print(f'State list: {supervisor.read_state_list()}')
                print('==============================================================================')
                time.sleep(0.5)

        except KeyboardInterrupt:
            print('Script terminated')
