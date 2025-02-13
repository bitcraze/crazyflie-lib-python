#!/usr/bin/env python3
# Demo that makes two Crazyflie take off 30cm above the first controller found
# Using the controller trigger it is then possible to 'grab' the closest
# Crazyflie and to make it move.
import math
import sys
import time

import openvr

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils.reset_estimator import reset_estimator

# URI to the Crazyflie to connect to
uri0 = 'radio://0/80/2M/E7E7E7E701'
uri1 = 'radio://0/80/2M/E7E7E7E702'

print('Opening')
vr = openvr.init(openvr.VRApplication_Other)
print('Opened')

# Find first controller or tracker
controllerId = None
poses = vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0,
                                           openvr.k_unMaxTrackedDeviceCount)
for i in range(openvr.k_unMaxTrackedDeviceCount):
    if poses[i].bPoseIsValid:
        device_class = vr.getTrackedDeviceClass(i)
        if device_class == openvr.TrackedDeviceClass_Controller or \
           device_class == openvr.TrackedDeviceClass_GenericTracker:
            controllerId = i
            break

if controllerId is None:
    print('Cannot find controller or tracker, exiting')
    sys.exit(1)


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


def vector_subtract(v0, v1):
    return [v0[0] - v1[0], v0[1] - v1[1], v0[2] - v1[2]]


def vector_add(v0, v1):
    return [v0[0] + v1[0], v0[1] + v1[1], v0[2] + v1[2]]


def vector_norm(v0):
    return math.sqrt((v0[0] * v0[0]) + (v0[1] * v0[1]) + (v0[2] * v0[2]))


def run_sequence(scf0, scf1):
    cf0 = scf0.cf
    cf1 = scf1.cf

    poses = vr.getDeviceToAbsoluteTrackingPose(
        openvr.TrackingUniverseStanding, 0, openvr.k_unMaxTrackedDeviceCount)
    controller_pose = poses[controllerId]
    pose = controller_pose.mDeviceToAbsoluteTracking
    setpoints = [[-1 * pose[2][3], -1 * pose[0][3] - 0.5, pose[1][3] + 0.3],
                 [-1 * pose[2][3], -1 * pose[0][3] + 0.5, pose[1][3] + 0.3]]

    closest = 0

    grabbed = False
    grab_controller_start = [0, 0, 0]
    grab_setpoint_start = [0, 0, 0]

    while True:
        poses = vr.getDeviceToAbsoluteTrackingPose(
            openvr.TrackingUniverseStanding, 0,
            openvr.k_unMaxTrackedDeviceCount)
        controller_state = vr.getControllerState(controllerId)[1]

        trigger = ((controller_state.ulButtonPressed & 0x200000000) != 0)

        controller_pose = poses[controllerId]
        pose = controller_pose.mDeviceToAbsoluteTracking

        if not grabbed and trigger:
            print('Grab started')
            grab_controller_start = [-1 * pose[2][3], -1 * pose[0][3], pose[1][3]]

            dist0 = vector_norm(vector_subtract(grab_controller_start,
                                                setpoints[0]))
            dist1 = vector_norm(vector_subtract(grab_controller_start,
                                                setpoints[1]))

            if dist0 < dist1:
                closest = 0
            else:
                closest = 1

            grab_setpoint_start = setpoints[closest]

        if grabbed and not trigger:
            print('Grab ended')

        grabbed = trigger

        if trigger:
            curr = [-1 * pose[2][3], -1 * pose[0][3], pose[1][3]]
            setpoints[closest] = vector_add(
                grab_setpoint_start, vector_subtract(curr,
                                                     grab_controller_start))

        cf0.commander.send_position_setpoint(setpoints[0][0],
                                             setpoints[0][1],
                                             setpoints[0][2],
                                             0)
        cf1.commander.send_position_setpoint(setpoints[1][0],
                                             setpoints[1][1],
                                             setpoints[1][2],
                                             0)

        time.sleep(0.02)

    cf0.commander.send_setpoint(0, 0, 0, 0)
    cf1.commander.send_setpoint(0, 0, 0, 0)
    # Make sure that the last packet leaves before the link is closed
    # since the message queue is not flushed before closing
    time.sleep(0.1)


if __name__ == '__main__':
    cflib.crtp.init_drivers()

    with SyncCrazyflie(uri0, cf=Crazyflie(rw_cache='./cache')) as scf0:
        reset_estimator(scf0)
        with SyncCrazyflie(uri1, cf=Crazyflie(rw_cache='./cache')) as scf1:
            reset_estimator(scf1)

            # Arm the Crazyflies
            scf0.cf.platform.send_arming_request(True)
            scf1.cf.platform.send_arming_request(True)
            time.sleep(1.0)

            run_sequence(scf0, scf1)

    openvr.shutdown()
