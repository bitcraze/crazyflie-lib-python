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
Simple "show" example that connects to 8 crazyflies (check the addresses at the top
and update it to your crazyflies addresses) and uses the high level commander with bezier curves
to send trajectories to fly a circle (while the 8 drones are positioned in a square).
To spice it up, the LEDs are changing color - the color move factor defines how fast and in which direction.

This example is intended to work with any positioning system (including LPS).
It aims at documenting how to set the Crazyflie in position control mode
and how to send setpoints using the high level commander.
"""
import sys
import time

import numpy as np

import cflib.crtp
from cflib.crazyflie.high_level_commander import HighLevelCommander
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.mem import CompressedSegment
from cflib.crazyflie.mem import CompressedStart
from cflib.crazyflie.mem import MemoryElement
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncLogger import SyncLogger

URI1 = 'radio://0/60/2M/E7E7E7E710'
URI2 = 'radio://0/60/2M/E7E7E7E711'
URI3 = 'radio://0/60/2M/E7E7E7E712'
URI4 = 'radio://0/60/2M/E7E7E7E713'
URI5 = 'radio://0/60/2M/E7E7E7E714'
URI6 = 'radio://0/60/2M/E7E7E7E715'
URI7 = 'radio://0/60/2M/E7E7E7E716'
URI8 = 'radio://0/60/2M/E7E7E7E717'

# The trajectory to fly
a = 0.55  # where the Beizer curve control point should be https://spencermortensen.com/articles/bezier-circle/
h = 1.0  # [m] how high we should fly
t = 2.0  # seconds per step, one circle has 4 steps
r1 = 1.0  # [m] the radius at which the first half of the drones are
r2 = np.sqrt(2.0)  # [m] the radius at which every second other drone is
loops = 2  # how many loops we should fly
color_move_factor = 3  # magic factor which defines how fast the colors move


def rotate_beizer_node(xl, yl, alpha):
    x_rot = []
    y_rot = []
    for x, y in zip(xl, yl):
        x_rot.append(x*np.cos(alpha) - y*np.sin(alpha))
        y_rot.append(x*np.sin(alpha) + y*np.cos(alpha))
    return x_rot, y_rot


def wait_for_position_estimator(scf):
    print('Waiting for estimator to find position...')

    log_config = LogConfig(name='Kalman Variance', period_in_ms=500)
    log_config.add_variable('kalman.varPX', 'float')
    log_config.add_variable('kalman.varPY', 'float')
    log_config.add_variable('kalman.varPZ', 'float')

    var_y_history = [1000] * 10
    var_x_history = [1000] * 10
    var_z_history = [1000] * 10

    threshold = 0.001

    with SyncLogger(scf, log_config) as logger:
        for log_entry in logger:
            data = log_entry[1]

            var_x_history.append(data['kalman.varPX'])
            var_x_history.pop(0)
            var_y_history.append(data['kalman.varPY'])
            var_y_history.pop(0)
            var_z_history.append(data['kalman.varPZ'])
            var_z_history.pop(0)

            min_x = min(var_x_history)
            max_x = max(var_x_history)
            min_y = min(var_y_history)
            max_y = max(var_y_history)
            min_z = min(var_z_history)
            max_z = max(var_z_history)

            # print("{} {} {}".
            #       format(max_x - min_x, max_y - min_y, max_z - min_z))

            if (max_x - min_x) < threshold and (
                    max_y - min_y) < threshold and (
                    max_z - min_z) < threshold:
                break


def reset_estimator(cf):
    cf.param.set_value('kalman.resetEstimation', '1')
    time.sleep(0.1)
    cf.param.set_value('kalman.resetEstimation', '0')

    wait_for_position_estimator(cf)


def activate_high_level_commander(cf):
    cf.param.set_value('commander.enHighLevel', '1')


def activate_mellinger_controller(cf):
    cf.param.set_value('stabilizer.controller', '2')


def upload_trajectory(cf, trajectory_id, trajectory):
    trajectory_mem = cf.mem.get_mems(MemoryElement.TYPE_TRAJ)[0]

    trajectory_mem.trajectory = trajectory

    upload_result = trajectory_mem.write_data_sync()
    if not upload_result:
        print('Upload failed, aborting!')
        sys.exit(1)
    cf.high_level_commander.define_trajectory(
        trajectory_id,
        0,
        len(trajectory),
        type=HighLevelCommander.TRAJECTORY_TYPE_POLY4D_COMPRESSED)

    total_duration = 0
    # Skip the start element
    for segment in trajectory[1:]:
        total_duration += segment.duration

    return total_duration


def turn_off_leds(scf):
    # Set solid color effect
    scf.cf.param.set_value('ring.effect', '7')
    # Set the RGB values
    scf.cf.param.set_value('ring.solidRed', '0')
    scf.cf.param.set_value('ring.solidGreen', '0')
    scf.cf.param.set_value('ring.solidBlue', '0')


def run_sequence(scf, alpha, r):
    commander = scf.cf.high_level_commander
    trajectory_id = 1
    duration = 4*t
    commander.takeoff(h, 2.0)
    time.sleep(3.0)
    x_start, y_start = rotate_beizer_node([r], [0.0], alpha)
    commander.go_to(x_start[0], y_start[0], h, 0.0, 2.0)
    time.sleep(3.0)
    relative = False
    start_time_leds = time.time()
    for i in range(loops):
        commander.start_trajectory(trajectory_id, 1.0, relative)
        start_time = time.time()
        end_time = start_time + duration
        while True:
            color_angle = alpha + ((time.time() - start_time_leds)/duration)*2.0*np.pi*color_move_factor
            scf.cf.param.set_value('ring.solidRed', np.cos(color_angle)*127 + 127)
            scf.cf.param.set_value('ring.solidGreen', 128 - np.cos(color_angle)*127)
            scf.cf.param.set_value('ring.solidBlue', '0')
            if time.time() > end_time:
                break
            time.sleep(0.2)
    commander.land(0.0, 2.0)
    scf.cf.param.set_value('ring.solidRed', '0')
    scf.cf.param.set_value('ring.solidGreen', '0')
    scf.cf.param.set_value('ring.solidBlue', '0')
    time.sleep(20)  # sleep long enough to be sure to have turned off leds
    commander.stop()


def create_trajectory(alpha, r):
    x_start, y_start = rotate_beizer_node([r], [0.0], alpha)
    beizer_point_1_x, beizer_point_1_y = rotate_beizer_node([r, r*a, 0.0], [r*a, r, r], alpha)
    beizer_point_2_x, beizer_point_2_y = rotate_beizer_node([-r*a, -r, -r], [r, r*a, 0.0], alpha)
    beizer_point_3_x, beizer_point_3_y = rotate_beizer_node([-r, -r*a, 0.0], [-r*a, -r, -r], alpha)
    beizer_point_4_x, beizer_point_4_y = rotate_beizer_node([r*a, r, r], [-r, -r*a, 0.0], alpha)
    trajectory = [
        CompressedStart(x_start[0], y_start[0], h, 0.0),
        CompressedSegment(t, beizer_point_1_x, beizer_point_1_y, [h], []),
        CompressedSegment(t, beizer_point_2_x, beizer_point_2_y, [h], []),
        CompressedSegment(t, beizer_point_3_x, beizer_point_3_y, [h], []),
        CompressedSegment(t, beizer_point_4_x, beizer_point_4_y, [h], []),
    ]
    return trajectory


def upload_trajectories(scf, alpha, r):
    trajectory_id = 1
    trajectory = create_trajectory(alpha, r)
    upload_trajectory(scf.cf, trajectory_id, trajectory)


if __name__ == '__main__':
    cflib.crtp.init_drivers()
    uris = [URI1, URI2, URI3, URI4, URI5, URI6, URI7, URI8]
    # uris = [URI1, URI5]
    position_params = {
        URI1: [0.0, r1],
        URI2: [np.pi/4, r2],
        URI3: [np.pi/2, r1],
        URI4: [np.pi/4*3, r2],
        URI5: [np.pi, r1],
        URI6: [np.pi/4*5, r2],
        URI7: [np.pi/4*6, r1],
        URI8: [np.pi/4*7, r2]}

    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        swarm.parallel_safe(turn_off_leds)
        swarm.parallel_safe(upload_trajectories, args_dict=position_params)
        time.sleep(5)
        swarm.parallel_safe(run_sequence, args_dict=position_params)
