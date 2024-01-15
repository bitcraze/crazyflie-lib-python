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
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.position_hl_commander import PositionHlCommander
from cflib.crazyflie.log import LogConfig

import time

# URI to the Crazyflie to connect to
uri = 'radio://0/80/2M/E7E7E7E705'


position_estimate = [0, 0, 0]  # Drone's pos

def log_pos_callback(uri, timestamp, data, logconf):
    global position_estimate_1
    position_estimate[0] = data['kalman.stateX']
    position_estimate[1] = data['kalman.stateY']
    position_estimate[2] = data['kalman.stateZ']
    print("{}: {} is at pos: ({}, {}, {})".format(timestamp, uri, position_estimate[0], position_estimate[1], position_estimate[2]))
                                            

def slightly_more_complex_usage():
    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        with PositionHlCommander(
                scf,
                x=0.0, y=0.0, z=0.0,
                default_velocity=0.3,
                default_height=0.5,
                controller=PositionHlCommander.CONTROLLER_MELLINGER) as pc:
            # Go to a coordinate
            pc.go_to(1.0, 1.0, 1.0)

            # Move relative to the current position
            pc.right(1.0)

            # Go to a coordinate and use default height
            pc.go_to(0.0, 0.0)

            # Go slowly to a coordinate
            pc.go_to(1.0, 1.0, velocity=0.2)

            # Set new default velocity and height
            pc.set_default_velocity(0.3)
            pc.set_default_height(1.0)
            pc.go_to(0.0, 0.0)


def simple_sequence():
    # with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
    with PositionHlCommander(
            scf,
            x=0.7, y=-0.0, z=0.0,
            default_velocity=0.2,
            default_height=0.3) as pc:
        # pc.forward(0.5)
        # pc.left(0.5)
        # pc.back(0.5)
        # pc.go_to(0.0, 0.0, 1.0)
        # pc.move_distance(0.5, 0.0, 0.0)
        # pc.move_distance(0.0, 0.5, 0.0)
        # pc.move_distance(-0.5, 0.0, 0.0)
        # pc.move_distance(0.0, -0.5, 1.0)
        
        pc.up(0.7)
        time.sleep(1)

        while position_estimate[2] < 1.3:

            pc.up(0.05)
            time.sleep(3)
            print(pc.get_position())

        print("outside loop")
        time.sleep(2)
        print(pc.get_position())


if __name__ == '__main__':
    cflib.crtp.init_drivers(enable_debug_driver=False)
    # with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
    #     pc = PositionHlCommander(scf)
    #     pc.take_off()
    #     time.sleep(3)
    #     pc.land()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        logconf = LogConfig(name='Position', period_in_ms=500)
        logconf.add_variable('kalman.stateX', 'float')
        logconf.add_variable('kalman.stateY', 'float')
        logconf.add_variable('kalman.stateZ', 'float')            
        scf.cf.log.add_config(logconf)
        logconf.data_received_cb.add_callback( lambda timestamp, data, logconf: log_pos_callback(uri, timestamp, data, logconf) )

        logconf.start()
        time.sleep(0.1)
    
        simple_sequence()

        logconf.stop()
    # slightly_more_complex_usage()
