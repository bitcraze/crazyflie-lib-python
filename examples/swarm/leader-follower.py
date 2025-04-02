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
'''
Example of a swarm sharing data and performing a leader-follower scenario
using the motion commander.

The swarm takes off and the drones hover until the follower's local coordinate
system is aligned with the global one. Then, the leader performs its own
trajectory based on commands from the motion commander. The follower is
constantly commanded to keep a defined distance from the leader, meaning that
it is moving towards the leader when their current distance is larger than the
defined one and away from the leader in the opposite scenario.
All movements refer to the local coordinate system of each drone.

This example is intended to work with an absolute positioning system, it has
been tested with the lighthouse positioning system.

This example aims at documenting how to use the collected data to define new
trajectories in real-time. It also indicates how to use the swarm class to
feed the Crazyflies completely different asynchronized trajectories in parallel.
'''
import math
import time

import cflib.crtp
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.positioning.motion_commander import MotionCommander

# Change uris according to your setup
# URIs in a swarm using the same radio must also be on the same channel
URI1 = 'radio://0/80/2M/E7E7E7E7E7'  # Follower
URI2 = 'radio://0/80/2M/E7E7E7E7E8'  # Leader


DEFAULT_HEIGHT = 0.75
DEFAULT_VELOCITY = 0.5
x1 = [0]
y1 = [0]
z1 = [0]
x2 = [0]
y2 = [0]
z2 = [0]
yaw1 = [0]
yaw2 = [0]
d = 0

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


def pos_to_vel(x1, y1, x2, y2, dist):
    '''
    This function takes two points on the x-y plane and outputs
    two components of the velocity vector: one along the x-axis
    and one along the y-axis. The combined vector represents the
    total velocity, pointing from point 1 to point 2, with a
    magnitude equal to the DEFAULT_VELOCITY. These 2 velocity
    vectors are meant to be used by the motion commander.
    The distance between them is taken as an argument because it
    is constanlty calculated by position_callback().
    '''
    if dist == 0:
        Vx = 0
        Vy = 0
    else:
        Vx = DEFAULT_VELOCITY * (x2-x1)/dist
        Vy = DEFAULT_VELOCITY * (y2-y1)/dist
    return Vx, Vy


def position_callback(uri, data):
    global d
    if uri == URI1:  # Follower
        x1.append(data['stateEstimate.x'])
        y1.append(data['stateEstimate.y'])
        z1.append(data['stateEstimate.z'])
        yaw1.append(data['stateEstimate.yaw'])
    elif uri == URI2:  # Leader
        x2.append(data['stateEstimate.x'])
        y2.append(data['stateEstimate.y'])
        z2.append(data['stateEstimate.z'])
        yaw2.append(data['stateEstimate.yaw'])

    d = math.sqrt(pow((x1[-1]-x2[-1]), 2)+pow((y1[-1]-y2[-1]), 2))


def start_position_printing(scf):
    log_conf1 = LogConfig(name='Position', period_in_ms=10)
    log_conf1.add_variable('stateEstimate.x', 'float')
    log_conf1.add_variable('stateEstimate.y', 'float')
    log_conf1.add_variable('stateEstimate.z', 'float')
    log_conf1.add_variable('stateEstimate.yaw', 'float')
    scf.cf.log.add_config(log_conf1)
    log_conf1.data_received_cb.add_callback(lambda _timestamp, data, _logconf: position_callback(scf.cf.link_uri, data))
    log_conf1.start()


def leader_follower(scf):
    r_min = 0.8  # The minimum distance between the 2 drones
    r_max = 1.0  # The maximum distance between the 2 drones
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:

        # The follower turns until it is aligned with the global coordinate system
        while abs(yaw1[-1]) > 2:
            if scf.__dict__['_link_uri'] == URI1:  # Follower
                if yaw1[-1] > 0:
                    mc.start_turn_right(36 if abs(yaw1[-1]) > 15 else 9)
                elif yaw1[-1] < 0:
                    mc.start_turn_left(36 if abs(yaw1[-1]) > 15 else 9)

            elif scf.__dict__['_link_uri'] == URI2:  # Leader
                mc.stop()
            time.sleep(0.005)

        time.sleep(0.5)

        start_time = time.time()
        # Define the flight time after the follower is aligned
        end_time = time.time() + 20

        while time.time() < end_time:

            if scf.__dict__['_link_uri'] == URI1:  # Follower
                if d > r_max:
                    cmd_vel_x, cmd_vel_y = pos_to_vel(x1[-1], y1[-1], x2[-1], y2[-1], d)
                elif d >= r_min and d <= r_max:
                    cmd_vel_x = 0
                    cmd_vel_y = 0
                elif d < r_min:
                    opp_cmd_vel_x, opp_cmd_vel_y = pos_to_vel(x1[-1], y1[-1], x2[-1], y2[-1], d)
                    cmd_vel_x = -opp_cmd_vel_x
                    cmd_vel_y = -opp_cmd_vel_y

                mc.start_linear_motion(cmd_vel_x, cmd_vel_y, 0)

            elif scf.__dict__['_link_uri'] == URI2:  # Leader
                # Define the sequence of the leader
                if time.time() - start_time < 3:
                    mc.start_forward(DEFAULT_VELOCITY)
                elif time.time() - start_time < 6:
                    mc.start_back(DEFAULT_VELOCITY)
                elif time.time() - start_time < 20:
                    mc.start_circle_right(0.9, DEFAULT_VELOCITY)
                else:
                    mc.stop()

            time.sleep(0.005)
        mc.land()


if __name__ == '__main__':
    cflib.crtp.init_drivers()

    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:

        swarm.reset_estimators()

        swarm.parallel_safe(arm)

        print('Waiting for parameters to be downloaded...')
        swarm.parallel_safe(wait_for_param_download)

        time.sleep(1)

        swarm.parallel_safe(start_position_printing)
        time.sleep(0.5)

        swarm.parallel_safe(leader_follower)
        time.sleep(1)
