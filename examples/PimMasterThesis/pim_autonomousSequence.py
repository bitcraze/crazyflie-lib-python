# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2016 Bitcraze AB
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
Simple example that connects to one crazyflie (check the address at the top
and update it to your crazyflie address) and send a sequence of setpoints,
one every 5 seconds.

This example is intended to work with the Loco Positioning System in TWR TOA
mode. It aims at documenting how to set the Crazyflie in position control mode
and how to send setpoints.
"""
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
# import cflib.crazyflie.log as lg
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger

# URI to the Crazyflie to connect to
uri = 'radio://0/80/2M/E7E7E7E702'
# uri = 'radio://0/80/2M'

is_flow_deck_attached = False
is_led_deck_attached = False
is_dwm1000_deck_attached = False


# Change the sequence according to your setup
#             x[m]    y[m]    z[m]    YAW[deg]
sequence = [
    (1.5, 2.0, 1.0, 0),
    (1.5, 2.5, 1.0, 0),
    (1.5, 3.0, 1.0, 0),
    (1.5, 3.5, 1.0, 0),
    (1.5, 3.5, 0.5, 0),
    (1.5, 3.0, 0.5, 0),
    (1.5, 2.5, 0.5, 0),
]

# sequence = [                # for hovering (vx[m/s],vy[m/s],yawrate[deg/s],zdist[m])
#     (0.01, 0.01, 0, 0.2),
#     (-0.01, -0.01, 0, 0.4),
#     (0.01, 0.01, 0, 0.6),
#     (-0.01, -0.01, 0, 0.8),
#     (0.01, 0.01, 0, 1.0),
#     (-0.01, -0.01, 0, 0.8),
#     (0.01, 0.01, 0, 0.6),
#     (-0.01, -0.01, 0, 0.4),
#     (0.01, 0.01, 0, 0.2),
# ]

# sequence = [                # for zdistance (vx[m/s],vy[m/s],yawrate[deg/s],zdist[m])
#     # (0, 0, 0, 0.2),
#     (0, 0, 0, 0.4),
#     (0, 0, 0, 0.6),
#     (0, 0, 0, 0.8),
#     (0, 0, 0, 1.0),
#     (0, 0, 0, 0.8),
#     (0, 0, 0, 0.6),
#     (0, 0, 0, 0.4),
#     # (0, 0, 0, 0.2),
# ]


def wait_for_position_estimator(scf):
    print('Waiting for estimator to find position...')

    # log_config = lg.LogConfig(name='Kalman Variance', period_in_ms=500)
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


def position_callback(timestamp, data, logconf):
    x = data['kalman.stateX']
    y = data['kalman.stateY']
    z = data['kalman.stateZ']
    print("pos: ({}, {}, {})".format(x, y, z))


def start_position_printing(scf):
    # log_conf = lg.LogConfig(name='Position', period_in_ms=500)
    log_conf = LogConfig(name='Position', period_in_ms=500)
    log_conf.add_variable('kalman.stateX', 'float')
    log_conf.add_variable('kalman.stateY', 'float')
    log_conf.add_variable('kalman.stateZ', 'float')


    # add_conf = lg.Log(scf.cf)
    # add_conf.add_config(log_conf)

    scf.cf.log.add_config(log_conf)
    log_conf.data_received_cb.add_callback(position_callback)
    log_conf.start()


def log_position(scf):
    # lg_stab = lg.LogConfig(name='position', period_in_ms=100)
    lg_stab = LogConfig(name='position', period_in_ms=100)
    lg_stab.add_variable('stateEstimate.x', 'float')
    lg_stab.add_variable('stateEstimate.y', 'float')
    lg_stab.add_variable('stateEstimate.z', 'float')

    uri = scf.cf.link_uri
    with SyncLogger(scf, lg_stab) as logger:
        for log_entry in logger:
            data = log_entry[1]

            x = data['stateEstimate.x']
            y = data['stateEstimate.y']
            z = data['stateEstimate.z']

            print(uri, "is at", x, y, z)


def run_sequence(scf, sequence):
    cf = scf.cf
    
    # cf.commander.set_client_xmode(enabled=True)

    # cf.commander.send_velocity_world_setpoint(0,0,0.01,0)


    for position in sequence:
        print('Setting position {}'.format(position))
        for i in range(50):
            cf.commander.send_velocity_world_setpoint(0.005,0.005,0.005,0)
            cf.commander.send_position_setpoint(position[0],
                                                position[1],
                                                position[2],
                                                position[3])
            # cf.commander.send_velocity_world_setpoint(0,0,0.001,0)
            # cf.commander.send_hover_setpoint(position[0],
            #                                  position[1],
            #                                  position[2],
            #                                  position[3])
            # print(i)
            time.sleep(0.05)  # sleep for 0.1 second
        
        

    cf.commander.send_stop_setpoint()
    # Make sure that the last packet leaves before the link is closed
    # since the message queue is not flushed before closing
    time.sleep(0.1)

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

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:

        scf.cf.param.add_update_callback(group='deck', name='bcFlow2',
                                         cb=param_deck_flow)
        scf.cf.param.add_update_callback(group='deck', name='bcLedRing',
                                         cb=param_deck_led)
        scf.cf.param.add_update_callback(group='deck', name='bcDWM1000',
                                         cb=param_deck_dwm1000)
        time.sleep(1)

        if is_dwm1000_deck_attached:
            reset_estimator(scf)
            start_position_printing(scf)
            # log_position(scf)
            # time.sleep(0.5)
            # run_sequence(scf, sequence)

        else:
            print("CF cannot fly since there is no dwm1000 deck attached!")

        
