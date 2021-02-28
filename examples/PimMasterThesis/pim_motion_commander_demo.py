# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2017 Bitcraze AB
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
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
"""
This script shows the basic use of the MotionCommander class.

Simple example that connects to the crazyflie at `URI` and runs a
sequence. This script requires some kind of location system, it has been
tested with (and designed for) the flow deck.

The MotionCommander uses velocity setpoints.

Change the URI variable to your Crazyflie configuration.
"""
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.positioning.motion_commander import MotionCommander

# URI = 'radio://0/70/2M'
URI = 'radio://0/80/2M/E7E7E7E702'

DEFAULT_HEIGHT = 0.5
position_estimate = [0, 0, 0]

is_flow_deck_attached = False
is_led_deck_attached = False
is_dwm1000_deck_attached = False


# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

def simple_move(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(1)

        # There is a set of functions that move a specific distance
        # We can move in all directions
        print('Setting position {forward 0.8}')
        mc.forward(0.8)
        print('Setting position {backward 0.8}')
        mc.back(0.8)
        time.sleep(1)

        print('Setting position {upward 0.5}')
        mc.up(0.5)
        print('Setting position {downward 0.5}')
        mc.down(0.5)
        time.sleep(1)

        # # We can also set the velocity
        # mc.right(0.5, velocity=0.8)
        # time.sleep(1)
        # mc.left(0.5, velocity=0.4)
        # time.sleep(1)

        # # We can do circles or parts of circles
        # mc.circle_right(0.5, velocity=0.5, angle_degrees=180)

        # # Or turn
        # mc.turn_left(90)
        # time.sleep(1)

        # # We can move along a line in 3D space
        # mc.move_distance(-1, 0.0, 0.5, velocity=0.6)
        # time.sleep(1)

        # # There is also a set of functions that start a motion. The
        # # Crazyflie will keep on going until it gets a new command.

        # mc.start_left(velocity=0.5)
        # # The motion is started and we can do other stuff, printing for
        # # instance
        # for _ in range(5):
        #     print('Doing other work')
        #     time.sleep(0.2)

        # # And we can stop
        # mc.stop()


def move_baduanjin_p1(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(1)
        mc.move_distance(0, 0, 0.7, velocity=0.05)   # so the final posistion (before landing) will be "height = 0.5(default h) + 0.7" 
        time.sleep(1)
        mc.move_distance(0, 0, -0.5, velocity=0.05)
        time.sleep(1)
        mc.move_distance(0, 0, -0.3, velocity=0.05)
        time.sleep(1)



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
        
        print("Var_x: ")
        print(var_x_history)
        print("Var_y: ")
        print(var_y_history)
        print("Var_z: ")
        print(var_z_history)


def reset_estimator(scf):
    cf = scf.cf
    cf.param.set_value('kalman.resetEstimation', '1')
    time.sleep(0.1)
    cf.param.set_value('kalman.resetEstimation', '0')

    wait_for_position_estimator(cf)



def position_callback(timestamp, data, logconf):
    x = data['kalman.stateX']
    y = data['kalman.stateY']
    z = data['kalman.stateZ']
    print("pos: ({}, {}, {})".format(x, y, z))


def start_position_printing(scf):
    log_conf = LogConfig(name='Position', period_in_ms=10)
    log_conf.add_variable('kalman.stateX', 'float')
    log_conf.add_variable('kalman.stateY', 'float')
    log_conf.add_variable('kalman.stateZ', 'float')

    scf.cf.log.add_config(log_conf)
    log_conf.data_received_cb.add_callback(position_callback)
    log_conf.start()
    time.sleep(5)
    log_conf.stop()


def param_deck_flow(name, value_str):
    value = int(value_str)
    # print(value)
    global is_flow_deck_attached
    if value:
        is_flow_deck_attached = True
        print('Flow Deck is attached!')
    else:
        is_flow_deck_attached = False
        print('Flow Deck is NOT attached!')

def param_deck_led(name, value_str):
    value = int(value_str)
    # print(value)
    global is_led_deck_attached
    if value:
        is_led_deck_attached = True
        print('LED Deck is attached!')
    else:
        is_led_deck_attached = False
        print('LED Deck is NOT attached!')

def param_deck_dwm1000(name, value_str):
    value = int(value_str)
    # print(value)
    global is_dwm1000_deck_attached
    if value:
        is_dwm1000_deck_attached = True
        print('DWM1000 Deck is attached!')
    else:
        is_dwm1000_deck_attached = False
        print('DWM1000 Deck is NOT attached!')


if __name__ == '__main__':
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:

        scf.cf.param.add_update_callback(group='deck', name='bcFlow2',
                                         cb=param_deck_flow)
        scf.cf.param.add_update_callback(group='deck', name='bcLedRing',
                                         cb=param_deck_led)
        scf.cf.param.add_update_callback(group='deck', name='bcDWM1000',
                                         cb=param_deck_dwm1000)
        time.sleep(1)

     
        # logconf.data_received_cb.add_callback(log_pos_callback)

        if is_flow_deck_attached:
            # reset_estimator(scf)
            start_position_printing(scf)

            # move_baduanjin_p1(scf)
            # simple_move(scf)

        else:
            print("CF cannot fly since there is no flow deck attached!")

