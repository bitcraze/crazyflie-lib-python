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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
Used for sending full state control setpoints to the Crazyflie
"""
import time
import logging

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.utils import uri_helper
import math
from cflib.crazyflie.log import LogConfig



# URI to the Crazyflie to connect to
uri = uri_helper.uri_from_env(default='radio://0/65/2M/E7E7E7E7F2')

def quaternion_from_euler(roll, pitch, yaw):

    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    q = [0] * 4
    q[0] = sr * cp * cy - cr * sp * sy
    q[1] = cr * sp * cy + sr * cp * sy
    q[2] = cr * cp * sy - sr * sp * cy
    q[3] = cr * cp * cy + sr * sp * sy

    return q


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

    wait_for_position_estimator(cf)


def position_callback(timestamp, data, logconf):
    x = data['kalman.stateX']
    y = data['kalman.stateY']
    z = data['kalman.stateZ']
    print('pos: ({}, {}, {})'.format(x, y, z))


def start_position_printing(scf):
    log_conf = LogConfig(name='Position', period_in_ms=500)
    log_conf.add_variable('kalman.stateX', 'float')
    log_conf.add_variable('kalman.stateY', 'float')
    log_conf.add_variable('kalman.stateZ', 'float')

    scf.cf.log.add_config(log_conf)
    log_conf.data_received_cb.add_callback(position_callback)
    log_conf.start()


def run_sequence(scf):
    cf = scf.cf

    # Set to mellinger controller
    # cf.param.set_value('stabilizer.controller', '2')

    # quaternion from roll pitch yaw
    roll = 0.0
    pitch = 0.0
    yaw = 0.0 #20.0*math.pi/180.0
    q = quaternion_from_euler(roll, pitch, yaw)
    print('takeoff')
    cf.commander.send_full_state_setpoint(0.0,0.0,1.0,
                                          0.0,0.0,0.0,
                                          0.0,0.0,0.0,
                                          q[0],q[1],q[2],q[3],
                                          0.0,0.0,0.0)
                                                                                  
    time.sleep(2.0)
    cf.commander.send_full_state_setpoint(0.0,0.0,1.0,
                                        0.0,0.0,0.0,
                                        0.0,0.0,0.0,
                                        q[0],q[1],q[2],q[3],
                                        0.0,0.0,0.0)
    time.sleep(2.0)
    print('land')
    cf.commander.send_full_state_setpoint(0.0,0.0,0.2,
                                          0.0,0.0,0.0,
                                          0.0,0.0,0.0,
                                          q[0],q[1],q[2],q[3],
                                          0.0,0.0,0.0)
                                                                                  
    time.sleep(2.0)


    cf.commander.send_stop_setpoint()
    # Make sure that the last packet leaves before the link is closed
    # since the message queue is not flushed before closing
    time.sleep(0.1)

def _stab_log_data(timestamp, data, logconf):
    print('roll: {}, pitch: {}, yaw: {}'.format(data['controller.roll'],
                                                data['controller.pitch'],
                                                data['controller.yaw']))
    print('ctrltarget.x: {}, ctrltarget.y: {}, ctrltarget.z: {}'.format(data['ctrltarget.x'],
                                                                        data['ctrltarget.y'],
                                                                        data['ctrltarget.z']))
if __name__ == '__main__':
    cflib.crtp.init_drivers()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        _lg_stab = LogConfig(name='Stabilizer', period_in_ms=500)
        _lg_stab.add_variable('controller.roll', 'float')
        _lg_stab.add_variable('controller.pitch', 'float')
        _lg_stab.add_variable('controller.yaw', 'float')
        _lg_stab.add_variable('ctrltarget.x', 'float')
        _lg_stab.add_variable('ctrltarget.y', 'float')
        _lg_stab.add_variable('ctrltarget.z', 'float')

        scf.cf.log.add_config(_lg_stab)
        _lg_stab.data_received_cb.add_callback(_stab_log_data)
        _lg_stab.start()

        #reset_estimator(scf)
        run_sequence(scf)
