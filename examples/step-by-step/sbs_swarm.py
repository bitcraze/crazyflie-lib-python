# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2022 Bitcraze AB
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
import time

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie


def activate_led_bit_mask(scf: SyncCrazyflie):
    scf.cf.param.set_value('led.bitmask', 255)


def deactivate_led_bit_mask(scf: SyncCrazyflie):
    scf.cf.param.set_value('led.bitmask', 0)


def light_check(scf: SyncCrazyflie):
    activate_led_bit_mask(scf)
    time.sleep(2)
    deactivate_led_bit_mask(scf)
    time.sleep(2)


def take_off(scf: SyncCrazyflie):
    commander = scf.cf.high_level_commander

    commander.takeoff(1.0, 2.0)
    time.sleep(3)


def land(scf: SyncCrazyflie):
    commander = scf.cf.high_level_commander

    commander.land(0.0, 2.0)
    time.sleep(2)

    commander.stop()


def run_square_sequence(scf: SyncCrazyflie):
    box_size = 1.0
    flight_time = 3.0

    commander = scf.cf.high_level_commander

    commander.go_to(box_size, 0, 0, 0, flight_time, relative=True)
    time.sleep(flight_time)

    commander.go_to(0, box_size, 0, 0, flight_time, relative=True)
    time.sleep(flight_time)

    commander.go_to(-box_size, 0, 0, 0, flight_time, relative=True)
    time.sleep(flight_time)

    commander.go_to(0, -box_size, 0, 0, flight_time, relative=True)
    time.sleep(flight_time)


uris = [
    'radio://0/20/2M/E7E7E7E701',
    'radio://0/20/2M/E7E7E7E702',
    'radio://0/20/2M/E7E7E7E703',
    'radio://0/20/2M/E7E7E7E704',
    # Add more URIs if you want more copters in the swarm
]

# The layout of the positions (1m apart from each other):
#   <------ 1 m ----->
#   0                1
#          ^              ^
#          |Y             |
#          |              |
#          +------> X    1 m
#                         |
#                         |
#   3               2     .


h = 0.0  # remain constant height similar to take off height
x0, y0 = +0.5, +0.5
x1, y1 = -0.5, -0.5

#    x   y   z  time
sequence0 = [
    (x1, y0, h, 3.0),
    (x0, y1, h, 3.0),
    (x0,  0, h, 3.0),
]

sequence1 = [
    (x0, y0, h, 3.0),
    (x1, y1, h, 3.0),
    (.0, y1, h, 3.0),
]

sequence2 = [
    (x0, y1, h, 3.0),
    (x1, y0, h, 3.0),
    (x1,  0, h, 3.0),
]

sequence3 = [
    (x1, y1, h, 3.0),
    (x0, y0, h, 3.0),
    (.0, y0, h, 3.0),
]

seq_args = {
    uris[0]: [sequence0],
    uris[1]: [sequence1],
    uris[2]: [sequence2],
    uris[3]: [sequence3],
}


def run_sequence(scf: SyncCrazyflie, sequence):
    cf = scf.cf

    for arguments in sequence:
        commander = scf.cf.high_level_commander

        x, y, z = arguments[0], arguments[1], arguments[2]
        duration = arguments[3]

        print('Setting position {} to cf {}'.format((x, y, z), cf.link_uri))
        commander.go_to(x, y, z, 0, duration, relative=True)
        time.sleep(duration)


if __name__ == '__main__':
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        print('Connected to  Crazyflies')
        swarm.parallel_safe(light_check)
        print('Light check done')

        swarm.reset_estimators()
        print('Estimators have been reset')

        swarm.parallel_safe(take_off)
        # swarm.parallel_safe(run_square_sequence)
        swarm.parallel_safe(run_sequence, args_dict=seq_args)
        swarm.parallel_safe(land)
