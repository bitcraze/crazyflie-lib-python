# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2017-2018 Bitcraze AB
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
Simple example of an asynchronized swarm choreography using the motion
commander.

The swarm takes off and flies an asynchronous choreography before landing.
All movements are relative to the starting position.
During the flight, the position of each Crazyflie is printed.

This example is intended to work with any kind  of location system, it has
been tested with the flow deck v2 and the lighthouse positioning system.
Not using an absolute positioning system makes every Crazyflie start its
positioning printing with (0,0,0) as its initial position.

This example aims at documenting how to use the motion commander together
with the Swarm class to achieve asynchronized sequences.
"""
import time

import cflib.crtp
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.positioning.motion_commander import MotionCommander

# Change uris according to your setup
# URIs in a swarm using the same radio must also be on the same channel
URI1 = 'radio://0/80/2M/E7E7E7E7E7'
URI2 = 'radio://0/80/2M/E7E7E7E7E8'

DEFAULT_HEIGHT = 0.5
DEFAULT_VELOCITY = 0.2
pos1 = [0, 0, 0]
pos2 = [0, 0, 0]

# List of URIs
uris = {
    URI1,
    URI2,
}


def wait_for_param_download(scf):
    while not scf.cf.param.is_updated:
        time.sleep(1.0)
    print('Parameters downloaded for', scf.cf.link_uri)


def arm(scf):
    scf.cf.platform.send_arming_request(True)
    time.sleep(1.0)


def position_callback(uri, data):
    if uri == URI1:
        pos1[0] = data['stateEstimate.x']
        pos1[1] = data['stateEstimate.y']
        pos1[2] = data['stateEstimate.z']
        print(f'Uri1 position: x={pos1[0]}, y={pos1[1]}, z={pos1[2]}')
    elif uri == URI2:
        pos2[0] = data['stateEstimate.x']
        pos2[1] = data['stateEstimate.y']
        pos2[2] = data['stateEstimate.z']
        print(f'Uri2 position: x={pos2[0]}, y={pos2[1]}, z={pos2[2]}')


def start_position_printing(scf):
    log_conf1 = LogConfig(name='Position', period_in_ms=500)
    log_conf1.add_variable('stateEstimate.x', 'float')
    log_conf1.add_variable('stateEstimate.y', 'float')
    log_conf1.add_variable('stateEstimate.z', 'float')
    scf.cf.log.add_config(log_conf1)
    log_conf1.data_received_cb.add_callback(lambda _timestamp, data, _logconf: position_callback(scf.cf.link_uri, data))
    log_conf1.start()


def async_flight(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(1)

        start_time = time.time()
        end_time = time.time() + 12

        while time.time() < end_time:

            if scf.__dict__['_link_uri'] == URI1:
                if time.time() - start_time < 5:
                    mc.start_up(DEFAULT_VELOCITY)
                elif time.time() - start_time < 7:
                    mc.stop()
                elif time.time() - start_time < 12:
                    mc.start_down(DEFAULT_VELOCITY)
                else:
                    mc.stop()

            elif scf.__dict__['_link_uri'] == URI2:
                if time.time() - start_time < 2:
                    mc.start_left(DEFAULT_VELOCITY)
                elif time.time() - start_time < 4:
                    mc.start_right(DEFAULT_VELOCITY)
                elif time.time() - start_time < 6:
                    mc.start_left(DEFAULT_VELOCITY)
                elif time.time() - start_time < 8:
                    mc.start_right(DEFAULT_VELOCITY)
                elif time.time() - start_time < 10:
                    mc.start_left(DEFAULT_VELOCITY)
                elif time.time() - start_time < 12:
                    mc.start_right(DEFAULT_VELOCITY)
                else:
                    mc.stop()

            time.sleep(0.01)
        mc.land()


if __name__ == '__main__':
    # logging.basicConfig(level=logging.DEBUG)
    cflib.crtp.init_drivers()

    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:

        swarm.reset_estimators()

        print('Waiting for parameters to be downloaded...')
        swarm.parallel_safe(wait_for_param_download)

        time.sleep(1)

        swarm.parallel_safe(start_position_printing)
        time.sleep(0.1)

        swarm.parallel_safe(arm)
        time.sleep(0.5)

        swarm.parallel_safe(async_flight)
        time.sleep(1)
