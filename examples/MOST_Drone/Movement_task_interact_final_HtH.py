import time
import logging
import cflib.crtp
import threading
import winsound
import math
import cv2

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.position_hl_commander import PositionHlCommander
from cflib.crazyflie.log import LogConfig


# URI to the Crazyflie to connect to
uri_1 = 'radio://0/80/2M/E7E7E7E705' # Drone's uri
uri_2 = 'radio://0/80/2M/E7E7E7E7E7' # Leg sensor1's uri
uri_3 = 'radio://0/80/2M/E7E7E7E7E8' # Leg sensor2's uri

init_H = float(0.7)  # Initial drone's height; unit: m
start_pos_d = 0.3 + init_H   # start z-position for drone
start_x = float(1.0)  # initial pos_X of the drone; unit: m
start_y = float(0.0)  # initial pos_y of the drone; unit: m

rep = 5   # repeat = rep-1

task_Vel = 0.2  # on-task velocity

# for hip extension
dx = 0.25   # step length
ori_pos_d_x = 0.0    # original drone position in x-axis
ori_pos_t_x = 0.8    # original tag position in x-axis
diff_x = ori_pos_d_x - ori_pos_t_x  # initial diff between drone and tag 


position_estimate_1 = [0, 0, 0]  # Drone's pos
position_estimate_2 = [0, 0, 0]  # LS1's pos
position_estimate_3 = [0, 0, 0]  # LS2's pos
# # Positioning Callback Section


def log_pos_callback_1(uri_1, timestamp, data, logconf_1):
    global position_estimate_1
    position_estimate_1[0] = data['kalman.stateX']
    position_estimate_1[1] = data['kalman.stateY']
    position_estimate_1[2] = data['kalman.stateZ']
    print("{}: {} is at pos: ({}, {}, {})".format(timestamp, uri_1, position_estimate_1[0], position_estimate_1[1], position_estimate_1[2]))
                                            

def log_pos_callback_2(uri_2, timestamp, data, logconf_2):
    global position_estimate_2
    position_estimate_2[0] = data['kalman.stateX']
    position_estimate_2[1] = data['kalman.stateY']
    position_estimate_2[2] = data['kalman.stateZ']
    print("{}: {} is at pos: ({}, {}, {})".format(timestamp, uri_2, position_estimate_2[0], position_estimate_2[1], position_estimate_2[2]))


def log_pos_callback_3(uri_3, timestamp, data, logconf_3):
    global position_estimate_3
    position_estimate_3[0] = data['kalman.stateX']
    position_estimate_3[1] = data['kalman.stateY']
    position_estimate_3[2] = data['kalman.stateZ']
    print("{}: {} is at pos: ({}, {}, {})".format(timestamp, uri_3, position_estimate_3[0], position_estimate_3[1], position_estimate_3[2]))
                 

def drone_guide_pc_HtH(scf, event1, event2): 
    
    with PositionHlCommander(
            scf,
            x=0.7, y=0.0, z=0.0,
            default_velocity=task_Vel,
            default_height=0.3,
            controller=PositionHlCommander.CONTROLLER_PID) as pc:

        time.sleep(0.3/0.2)

        t_zero = time.time()
        print("before going up") # the drone reaches the default take-off height 0.3 m

        pc.up(init_H)
        time.sleep(0.5) # Hovering for 1 sec after reaching the init_H + 0.3 m

        print("start!!!")

        for i in range(1,rep):

            print("move forward, step: ", i)
            t_start = time.time()

            pc.move_distance(dx, 0.0, 0.0)
            time.sleep(0.05/task_Vel)
            print(pc.get_position())

            while not event2.is_set():  # the subject doesn't follow the drone's step
                print("please step forward to follow the drone")
                # time.sleep(0.1)

            print("Good job and keep going!")
            winsound.PlaySound('Success.wav', winsound.SND_FILENAME)

            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per step ", i, ": ", TpR)
            print("next!!!")
            

        print("subject and drone reached the target")
        winsound.PlaySound('_short-success.mp3', winsound.SND_FILENAME)
        print(pc.get_position())

        TpT = t_end - t_zero
        print("Total time: ", TpT)
        time.sleep(0.1) # hovering for 0.1 sec

        # set the event for turning off the sound feedback process
        event1.set()

        

# # Feedback Section

def position_state_change(event1, event2):
    print("position thread start")
    while not event1.is_set():  # the drone hasn't finished the guiding yet
        
        if abs(position_estimate_1[0]-position_estimate_2[0]-diff_x) < 0.02 or abs(position_estimate_1[0]-position_estimate_3[0]-diff_x) < 0.02 : 
            # print("good job")
            event2.set()
                            
        else: 
            # print("keep going")
            event2.clear()

    print("Finish guiding")


# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


if __name__ == '__main__':

    # # initializing the queue and event object
    e1 = threading.Event()  # Checking whether the drone completes its task
    e2 = threading.Event()  # Checking whether the Subject follows the drone


    # # initializing Crazyflie 
    cflib.crtp.init_drivers(enable_debug_driver=False)

   
    with SyncCrazyflie(uri_3, cf=Crazyflie(rw_cache='./cache')) as scf_3:
        logconf_3 = LogConfig(name='Position', period_in_ms=500)
        logconf_3.add_variable('kalman.stateX', 'float')
        logconf_3.add_variable('kalman.stateY', 'float')
        logconf_3.add_variable('kalman.stateZ', 'float')            
        scf_3.cf.log.add_config(logconf_3)
        logconf_3.data_received_cb.add_callback( lambda timestamp, data, logconf_3: log_pos_callback_3(uri_3, timestamp, data, logconf_3) )

        with SyncCrazyflie(uri_2, cf=Crazyflie(rw_cache='./cache')) as scf_2:
            logconf_2 = LogConfig(name='Position', period_in_ms=500)
            logconf_2.add_variable('kalman.stateX', 'float')
            logconf_2.add_variable('kalman.stateY', 'float')
            logconf_2.add_variable('kalman.stateZ', 'float')            
            scf_2.cf.log.add_config(logconf_2)
            logconf_2.data_received_cb.add_callback( lambda timestamp, data, logconf_2: log_pos_callback_2(uri_2, timestamp, data, logconf_2) )

            with SyncCrazyflie(uri_1, cf=Crazyflie(rw_cache='./cache')) as scf_1:
                logconf_1 = LogConfig(name='Position', period_in_ms=500)
                logconf_1.add_variable('kalman.stateX', 'float')
                logconf_1.add_variable('kalman.stateY', 'float')
                logconf_1.add_variable('kalman.stateZ', 'float')        
                scf_1.cf.log.add_config(logconf_1)
                logconf_1.data_received_cb.add_callback( lambda timestamp, data, logconf_1: log_pos_callback_1(uri_1, timestamp, data, logconf_1) )
                
                logconf_1.start()
                logconf_2.start()
                logconf_3.start()
                time.sleep(3)


            # # Drone Motion (MotionCommander)
                # Declaring threads for feedback providing
                pos_state_thread = threading.Thread(name='Position-State-Change-Thread', target=position_state_change, args=(e1, e2))

                # Starting threads for drone motion
                pos_state_thread.start()

                # Perform the drone guiding task
                drone_guide_pc_HtH(scf_1, e1, e2)

                
                # Threads join
                pos_state_thread.join()

                
                time.sleep(3)

                logconf_1.stop()
                logconf_2.stop()
                logconf_3.stop()