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
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
"""
This script shows the basic use of the PositionHlCommander class.

Simple example that connects to the crazyflie at `URI` and runs a
sequence. This script requires some kind of location system.

The PositionHlCommander uses position setpoints.

Change the URI variable to your Crazyflie configuration.
"""
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.positioning.position_hl_commander import PositionHlCommander

import time


# URI to the Crazyflie to connect to
uri = 'radio://0/80/2M/E7E7E7E701'

# Input params
print("Please Enter Default Height: ")
DEFAULT_HEIGHT = input()    # initial height level of Crazyflie after taking off (default = 0.7)
DEFAULT_HEIGHT = float(DEFAULT_HEIGHT)
print("Please Enter Absolute Distance: ")
d_abs = input()      
d_abs = float(d_abs)       # entire distance from initial to end (i.e. a distance from ground to subject's wrist when he lift his arm up at the maximum height)  
d_fly = d_abs - DEFAULT_HEIGHT       # flying distance of Crazyflie 


# Sensor checking
is_flow_deck_attached = False
is_led_deck_attached = False
is_dwm1000_deck_attached = False

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
        
        # print("Var_x: ")
        # print(var_x_history)
        # print("Var_y: ")
        # print(var_y_history)
        # print("Var_z: ")
        # print(var_z_history)


def reset_estimator(scf):
    cf = scf.cf
    cf.param.set_value('kalman.resetEstimation', '1')
    time.sleep(0.1)
    cf.param.set_value('kalman.resetEstimation', '0')

    wait_for_position_estimator(cf)


def activate_high_level_commander(cf):
    cf.param.set_value('commander.enHighLevel', '1')


def position_callback(timestamp, data, logconf):
    x = data['kalman.stateX']
    y = data['kalman.stateY']
    z = data['kalman.stateZ']
    print("pos: ({}, {}, {})".format(x, y, z))


def start_position_printing(scf):
    log_conf = LogConfig(name='Position', period_in_ms=500)
    log_conf.add_variable('kalman.stateX', 'float')
    log_conf.add_variable('kalman.stateY', 'float')
    log_conf.add_variable('kalman.stateZ', 'float')

    scf.cf.log.add_config(log_conf)
    log_conf.data_received_cb.add_callback(position_callback)
    log_conf.start()

def slightly_more_complex_usage(scf):
    # with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:

    with PositionHlCommander(
            scf,
            x=2.2, y=1.7, z=0.0,
            default_velocity=0.2,
            default_height=0.5,
            controller=PositionHlCommander.CONTROLLER_PID) as pc:
        # Go to a coordinate
        # print('Setting position {2.0, 2.0, 0.5}')
        # pc.forward(0.5)
        # print('Setting position {2.0, 3.5, 0.5}')
        # pc.left(1.5)
        
        print('Setting position {2.2, 1.7, 1.0}')
        print("t1: ", time.time())
        # pc.go_to(2.2, 1.7, 1.0, velocity=0.2)
        pc.up(1.8, velocity=0.05)

        # print('Setting position {2.2, 1.7, 1.5}')
        # print("t2: ", time.time())
        # # pc.go_to(2.2, 1.7, 1.5, velocity=0.1)
        # pc.up(0.5, velocity=0.05)

        # print('Setting position {2.2, 1.7, 1.0}')
        # print("t3: ", time.time())
        # # pc.go_to(2.2, 1.7, 1.0, velocity=0.05)
        # pc.down(0.5, velocity=0.05)

        print('Setting position {2.2, 1.7, 0.5}')
        print("t4: ", time.time())
        # pc.go_to(2.2, 1.7, 0.5, velocity=0.05)
        pc.down(1.8, velocity=0.05)
        
        print("t5: ", time.time())

        # pc.set_default_velocity(0.2)
        # pc.set_default_height(0.2)
        # pc.go_to(1.5, 3.5)
        # pc.down(0.5, velocity=0.2)
        # pc.down(0.2, velocity=0.1)
        # pc.go_to(1.0, 1.0, 1.0)

        # # Move relative to the current position
        # pc.left(1.0)

        # # Go to a coordinate and use default height
        # pc.go_to(1.0, 3.0)

        # # Go slowly to a coordinate
        # pc.go_to(1.0, 1.0, velocity=0.2)

        # # Set new default velocity and height
        # pc.set_default_velocity(0.3)
        # pc.set_default_height(1.0)
        # pc.go_to(1.0, 2.0)


# # Posture 1 (using PositionHlCommander)
def move_baduanjin_hl_p1(scf):
    with PositionHlCommander(
            scf,
            x=1.2, y=1.7, z=0.0,
            default_velocity=0.2,
            default_height=DEFAULT_HEIGHT,
            controller=PositionHlCommander.CONTROLLER_PID) as pc:
        
        print('Setting position [2.2, 1.7, {}]'.format(DEFAULT_HEIGHT))
        t_init = time.time()

        time.sleep(1)

        ## Go up: d_fly meter/6 sec
        print('Setting position [2.2, 1.7, {}]'.format(d_abs))
        pc.up(d_fly, velocity=d_fly/6)
        t1 = time.time() - t_init
        print("t1: ", t1)
        
        ## Delay 4 sec
        time.sleep(4)
        t2 = time.time() - t_init
        print("t2: ", t2)

        ## Go down: d_fly meter/6 sec
        print('Setting position [2.2, 1.7, {}]'.format(DEFAULT_HEIGHT))
        pc.down(d_fly, velocity=d_fly/6)
        t3 = time.time() - t_init
        print("t3: ", t3)
        time.sleep(1)



def simple_sequence():
    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        with PositionHlCommander(scf) as pc:
            pc.forward(1.0)
            # pc.left(2.0)
            pc.forward(1.5)
            # pc.back(1.0)
            pc.go_to(1.5, 3.0, 1.0)
            pc.down(0.5)

            time.sleep(0.1)  # wait for testing


if __name__ == '__main__':
    cflib.crtp.init_drivers(enable_debug_driver=False)

    # slightly_more_complex_usage()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:

        scf.cf.param.add_update_callback(group='deck', name='bcFlow2',
                                         cb=param_deck_flow)
        scf.cf.param.add_update_callback(group='deck', name='bcLedRing',
                                         cb=param_deck_led)
        scf.cf.param.add_update_callback(group='deck', name='bcDWM1000',
                                         cb=param_deck_dwm1000)
        time.sleep(1)

        if is_dwm1000_deck_attached:
            # reset_estimator(scf)
            start_position_printing(scf)

            # pc = PositionHlCommander(scf)
            # pc.take_off()
            # time.sleep(1)
            # pc.land()

            # simple_sequence()

            activate_high_level_commander(scf.cf)

            # slightly_more_complex_usage(scf)

            move_baduanjin_hl_p1(scf)

        else:
            print("CF cannot fly since there is no dwm1000 deck attached!")


    
    
