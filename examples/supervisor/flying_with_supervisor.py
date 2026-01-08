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
Simple example showing how to fly the Crazyflie using supervisor state information.
Based on its current state, the Crazyflie will arm (if it can be armed), take
off (if it can fly), and land (if it is flying). Before each action, we call
the supervisor to check if the Crazyflie is crashed, locked or tumbled.
Tested with the Flow deck V2 and the Lighthouse positioning system.
"""
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper


# URI to the Crazyflie to connect to
uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')


def safety_check(sup):
    if sup.is_crashed:
        raise Exception('Crazyflie crashed!')
    if sup.is_locked:
        raise Exception('Crazyflie locked!')
    if sup.is_tumbled:
        raise Exception('Crazyflie tumbled!')


def run_sequence(scf: SyncCrazyflie, sup):
    commander = scf.cf.high_level_commander

    try:
        safety_check(sup)
        if sup.can_be_armed:
            print('The Crazyflie can be armed...arming!')
            safety_check(sup)
            sup.send_arming_request(True)
            time.sleep(1)

        safety_check(sup)
        if sup.can_fly:
            print('The Crazyflie can fly...taking off!')
            commander.takeoff(1.0, 2.0)
            time.sleep(3)

        safety_check(sup)
        if sup.is_flying:
            print('The Crazyflie is flying...landing!')
            commander.land(0.0, 2.0)
            time.sleep(3)

        safety_check(sup)

    except Exception as e:
        print(f'Safety check failed: {e}')


if __name__ == '__main__':
    cflib.crtp.init_drivers()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        time.sleep(1)
        supervisor = scf.cf.supervisor
        time.sleep(1)
        run_sequence(scf, supervisor)
