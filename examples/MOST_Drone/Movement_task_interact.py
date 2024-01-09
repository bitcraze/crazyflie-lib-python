import time
import logging
import cflib.crtp
import threading
import winsound
import cv2

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.log import LogConfig


# URI to the Crazyflie to connect to
uri_1 = 'radio://0/80/2M/E7E7E7E705' # Drone's uri
uri_2 = 'radio://0/80/2M/E7E7E7E7E7' # Leg sensor's uri

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

init_H = float(0.7)  # Initial drone's height; unit: m

max_ROM = 0.5   # change this variable according to the selected movement
ori_pos = 0.3    # original leg's sensor height

move_dist = max_ROM - ori_pos  # total moving distant for drone and leg's sensor

start_pos_d = 0.3 + init_H   # start position for drone

init_Vel = 0.3  # Initial velocity
task_Vel = 0.2  # on-task velocity


position_estimate_1 = [0, 0, 0]  # Drone's pos
position_estimate_2 = [0, 0, 0]  # LS's pos
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
                                              

def drone_unit_test(scf):
    with MotionCommander(scf) as mc:
        print("unit start!!!")
        
        time.sleep(0.3/0.2)
        
        print("before going up") # the drone reaches the default take-off height 0.3 m

        mc.up(init_H, velocity=init_Vel)
        time.sleep(1) # Hovering for 1 sec after reaching the init_H + 0.3 m

        print("start!!!")

        for i in range(1,11):
            print("Round: ", i)

            print("start moving up")
            mc.start_up(velocity=task_Vel)  # drone starts moving up
            time.sleep(0.3/task_Vel) 

            print("start moving down")
            mc.start_down(velocity=task_Vel)
            time.sleep(0.3/task_Vel)

            mc.stop()
            time.sleep(0.1)



def drone_guide_mc_KnF(scf, event1, event2, event3): 
# default take-off height = 0.3 m, take-off velocity = 0.2
    with MotionCommander(scf) as mc:
        
        time.sleep(0.3/0.2)

        t_zero = time.time()
        print("before going up") # the drone reaches the default take-off height 0.3 m

        mc.up(init_H, velocity=init_Vel)
        time.sleep(1) # Hovering for 1 sec after reaching the init_H + 0.3 m

        print("start!!!")

        for i in range(1,11):

            print("Round: ", i)
            t_start = time.time()

            print("start moving up")
            mc.start_up(velocity=task_Vel)  # drone starts moving up
            time.sleep(0.1)

            while not event2.is_set(): # the current leg sensor's position hasn't reached the max ROM in z-axis
                
                print("event2 is not set")

                while event3.is_set()==True and event2.is_set()==False:  # the subject doesn't follow the drone
                    print("????????")
                    mc.stop()
                    time.sleep(0.1)

                    # if position_estimate_1[2] > start_pos_d + move_dist:
                    #     over_dist = position_estimate_1[2] - (start_pos_d + move_dist) 
                    #     print("over the upper limit_in (m): ", over_dist)
                    #     mc.down(over_dist, velocity=over_dist/0.2)  # moving down to the start_pos_d + move_dist within 0.2 second
                    #     # time.sleep(0.1)
                    
                print("moving up 5 cm/s")
                # mc.start_up(velocity=task_Vel)
                # time.sleep(0.05/task_Vel)    # This line can't be blank!!!
                
                mc.up(0.05, velocity=task_Vel)  # optional for the above two lines
                time.sleep(0.1)

                if position_estimate_1[2] > start_pos_d + move_dist:
                    over_dist = position_estimate_1[2] - (start_pos_d + move_dist) 
                    print("over the upper limit_out (m): ", over_dist)
                    mc.down(over_dist, velocity=over_dist/0.1)  # moving down to the start_pos_d + move_dist within 0.2 second
                    # time.sleep(0.1)
                

            # if position_estimate_1[2] > start_pos_d + move_dist:
            #     over_dist = position_estimate_1[2] - (start_pos_d + move_dist) 
            #     print("over the upper limit_2 (m): ", over_dist)
            #     mc.down(over_dist, velocity=over_dist/0.2)  # moving down to the start_pos_d + move_dist within 0.2 second
            #     # time.sleep(0.1)

            print("event2 is set (reached the target)") 
            # mc.stop()
            # time.sleep(0.1) # for subject's preparation

            
            ## Return process (without feedback)
            print("start moving down")
            if position_estimate_1[2] > start_pos_d:
                move_down_dist = position_estimate_1[2] - start_pos_d
                print("move down distance (m): ", move_down_dist)
                mc.down(move_down_dist, velocity=move_down_dist/2)  # moving down to the start_pos_d within 2 second
                print("Ready?")
                mc.stop()
                time.sleep(0.5)  # hovering for 0.5 sec

            # fine-tune error
            if position_estimate_1[2] < start_pos_d:
                under_dist = start_pos_d - position_estimate_1[2] 
                print("under the lower limit (m): ", under_dist)
                mc.up(under_dist, velocity=under_dist/0.2)  # moving up to the start_pos_d within 0.2 second
                # time.sleep(0.5)
            
            
            print("reached the start point")
            
            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per round: ", TpR)

            print("next!!!")

                 
        print("Task done")
        TpT = t_end - t_zero
        print("Total time: ", TpT)
        # set the event for turning off the sound feedback process
        event1.set()


