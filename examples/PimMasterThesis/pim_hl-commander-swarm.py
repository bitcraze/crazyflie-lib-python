# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2019 Bitcraze AB
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
Simple example of a swarm using the High level commander.

The swarm takes off and flies a synchronous square shape before landing.
The trajectories are relative to the starting positions and the Crazyflies can
be at any position on the floor when the script is started.

This example is intended to work with any absolute positioning system.
It aims at documenting how to use the High Level Commander together with
the Swarm class.
"""
import time

import cflib.crtp
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncLogger import SyncLogger


uris = {
    'radio://0/80/2M/E7E7E7E701',
    'radio://0/80/2M/E7E7E7E702',
    # Add more URIs if you want more copters in the swarm
}

is_flow_deck_attached = False
is_led_deck_attached = False
is_dwm1000_deck_attached = False

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


def reset_estimator(scf):
    cf = scf.cf
    cf.param.set_value('kalman.resetEstimation', '1')
    time.sleep(0.1)
    cf.param.set_value('kalman.resetEstimation', '0')
    wait_for_position_estimator(scf)



def position_callback(uri, timestamp, data, logconf):
    x = data['kalman.stateX']
    y = data['kalman.stateY']
    z = data['kalman.stateZ']
    print("{} is at pos: ({}, {}, {})".format(uri, x, y, z))

    if uri == 'radio://0/80/2M/E7E7E7E701':
        # position_callback.current_h1 = z
        current_h1 = z 
    elif uri == 'radio://0/80/2M/E7E7E7E702':
        # position_callback.current_h2 = z
        current_h2 = z


def reaching_height_effect():
    if position_callback.current_h2 >= position_callback.current_h1:
        print("Reaching!!!") 


def start_position_printing(scf):
    log_conf = LogConfig(name='Position', period_in_ms=100)
    log_conf.add_variable('kalman.stateX', 'float')
    log_conf.add_variable('kalman.stateY', 'float')
    log_conf.add_variable('kalman.stateZ', 'float')

    uri= scf.cf.link_uri
    scf.cf.log.add_config(log_conf)
    # log_conf.data_received_cb.add_callback(position_callback)
    log_conf.data_received_cb.add_callback( lambda timestamp, data, logconf: position_callback(uri, timestamp, data, logconf) )
    log_conf.start()


def log_position(scf):
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


def activate_high_level_commander(scf):
    scf.cf.param.set_value('commander.enHighLevel', '1')


def activate_mellinger_controller(scf, use_mellinger):
    controller = 1
    if use_mellinger:
        controller = 2
    scf.cf.param.set_value('stabilizer.controller', controller)


def reaching_height_landing(scf):
    activate_mellinger_controller(scf, False)

    takeoff_height = 1.5
    takeoff_time = 3

    land_height = 0.2
    land_time = 3

    commander = scf.cf.high_level_commander
    uri= scf.cf.link_uri

    if uri == 'radio://0/80/2M/E7E7E7E701':

        commander.takeoff(takeoff_height, takeoff_time)
        
        time.sleep(15)

        commander.land(land_height, land_time)


        # if position_callback.current_h2 >= position_callback.current_h1:
        #     commander.land(land_height, land_time)


        



def run_sequence(scf): # flying only one Crazyflie
    activate_mellinger_controller(scf, False)

    box_size = 1
    flight_time = 2

    commander = scf.cf.high_level_commander
    uri= scf.cf.link_uri

    if uri == 'radio://0/80/2M/E7E7E7E701':
        
        print("Take off")
        commander.takeoff(1.0, 2.0)
        time.sleep(3)

        print("Pos 1")
        commander.go_to(box_size, 0, 0, 0, flight_time, relative=True)
        time.sleep(flight_time)

        print("Pos 2")
        commander.go_to(0, box_size, 0, 0, flight_time, relative=True)
        time.sleep(flight_time)

        print("Pos 3")
        commander.go_to(-box_size, 0, 0, 0, flight_time, relative=True)
        time.sleep(flight_time)

        print("Pos 4")
        commander.go_to(0, -box_size, 0, 0, flight_time, relative=True)
        time.sleep(flight_time)

        print("Landing")
        commander.land(0.0, 2.0)
        time.sleep(2)

        commander.stop()
    
    else:
        pass


def run_shared_sequence(scf):  # flying every Crazyflies in swarm
    activate_mellinger_controller(scf, False)

    box_size = 1
    flight_time = 2

    commander = scf.cf.high_level_commander

    print("Take off")
    commander.takeoff(1.0, 2.0)
    time.sleep(3)

    print("Pos 1")
    commander.go_to(box_size, 0, 0, 0, flight_time, relative=True)
    time.sleep(flight_time)

    print("Pos 2")
    commander.go_to(0, box_size, 0, 0, flight_time, relative=True)
    time.sleep(flight_time)

    print("Pos 3")
    commander.go_to(-box_size, 0, 0, 0, flight_time, relative=True)
    time.sleep(flight_time)

    print("Pos 4")
    commander.go_to(0, -box_size, 0, 0, flight_time, relative=True)
    time.sleep(flight_time)

    print("Landing")
    commander.land(0.0, 2.0)
    time.sleep(2)

    commander.stop()


if __name__ == '__main__':
    cflib.crtp.init_drivers(enable_debug_driver=False)
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        swarm.parallel_safe(activate_high_level_commander)
        swarm.parallel_safe(reset_estimator)
        # swarm.parallel_safe(log_position)
        swarm.parallel_safe(start_position_printing)
        # swarm.parallel_safe(run_shared_sequence)
        # swarm.parallel_safe(run_sequence)
        swarm.parallel_safe(reaching_height_landing)
        # swarm.parallel_safe(reaching_height_effect)

'''
The call to swarm.parallel_safe() in the main thread returns when the log_position() returns for all members of the swarm.
Since log_position() loops for ever in this case, swarm.parallel_safe() will block forever.
'''