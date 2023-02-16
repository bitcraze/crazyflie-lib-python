# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2023 Bitcraze AB
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
Simple example that connects to one crazyflie (check the address at the top
and update it to your crazyflie address) and a combination of high level
and low level commands to make the crazyflie move.

The high level commands (low priority) are used to take off, land and go to a specific location
The low level commands (high priority) are used to make the crazyflie move in a specific direction
The landing command from the high level commander will first need to follow a setpoint priority 
  relaxation before being able to land. 
"""


import time

import cflib.crtp
from cflib.crazyflie import Crazyflie

from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

# URI to the Crazyflie to connect to
uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

def run_sequence(cf):
    commander_high_level = cf.high_level_commander
    commander_low_level = cf.commander
    standard_height = 1.0
    vel_max = 0.5
    
    print('take off')
    commander_high_level.takeoff(standard_height, 2.0)
    time.sleep(3.0)
    print('go forward high level commander')
    commander_high_level.go_to(0.0, 1.0, standard_height, 0.0, 2.0)
    time.sleep(1.0)
    print('take over low level commander, which has higher priority')
    commander_low_level.send_hover_setpoint(vel_max, 0.0, 0.0, standard_height)
    time.sleep(2.0)
    print('second setpoint to make sure that it does not stop')
    commander_low_level.send_hover_setpoint(-vel_max, 0.0, 0.0, standard_height)
    time.sleep(2.0)
    print('Stop on the spot')
    commander_low_level.send_hover_setpoint(0.0, 0.0, 0.0, standard_height)
    time.sleep(1.0)
    print('lower priority of low level commander')
    commander_low_level.send_notify_setpoint_stop()
    time.sleep(0.1)
    print('land again with high level commander')
    commander_high_level.land(0.0, 2.0)
    time.sleep(2)
    commander_high_level.stop()


if __name__ == '__main__':
    cflib.crtp.init_drivers()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        cf = scf.cf
        run_sequence(cf)