# # Feedback Section

def position_state_change(event1, event2, event3):
    print("position thread start")
    while not event1.is_set():  # the drone hasn't finished the guiding yet
        
        if position_estimate_2[2] < max_ROM: # subject hasn't reached the max ROM yet
            # print("keep going")
            event2.clear()
        
            if abs(abs(position_estimate_2[2] - ori_pos)-abs(position_estimate_1[2] - 0.3 - init_H)) < 0.04:  # subject follows the drone
            # if abs((position_estimate_2[2])-(position_estimate_1[2])) < 0.04:
                # print("good job")
                event3.clear()
            
            # elif abs((position_estimate_2[2] + 0.3 + init_H)-(position_estimate_1[2])) > 0.04:
            else:
                # print("please follow the drone")
                event3.set()

        else:   # If the current leg sensor's position reaches the max ROM in z-axis
            # print("target reached!")
            event2.set()

    print("Finish guiding")

def sound_feedback(event1, event2, event3):
    print("sound thread started")
    while not event1.is_set():  # the drone hasn't finished the guiding yet
        
        if event2.is_set()==False: # the subject hasn't reached the max ROM yet
            
            if event3.is_set()==True and abs(position_estimate_2[2] - ori_pos) < abs(position_estimate_1[2] - 0.3 - init_H):
            # if event3.is_set()==True and position_estimate_2[2] < position_estimate_1[2]:  # subject not follow the drone
                print("Too low")
                frequency = 1500  # Set Frequency To 2500 Hertz
                duration = 500  # Set Duration To 250 ms == 0.25 second
                winsound.Beep(frequency, duration)
            
            elif event3.is_set()==True and abs(position_estimate_2[2] - ori_pos) > abs(position_estimate_1[2] - 0.3 - init_H):
            # elif event3.is_set()==True and position_estimate_2[2] > position_estimate_1[2]:  # subject not follow the drone
                print("Too high")
                # winsound.PlaySound('_invalid-selection.mp3', winsound.SND_FILENAME)
                frequency = 1500  # Set Frequency To 2500 Hertz
                duration = 200  # Set Duration To 250 ms == 0.25 second
                winsound.Beep(frequency, duration)
            
            else:
                print("Not in the case")

        else:
            print("You did it!")
            winsound.PlaySound('_short-success.mp3', winsound.SND_FILENAME)
            
        time.sleep(0.1)


if __name__ == '__main__':

    # # initializing the queue and event object
    e1 = threading.Event()  # Checking whether the drone completes its task
    e2 = threading.Event()  # Checking whether the Subject reaches the maximum ROM
    e3 = threading.Event()  # Checking whether the Subject follows the drone guide


    # # initializing Crazyflie 
    cflib.crtp.init_drivers(enable_debug_driver=False)

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
            time.sleep(3)

            drone_unit_test(scf_1)

            time.sleep(3)

            logconf_1.stop()
            logconf_2.stop()

'''
        # # Drone Motion (MotionCommander)
            # Declaring threads for feedback providing
            pos_state_thread = threading.Thread(name='Position-State-Change-Thread', target=position_state_change, args=(e1, e2, e3))
            sound_thread = threading.Thread(name='Sound-Feedback-Thread', target=sound_feedback, args=(e1, e2, e3))

            # Starting threads for drone motion
            pos_state_thread.start()
            sound_thread.start()

            # Perform the drone guiding task
            drone_guide_mc_KnF(scf_1, e1, e2, e3)
            # drone_guide_mc(scf_1, e2)
            
            # Threads join
            pos_state_thread.join()
            sound_thread.join()
    
            
            time.sleep(3)

            logconf_1.stop()
            logconf_2.stop()
'''
