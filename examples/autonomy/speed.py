# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2018 Bitcraze AB
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
and update it to your crazyflie address) and uses the high level commander
to send setpoints and trajectory to fly a figure 8.

This example is intended to work with any positioning system (including LPS).
It aims at documenting how to set the Crazyflie in position control mode
and how to send setpoints using the high level commander.
"""
import time

import numpy as np

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.utils import uri_helper

# URI to the Crazyflie to connect to
uri = uri_helper.uri_from_env(default='radio://0/88/2M/F00D2BEFED')

# The trajectory to fly
# See https://github.com/whoenig/uav_trajectories for a tool to generate


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

            if (
                (max_x - min_x) < threshold
                and (max_y - min_y) < threshold
                and (max_z - min_z) < threshold
            ):
                break


def reset_estimator(cf):
    cf.param.set_value('kalman.resetEstimation', '1')
    time.sleep(0.1)
    cf.param.set_value('kalman.resetEstimation', '0')

    wait_for_position_estimator(cf)


def activate_mellinger_controller(cf):
    cf.param.set_value('stabilizer.controller', '2')


def calculate_distance(p1, p2):
    return np.sqrt(np.sum((p2 - p1) ** 2))


def calculate_spiral_length(r0, rf, ascent, angle):
    average_radius = (r0 + rf) / 2
    circular_length = angle * average_radius
    return circular_length + abs(ascent)


def run_native_sequence(cf):
    commander = cf.high_level_commander

    TIME_SCALE = 1.
    DESIRED_SPEED = 2.

    GATE_LOCATIONS = [
        np.array([-1.28, -1.6, 1.06]),  # Gate 1
        np.array([-3.48, 0.14, 1.45]),  # Gate 2
        np.array([-1.76, 1.77, 1.76]),  # Gate 3
        np.array([0.21, 0.33, 1.33]),  # Gate 4
    ]
    PAD_LOCATION = np.array([-1.64, 0.20, 0])

    # Take off and hover for a bit
    commander.takeoff(1.0, 2.0)
    time.sleep(3.0)

    # center above pad to ensure the trajectory starts at the same point
    commander.go_to(
        x=PAD_LOCATION[0],
        y=0,
        z=1.0,
        yaw=0,
        duration_s=1.0 * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(1.0 * TIME_SCALE)

    commander.go_to(
        x=0.3, y=0, z=0, yaw=0, duration_s=0.6 * TIME_SCALE, relative=True, linear=True
    )
    time.sleep(0.6 * TIME_SCALE)

    """ FIRST GATE """
    # -1.28, -1.5, 1.09
    r0 = abs(GATE_LOCATIONS[0][1]) / 2.0
    rf = abs(GATE_LOCATIONS[0][1]) / 2.0
    ascent = 0.00
    angle = np.pi
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED * 1.5
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=True,
    )
    time.sleep(duration * TIME_SCALE)

    current_position = GATE_LOCATIONS[0]
    target_position = np.array([current_position[0] - 0.5, current_position[1], current_position[2]])
    duration = calculate_distance(current_position, target_position) / DESIRED_SPEED
    commander.go_to(
        x=target_position[0],
        y=target_position[1],
        z=target_position[2],
        yaw=np.pi,
        duration_s=duration * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(duration * TIME_SCALE)

    """ SECOND GATE """
    # Spiral to Gate 2
    r0 = abs(GATE_LOCATIONS[1][1] - target_position[1])
    rf = abs(GATE_LOCATIONS[1][0] - target_position[0])
    ascent = GATE_LOCATIONS[1][2] - target_position[2]
    angle = np.pi / 2
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=True,
    )
    time.sleep(duration * TIME_SCALE)

    current_position = GATE_LOCATIONS[1]
    target_position = np.array([current_position[0], current_position[1] + 0.5, current_position[2]])
    duration = calculate_distance(current_position, target_position) / DESIRED_SPEED
    commander.go_to(
        x=target_position[0],
        y=target_position[1],
        z=target_position[2],
        yaw=np.pi / 2,
        duration_s=duration * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(duration * TIME_SCALE)

    """ THIRD GATE """
    # Spiral to Gate 3
    r0 = abs(GATE_LOCATIONS[2][0] - target_position[0])
    rf = abs(GATE_LOCATIONS[2][1] - target_position[1])
    ascent = GATE_LOCATIONS[2][2] - target_position[2]
    angle = np.pi / 2
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=True,
    )
    time.sleep(duration * TIME_SCALE)

    current_position = GATE_LOCATIONS[2]
    target_position = np.array([current_position[0] + 0.5, current_position[1], current_position[2]])
    duration = calculate_distance(current_position, target_position) / DESIRED_SPEED
    commander.go_to(
        x=target_position[0],
        y=target_position[1],
        z=target_position[2],
        yaw=0,
        duration_s=duration * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(duration * TIME_SCALE)

    """ FOURTH GATE """
    # Spiral to Gate 4
    r0 = abs(GATE_LOCATIONS[3][1] - target_position[1])
    rf = abs(GATE_LOCATIONS[3][0] - target_position[0])
    ascent = GATE_LOCATIONS[3][2] - target_position[2]
    angle = np.pi / 2
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=True,
    )
    time.sleep(duration * TIME_SCALE)

    current_position = GATE_LOCATIONS[3]
    target_position = np.array([current_position[0], current_position[1] - 0.5, current_position[2]])
    duration = calculate_distance(current_position, target_position) / DESIRED_SPEED
    commander.go_to(
        x=target_position[0],
        y=target_position[1],
        z=target_position[2],
        yaw=-np.pi / 2,
        duration_s=duration * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(duration * TIME_SCALE)

    """ AGAIN GATE 1 """
    # -1.28, -1.5, 1.09
    r0 = abs(GATE_LOCATIONS[0][0] - target_position[0])
    rf = abs(GATE_LOCATIONS[0][1] - target_position[1])
    ascent = GATE_LOCATIONS[0][2] - target_position[2]
    angle = np.pi / 2
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration,
        clockwise=True,
    )
    time.sleep(duration * TIME_SCALE)

    current_position = GATE_LOCATIONS[0]
    target_position = np.array([current_position[0]-0.3, current_position[1], current_position[2]])
    duration = calculate_distance(current_position, target_position) / DESIRED_SPEED * 3
    straight_part_duration = duration
    commander.go_to(
        x=target_position[0],
        y=target_position[1],
        z=target_position[2],
        yaw=np.pi,
        duration_s=duration * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(duration * TIME_SCALE)

    # spiral further down
    r0 = 0.5
    rf = 0.5
    ascent = -0.5
    angle = np.pi
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length * 1.5 / DESIRED_SPEED
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=True,
    )
    time.sleep(duration * TIME_SCALE)

    commander.go_to(
        x=target_position[0] + 0.6,
        y=target_position[1] + 1.,
        z=target_position[2] - 0.5,
        yaw=0,
        duration_s=straight_part_duration * TIME_SCALE * 3,
        relative=False,
        linear=True,
    )
    time.sleep(straight_part_duration * TIME_SCALE * 3)

    # spiral back up through the gate
    r0 = 0.5
    rf = 0.5
    ascent = 0.5
    angle = np.pi
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length * 1.5 / DESIRED_SPEED
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=True,
    )
    time.sleep(duration * TIME_SCALE)

    # # position right through the gate
    # current_position = GATE_LOCATIONS[0]
    # target_position = np.array([current_position[0]-0.5, current_position[1], current_position[2]])
    # duration = calculate_distance(current_position, target_position) / DESIRED_SPEED
    # commander.go_to(
    #     x=target_position[0],
    #     y=target_position[1],
    #     z=target_position[2],
    #     yaw=np.pi,
    #     duration_s=duration * TIME_SCALE,
    #     relative=False,
    #     linear=True,
    # )
    # time.sleep(duration * TIME_SCALE)

    """
    START FIGURE 8
    """

    thickness = 0.5

    current_position = GATE_LOCATIONS[0]
    target_position = np.array([current_position[0] - thickness / 2, current_position[1], current_position[2]])
    duration = calculate_distance(current_position, target_position) / DESIRED_SPEED * 2
    print(current_position, target_position, duration)
    commander.go_to(
        x=target_position[0],
        y=target_position[1],
        z=target_position[2],
        yaw=np.pi,
        duration_s=duration * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(duration * TIME_SCALE)

    delta_x = abs(GATE_LOCATIONS[2][0] - GATE_LOCATIONS[0][0])/3.
    delta_y = abs(GATE_LOCATIONS[2][1] - GATE_LOCATIONS[0][1])
    delta_z = abs(GATE_LOCATIONS[2][2] - GATE_LOCATIONS[0][2])

    # spiral to midpoint
    r0 = delta_y/4
    rf = delta_y/4
    ascent = delta_z/2
    angle = np.pi
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=True,
    )
    time.sleep(duration * TIME_SCALE)

    # straight mid part
    current_position = np.array([GATE_LOCATIONS[0][0] - thickness/2, GATE_LOCATIONS[2]
                                [1] - delta_y/2, GATE_LOCATIONS[2][2] - delta_z/2])
    target_position = np.array([current_position[0] + thickness + delta_x, current_position[1], current_position[2]])
    duration = calculate_distance(current_position, target_position) / DESIRED_SPEED
    print(current_position, target_position, duration)
    commander.go_to(
        x=target_position[0],
        y=target_position[1],
        z=target_position[2],
        yaw=0,
        duration_s=duration * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(duration * TIME_SCALE)

    # spiral to gate 3
    r0 = delta_y/4
    rf = delta_y/4
    ascent = delta_z/2
    angle = np.pi
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    # straight part through gate 3
    current_position = GATE_LOCATIONS[0] + np.array([thickness/2 + delta_x, delta_y, delta_z])
    target_position = np.array([current_position[0] - thickness, current_position[1], current_position[2]])
    # current_position = np.array([GATE_LOCATIONS[2][0] + thickness/2, GATE_LOCATIONS[2][1], GATE_LOCATIONS[2][2]])
    # target_position = np.array([current_position[0] - thickness, current_position[1], current_position[2]])
    duration = calculate_distance(current_position, target_position) / DESIRED_SPEED
    print(current_position, target_position, duration)
    commander.go_to(
        x=target_position[0],
        y=target_position[1],
        z=target_position[2],
        yaw=np.pi,
        duration_s=duration * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(duration * TIME_SCALE)

    # spiral to middle
    r0 = delta_y/4
    rf = delta_y/4
    ascent = -delta_z/2
    angle = np.pi
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    # another straight middle part
    current_position = np.array([GATE_LOCATIONS[0][0] - thickness/2 + delta_x,
                                GATE_LOCATIONS[0][1] + delta_y/2, GATE_LOCATIONS[0][2] + delta_z/2])
    target_position = np.array([current_position[0] + thickness, current_position[1], current_position[2]])
    duration = calculate_distance(current_position, target_position) / DESIRED_SPEED
    commander.go_to(
        x=target_position[0],
        y=target_position[1],
        z=target_position[2],
        yaw=0,
        duration_s=duration * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(duration * TIME_SCALE)

    # spiral to gate 0 again
    r0 = delta_y/4
    rf = delta_y/4
    ascent = -delta_z/2
    angle = np.pi
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=True,
    )
    time.sleep(duration * TIME_SCALE)

    # straight part to gate 0
    current_position = np.array([GATE_LOCATIONS[0][0] + thickness/2, GATE_LOCATIONS[0][1], GATE_LOCATIONS[0][2]])
    target_position = np.array([current_position[0] - thickness, current_position[1], current_position[2]])
    duration = calculate_distance(current_position, target_position) / DESIRED_SPEED
    commander.go_to(
        x=target_position[0],
        y=target_position[1],
        z=target_position[2],
        yaw=np.pi,
        duration_s=duration * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(duration * TIME_SCALE)

    # lets head to gate 4, so we go to y of

    # quick 180
    delta_y = abs(GATE_LOCATIONS[3][1] - GATE_LOCATIONS[0][1])
    delta_z = abs(GATE_LOCATIONS[3][2] - GATE_LOCATIONS[0][2])
    r0 = delta_y/4
    rf = delta_y/4
    ascent = 0
    angle = np.pi
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED * 1.3
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=True,
    )
    time.sleep(duration * TIME_SCALE)

    # straight part to gate 2
    current_position = GATE_LOCATIONS[0] + np.array([-thickness/2, delta_y/2, 0])
    target_position = GATE_LOCATIONS[3] + np.array([-delta_y/2, -delta_y/2, -delta_z/2])
    duration = calculate_distance(current_position, target_position) / DESIRED_SPEED * 1.1
    commander.go_to(
        x=target_position[0],
        y=target_position[1],
        z=target_position[2],
        yaw=0,
        duration_s=duration * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(duration * TIME_SCALE)

    # spiral to gate 4
    r0 = delta_y/2
    rf = delta_y/2
    ascent = delta_z/2
    angle = np.pi/2
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED * 1.3
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    # straight part through gate 4
    current_position = GATE_LOCATIONS[3]
    target_position = GATE_LOCATIONS[3] + np.array([0, thickness/2, 0])
    duration = calculate_distance(current_position, target_position) / DESIRED_SPEED * 3
    commander.go_to(
        x=target_position[0],
        y=target_position[1],
        z=target_position[2],
        yaw=np.pi/2,
        duration_s=duration * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(duration * TIME_SCALE)

    # spiral around star 1/2
    STAR_POSITION = np.array([-1.5, 0.12, 2.3])
    delta_x = abs(STAR_POSITION[0] - GATE_LOCATIONS[3][0])
    delta_y = abs(STAR_POSITION[1] - GATE_LOCATIONS[3][1])
    delta_z = abs(STAR_POSITION[2] - GATE_LOCATIONS[3][2])

    star_thickness_y = 1.8
    star_thickness_x = 2.

    r0 = (delta_x + star_thickness_x/2)/2
    rf = (delta_y + star_thickness_y/2)/2
    print('rf', rf)
    ascent = delta_z/2
    angle = np.pi/2
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED * 1.1
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    # get into spiral around star 2/2
    r0 = (delta_y + star_thickness_y/2 + thickness/2)/2
    print('r0', r0)
    rf = (delta_x + star_thickness_x/2)/2
    ascent = delta_z/2
    angle = np.pi/2
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED * 1.1
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    # circle around star 1/3
    r0 = star_thickness_x/2
    rf = star_thickness_y/2
    ascent = 0
    angle = np.pi/2
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    # circle around star 2/3
    r0 = star_thickness_y/2
    rf = star_thickness_x/2
    ascent = 0
    angle = np.pi/2
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    # circle around star 3/3
    r0 = star_thickness_x/2
    rf = star_thickness_y/2
    ascent = 0
    angle = np.pi/2
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    # # go straight for a tiny bit
    # current_position = STAR_POSITION + np.array([0, star_thickness_y/2, 0])
    # target_position = STAR_POSITION + np.array([-star_thickness_x/2, star_thickness_y/2, 0])
    # duration = calculate_distance(current_position, target_position) / DESIRED_SPEED * 1.1
    # commander.go_to(
    #     x=target_position[0],
    #     y=target_position[1],
    #     z=target_position[2],
    #     yaw=np.pi/2,
    #     duration_s=duration * TIME_SCALE,
    #     relative=False,
    #     linear=True,
    # )

    # spiral to gate 2
    delta_x = abs(GATE_LOCATIONS[1][0] - STAR_POSITION[0])
    delta_y = abs(GATE_LOCATIONS[1][1] - STAR_POSITION[1] - star_thickness_y/4)
    delta_z = abs(GATE_LOCATIONS[1][2] - STAR_POSITION[2])

    r0 = delta_y
    rf = delta_x
    ascent = -delta_z
    angle = np.pi/2
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED * 1.3
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    # straight part through gate 2
    current_position = GATE_LOCATIONS[1] + np.array([0, thickness/2, 0])
    target_position = GATE_LOCATIONS[1] - np.array([0, thickness/2, 0])
    duration = calculate_distance(current_position, target_position) / DESIRED_SPEED * 5
    print(current_position, target_position, duration)
    commander.go_to(
        x=target_position[0],
        y=target_position[1],
        z=target_position[2],
        yaw=-np.pi/2,
        duration_s=duration * TIME_SCALE,
        relative=False,
        linear=True,
    )
    time.sleep(duration * TIME_SCALE)

    # spiral back up to star
    delta_x = abs(STAR_POSITION[0] - GATE_LOCATIONS[1][0])
    delta_y = abs(STAR_POSITION[1] - GATE_LOCATIONS[1][1])
    delta_z = abs(STAR_POSITION[2] - GATE_LOCATIONS[1][2])

    r0 = delta_x
    rf = delta_y + star_thickness_y/3
    ascent = delta_z
    angle = np.pi/2
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED * 1.3
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    # spiral down in parts (because we are limited to 2pi)
    r0 = star_thickness_y/2
    rf = star_thickness_y/3
    ascent = -0.5
    angle = 2*np.pi
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED * 1.6
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    r0 = star_thickness_y/3
    rf = star_thickness_y/4
    ascent = -0.5
    angle = 2*np.pi
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED * 1.6
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    r0 = star_thickness_y/4
    rf = star_thickness_y/5
    ascent = -0.5
    angle = 2*np.pi
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED * 1.6
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    r0 = star_thickness_y/5
    rf = star_thickness_y/6
    ascent = -0.5
    angle = 2*np.pi
    spiral_length = calculate_spiral_length(r0, rf, ascent, angle)
    duration = spiral_length / DESIRED_SPEED * 1.6
    commander.spiral(
        angle=angle,
        r0=r0,
        rF=rf,
        ascent=ascent,
        duration_s=duration * TIME_SCALE,
        clockwise=False,
    )
    time.sleep(duration * TIME_SCALE)

    cf.high_level_commander.go_to(0, 0, 0, 0, 3., relative=True, linear=True)
    time.sleep(3)

    # return
    cf.high_level_commander.go_to(-1.63, 0.24, 0.3, 0, 5.0)
    time.sleep(5)
    commander.land(0.0, 2.0)
    time.sleep(2)
    commander.stop()


if __name__ == '__main__':
    cflib.crtp.init_drivers()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        cf = scf.cf
        cf.platform.send_arming_request(True)
        time.sleep(10)

        activate_mellinger_controller(cf)
        reset_estimator(cf)
        run_native_sequence(cf)
        # clear_trajectory(cf)
        # trajectory_id = 1
        # offset = 0
        # duration0, offset = upload_trajectory(cf, trajectory_id, trajectory0, offset)
        # print('The sequence is {:.1f} seconds long'.format(duration0))
        # trajectory_id += 1
        # duration1 = 0
        # print(offset)
        # duration1, offset = upload_trajectory(cf, trajectory_id, trajectory1, offset)
        # run_sequence(cf, trajectory_id, duration0, duration1)


# def clear_trajectory(cf):
#     trajectory_mem = cf.mem.get_mems(MemoryElement.TYPE_TRAJ)[0]
#     # print(trajectory_mem.trajectory)
#     trajectory_mem.trajectory = []
#     upload_result = trajectory_mem.write_data_sync()


# def upload_trajectory(cf, trajectory_id, trajectory, next_offset):
#     trajectory_mem = cf.mem.get_mems(MemoryElement.TYPE_TRAJ)[0]
#     # print(trajectory_mem.trajectory)
#     # trajectory_mem.trajectory = []

#     total_duration = 0
#     for row in trajectory:
#         duration = row[0]
#         x = Poly4D.Poly(row[1:9])
#         y = Poly4D.Poly(row[9:17])
#         z = Poly4D.Poly(row[17:25])
#         yaw = Poly4D.Poly(row[25:33])
#         trajectory_mem.trajectory.append(Poly4D(duration, x, y, z, yaw))
#         total_duration += duration

#     upload_result = trajectory_mem.write_data_sync()
#     if not upload_result:
#         print("Upload failed, aborting!")
#         sys.exit(1)
#     cf.high_level_commander.define_trajectory(
#         trajectory_id, next_offset, len(trajectory_mem.trajectory)
#     )
#     next_offset += len(trajectory_mem.trajectory)
#     return total_duration, next_offset * 132


# def run_sequence(cf, trajectory_id, duration0, duration1):
#     commander = cf.high_level_commander

#     TIME_SCALE = 0.4

#     commander.takeoff(1.0, 2.0)
#     time.sleep(3.0)
#     relative = True
#     commander.start_trajectory(1, TIME_SCALE, relative)
#     time.sleep(duration0 * TIME_SCALE - 0.1)
#     cf.high_level_commander.hover(0, 5.0)
#     # commander.start_trajectory(2, TIME_SCALE, relative)
#     time.sleep(duration1 * TIME_SCALE - 0.1)
#     cf.high_level_commander.go_to(-1.63, 0.24, 0.7, 0, 5.0)
#     time.sleep(5)
#     commander.land(0.0, 2.0)
#     time.sleep(2)
#     commander.stop()
