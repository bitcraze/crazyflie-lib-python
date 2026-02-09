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
Script for flying a swarm of 8 Crazyflies performing a coordinated spiral choreography
resembling a Christmas tree outline in 3D space. Each drone takes off to a different
height, flies in spiraling circular layers, and changes radius as it rises and descends,
forming the visual structure of a cone when viewed from outside.

The script is using the high level commanded and has been tested with 3 Crazyradios 2.0
and the Lighthouse positioning system.
"""
import math
import time

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

uri1 = 'radio://0/30/2M/E7E7E7E701'
uri2 = 'radio://0/30/2M/E7E7E7E702'
uri3 = 'radio://0/30/2M/E7E7E7E703'

uri4 = 'radio://1/55/2M/E7E7E7E704'
uri5 = 'radio://1/55/2M/E7E7E7E705'
uri6 = 'radio://1/55/2M/E7E7E7E706'

uri7 = 'radio://2/70/2M/E7E7E7E707'
uri8 = 'radio://2/70/2M/E7E7E7E708'

uris = [
    uri1,
    uri2,
    uri3,
    uri4,
    uri5,
    uri6,
    uri7,
    uri8,
    # Add more URIs if you want more copters in the swarm
]


def arm(scf: SyncCrazyflie):
    scf.cf.platform.send_arming_request(True)
    time.sleep(1.0)


# center of the spiral
x0 = 0
y0 = 0
z0 = 0.5

x_offset = 0.4  # Vertical distance between 2 layers
z_offset = 0.5  # Radius difference between 2 layers

starting_x = {
    uri1: x0 + x_offset,
    uri2: x0 + 2*x_offset,
    uri3: x0 + 3*x_offset,
    uri4: x0 + 4*x_offset,
    uri5: x0 - x_offset,
    uri6: x0 - 2*x_offset,
    uri7: x0 - 3*x_offset,
    uri8: x0 - 4*x_offset,
}

starting_z = {
    uri1: z0 + 3*z_offset,
    uri2: z0 + 2*z_offset,
    uri3: z0 + z_offset,
    uri4: z0,
    uri5: z0 + 3*z_offset,
    uri6: z0 + 2*z_offset,
    uri7: z0 + z_offset,
    uri8: z0,
}

starting_yaw = {
    uri1: math.pi/2,
    uri2: -math.pi/2,
    uri3: math.pi/2,
    uri4: -math.pi/2,
    uri5: -math.pi/2,
    uri6: math.pi/2,
    uri7: -math.pi/2,
    uri8: math.pi/2,

}

rotate_clockwise = {
    uri1: False,
    uri2: True,
    uri3: False,
    uri4: True,
    uri5: False,
    uri6: True,
    uri7: False,
    uri8: True,
}

takeoff_dur = {
    uri: value / 0.4
    for uri, value in starting_z.items()
}


def x_from_z(z):
    cone_width = 4  # m
    cone_height = 5  # m
    """
    Returns the radius of the tree with a given z.
    """
    return cone_width/2 - (cone_width/cone_height) * z


def run_shared_sequence(scf: SyncCrazyflie):
    circle_duration = 5  # Duration of a full-circle
    commander = scf.cf.high_level_commander
    uri = scf._link_uri

    commander.takeoff(starting_z[uri], takeoff_dur[uri])
    time.sleep(max(takeoff_dur.values())+1)

    # Go to the starting position
    commander.go_to(starting_x[uri], y0, starting_z[uri], starting_yaw[uri], 4)
    time.sleep(5)

    # Full circle with ascent=0
    commander.spiral(2*math.pi, abs(starting_x[uri]), abs(starting_x[uri]),
                     ascent=0, duration_s=circle_duration, sideways=False, clockwise=rotate_clockwise[uri])
    time.sleep(circle_duration+1)

    # Half circle with ascent=-0.5m
    commander.spiral(math.pi, abs(starting_x[uri]), x_from_z(starting_z[uri]-0.5*z_offset),
                     ascent=-0.5*z_offset, duration_s=0.5*circle_duration, sideways=False,
                     clockwise=rotate_clockwise[uri])
    time.sleep(0.5*circle_duration+0.5)

    # Full circle with ascent=+1.0m
    commander.spiral(2*math.pi, x_from_z(starting_z[uri]-0.5*z_offset), x_from_z(starting_z[uri]+0.5*z_offset),
                     ascent=z_offset, duration_s=circle_duration, sideways=False,
                     clockwise=rotate_clockwise[uri])
    time.sleep(circle_duration+1)

    # Half circle with ascent=-0.5m
    commander.spiral(math.pi, x_from_z(starting_z[uri]+0.5*z_offset), x_from_z(starting_z[uri]),
                     ascent=-0.5*z_offset, duration_s=0.5*circle_duration, sideways=False,
                     clockwise=rotate_clockwise[uri])
    time.sleep(0.5*circle_duration+1)

    commander.land(0, takeoff_dur[uri])
    time.sleep(max(takeoff_dur.values())+3)


if __name__ == '__main__':
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        # swarm.reset_estimators()
        time.sleep(0.5)
        print('arming...')
        swarm.parallel_safe(arm)
        print('starting sequence...')
        swarm.parallel_safe(run_shared_sequence)
        time.sleep(1)
