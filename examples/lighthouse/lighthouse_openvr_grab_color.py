#!/usr/bin/env python3
# Demo that makes one Crazyflie take off 30cm above the first controller found
# Using the controller trigger it is then possible to 'grab' the Crazyflie
# and to make it move.
# If the Crazyflie has a ledring attached, the touchpad of the controller can
# be used to change the color of the led-ring LEDs
import colorsys
import math
import sys
import time

import openvr

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger

# URI to the Crazyflie to connect to
uri = 'radio://0/80/2M'

print('Openning')
vr = openvr.init(openvr.VRApplication_Other)
print('Oppened')

# Find first controller or tracker
controllerId = None
poses = vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0,
                                           openvr.k_unMaxTrackedDeviceCount)
for i in range(openvr.k_unMaxTrackedDeviceCount):
    if poses[i].bPoseIsValid:
        device_class = vr.getTrackedDeviceClass(i)
        if device_class == openvr.TrackedDeviceClass_Controller or\
           device_class == openvr.TrackedDeviceClass_GenericTracker:
            controllerId = i
            break

if controllerId is None:
    print('Cannot find controller or tracker, exiting')
    sys.exit(1)


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

            # print('{} {} {}'.
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


def vector_substract(v0, v1):
    return [v0[0] - v1[0], v0[1] - v1[1], v0[2] - v1[2]]


def vector_add(v0, v1):
    return [v0[0] + v1[0], v0[1] + v1[1], v0[2] + v1[2]]


def run_sequence(scf):
    cf = scf.cf

    cf.param.set_value('ring.effect', '7')

    poses = vr.getDeviceToAbsoluteTrackingPose(
        openvr.TrackingUniverseStanding, 0, openvr.k_unMaxTrackedDeviceCount)

    controller_pose = poses[controllerId]
    pose = controller_pose.mDeviceToAbsoluteTracking
    # setpoint = [-1*pose[2][3], -1*pose[0][3], pose[1][3] + 0.3]
    setpoint = [0, 0, 0.5]

    grabbed = False
    grab_controller_start = [0, 0, 0]
    grab_setpoint_start = [0, 0, 0]

    while True:
        poses = vr.getDeviceToAbsoluteTrackingPose(
            openvr.TrackingUniverseStanding, 0,
            openvr.k_unMaxTrackedDeviceCount)
        controller_state = vr.getControllerState(controllerId)[1]

        trigger = ((controller_state.ulButtonPressed & 0x200000000) != 0)
        trackpad_touched = ((controller_state.ulButtonTouched & 0x100000000) != 0)  # noqa

        trackpad = (0, 0)
        for i in range(openvr.k_unControllerStateAxisCount):
            axis_type = vr.getInt32TrackedDeviceProperty(
                controllerId, openvr.Prop_Axis0Type_Int32 + i)[0]
            if axis_type == openvr.k_eControllerAxis_TrackPad:
                trackpad = (controller_state.rAxis[i].x,
                            controller_state.rAxis[i].y)

        controller_pose = poses[controllerId]
        pose = controller_pose.mDeviceToAbsoluteTracking

        if trackpad_touched:
            angle = math.atan2(trackpad[1], trackpad[0])
            hue = (angle + math.pi) / (2*math.pi)
            rgb = colorsys.hsv_to_rgb(hue, 1, 0.3)

            print(rgb)

            cf.param.set_value('ring.solidRed',
                               '{}'.format(int(rgb[0] * 255)))
            cf.param.set_value('ring.solidGreen',
                               '{}'.format(int(rgb[1] * 255)))
            cf.param.set_value('ring.solidBlue',
                               '{}'.format(int(rgb[2] * 255)))

        if not grabbed and trigger:
            print('Grab started')
            grab_controller_start = [-1*pose[2][3], -1*pose[0][3], pose[1][3]]
            grab_setpoint_start = setpoint

        if grabbed and not trigger:
            print('Grab ended')

        grabbed = trigger

        if trigger:
            curr = [-1*pose[2][3], -1*pose[0][3], pose[1][3]]
            setpoint = vector_add(grab_setpoint_start,
                                  vector_substract(curr, grab_controller_start)
                                  )

        cf.commander.send_position_setpoint(setpoint[0],
                                            setpoint[1],
                                            setpoint[2],
                                            0)
        time.sleep(0.02)

    cf.commander.send_setpoint
    (0, 0, 0, 0)
    # Make sure that the last packet leaves before the link is closed
    # since the message queue is not flushed before closing
    time.sleep(0.1)


if __name__ == '__main__':
    cflib.crtp.init_drivers()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        reset_estimator(scf)
        # start_position_printing(scf)
        run_sequence(scf)

    openvr.shutdown()
