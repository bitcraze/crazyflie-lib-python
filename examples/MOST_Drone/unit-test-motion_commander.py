import logging
import time
import math
import cflib.crtp

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.log import LogConfig

uri_1 = 'radio://0/80/2M/E7E7E7E710'

init_H = float(0.7)  # Initial drone's height; unit: m


init_Vel = 0.3  # Initial velocity
task_Vel = 0.2  # on-task velocity


position_estimate_1 = [0, 0, 0]  # Drone's pos


# # Positioning Callback Section

def log_pos_callback_1(uri_1, timestamp, data, logconf_1):
    global position_estimate_1
    position_estimate_1[0] = data['kalman.stateX']
    position_estimate_1[1] = data['kalman.stateY']
    position_estimate_1[2] = data['kalman.stateZ']
    print("{}: {} is at pos: ({}, {}, {})".format(timestamp, uri_1, position_estimate_1[0], position_estimate_1[1], position_estimate_1[2]))
                                            

def drone_guide_mc(scf): # default take-off height = 0.3 m, take-off velocity = 0.2
    with MotionCommander(scf) as mc:

        # # t_start = time.time()
        time.sleep(0.3/0.2)

        # print("start")

        t_start = time.time()
        print("before going up") # the drone reaches the default take-off height 0.3 m

        mc.up(init_H, velocity=init_Vel)
        t_up = time.time() # t_up = t_stop
        # print("start going up")

        # time.sleep(init_H/init_Vel)

        t_stop = time.time() # the drone reaches the init_H + 0.3 = 1.0 m
        
    print("Time spend: ", t_stop-t_up)
    print("Total time: ", t_stop-t_start)  # total time = init_H/init_Vel = 0.7/0.3 = 2.34


def drone_guide_mc_2(scf): # default take-off height = 0.3 m, take-off velocity = 0.2
    with MotionCommander(scf) as mc:

        # # t_start = time.time()
        time.sleep(0.3/0.2)

        # print("start")

        t_start = time.time()
        print("before going up") # the drone reaches the default take-off height 0.3 m

        mc.start_up(velocity=init_Vel)
        t_up = time.time()  # t_up = t_start
        print("start going up")

        time.sleep(init_H/init_Vel)  # without this line, the drone will immediately land.

        t_stop = time.time() # the drone reaches the init_H + 0.3 = 1.0 m
        
    print("Time spend: ", t_stop-t_up)
    print("Total time: ", t_stop-t_start)  # total time = init_H/init_Vel = 0.7/0.3 = 2.34


def drone_guide_mc_3(scf): # default take-off height = 0.3 m, take-off velocity = 0.2
    with MotionCommander(scf) as mc:

        # # t_start = time.time()
        time.sleep(0.3/0.2)

        # print("start")

        t_start = time.time()
        print("before linear motion") # the drone reaches the default take-off height 0.3 m

        velocity = init_Vel

        distance_x_m = 0.5
        distance_y_m = 0.0
        distance_z_m = 0.0

        distance = math.sqrt(distance_x_m * distance_x_m +
                             distance_y_m * distance_y_m +
                             distance_z_m * distance_z_m)
                
        flight_time = distance / velocity
        print("flight time: ", flight_time)

        velocity_x = velocity * distance_x_m / distance
        velocity_y = velocity * distance_y_m / distance
        velocity_z = velocity * distance_z_m / distance

        mc.start_linear_motion(velocity_x, velocity_y, velocity_z)
        t_up = time.time()  # t_up = t_start
        print("start linear motion")
        time.sleep(flight_time)

        t_stop = time.time() # the drone reaches the target point (0.5,0.0,0.5)
        
        print("Time spend: ", t_stop-t_up)
        print("Total time: ", t_stop-t_start)  # total time = init_H/init_Vel = 0.7/0.3 = 2.34


def drone_guide_mc_4(scf): # default take-off height = 0.3 m, take-off velocity = 0.2
    with MotionCommander(scf) as mc:

        # # t_start = time.time()
        time.sleep(0.3/0.2)

        # print("start")

        t_start = time.time()
        print("before going forward") # the drone reaches the default take-off height 0.3 m

        mc.start_forward(velocity=init_Vel)
        t_forward = time.time()  # t_up = t_start
        print("start going forward")

        time.sleep(0.5/init_Vel)

        t_stop = time.time() # the drone reaches the init_H + 0.3 = 1.0 m
        
    print("Time spend: ", t_stop-t_forward)
    print("Total time: ", t_stop-t_start)  # total time = init_H/init_Vel = 0.7/0.3 = 2.34


def drone_guide_mc_5(scf): # default take-off height = 0.3 m, take-off velocity = 0.2
    with MotionCommander(scf) as mc:

        # # t_start = time.time()
        time.sleep(0.3/0.2)

        # print("start")

        t_start = time.time()
        print("before moving forward") # the drone reaches the default take-off height 0.3 m

        mc.forward(0.5, velocity=init_Vel)
        t_forward = time.time() # t_up = t_stop
        # print("start going up")

        # time.sleep(init_H/init_Vel)

        t_stop = time.time() # the drone reaches the init_H + 0.3 = 1.0 m
        
    print("Time spend: ", t_stop-t_forward)
    print("Total time: ", t_stop-t_start)  # total time = init_H/init_Vel = 0.7/0.3 = 2.34


# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


if __name__ == '__main__':
    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(uri_1, cf=Crazyflie(rw_cache='./cache')) as scf_1:
        logconf_1 = LogConfig(name='Position', period_in_ms=500)
        logconf_1.add_variable('kalman.stateX', 'float')
        logconf_1.add_variable('kalman.stateY', 'float')
        logconf_1.add_variable('kalman.stateZ', 'float')            
        scf_1.cf.log.add_config(logconf_1)
        logconf_1.data_received_cb.add_callback(lambda timestamp, data, logconf_1: log_pos_callback_1(uri_1, timestamp, data, logconf_1) )

        logconf_1.start()
        time.sleep(1)


        # drone_guide_mc(scf_1)
        # drone_guide_mc_2(scf_1)
        drone_guide_mc_3(scf_1)