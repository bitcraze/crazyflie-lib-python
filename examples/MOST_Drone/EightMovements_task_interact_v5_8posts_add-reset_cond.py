import time
import cflib.crtp
import queue
import threading
import winsound
import os

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.log import LogConfig


# URI to the Crazyflie to connect to
uri_1 = 'radio://0/80/2M/E7E7E7E705' # Drone's uri
uri_2 = 'radio://0/80/2M/E7E7E7E7E7' # Leg sensor's uri

init_H = float(1)  # Initial drone's height; unit: m
# final_H = float(0.7)  # Final drone's height; unit: m

## Define the max ROM according to the movement
max_hip_exten = float(0.68)         # for movement (a) Hip exten; unit: m
max_hip_abd = float(0.58)           # for movement (b) Hip abd/add; unit: m
max_knee_flex = float(0.5)          # for movement (c) Knee flex; unit: m
max_tiptoe = float(0.31)            # for movement (d) Tiptoe; unit: m
max_hip_knee_flex = float(0.53)     # for movement (e) Hip & knee flex; unit: m
max_heel_to_heel = float(0.2)       # for movement (f) Heel to heel; unit: m
max_step_forward = float(0.5)       # for movement (g) Step forward; unit: m

# max_ROM = 1
max_ROM = 0.38    # change this variable according to the selected movement
ori_pos = 0.29    # original leg's sensor height

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
                                              


# # Crazyflie Motion Section

def drone_guide_mc(scf, event1, event2, event3): # default take-off height = 0.3 m
    with MotionCommander(scf) as mc:
        
        mc.up(init_H, velocity=init_Vel)
        time.sleep(1)
        print("start!!!")

        while position_estimate_1[2] < init_H:
            pass


        for i in range(1,6):

            print("Round: ", i)
            
            
            ## Tip-toe

            mc.start_up(velocity=task_Vel)  # drone starts moving up
            # time.sleep(0.3)


            while not event2.is_set(): # the current leg sensor's position hasn't reached the max ROM in z-axis
                
                # print("event2 is not set")
                # mc.start_up(velocity=task_Vel)

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    mc.stop()
                    time.sleep(0.1)
                
                # print("start up")
                mc.start_up(velocity=task_Vel)
                time.sleep(0.1)      # This line can't be blank!!!
        
            print("event2 is set (reached the target)") 
            # mc.stop()
            # time.sleep(0.1) # for subject's preparation

            print("start down")
            mc.start_down(velocity=task_Vel)  # drone starts moving down
            time.sleep(0.1)
            
            
            # If the drone exceeds the upper limit, then moving down
            while position_estimate_1[2] - 0.3 - init_H > max_ROM - ori_pos:
                print("over the upper limit")
                mc.start_down(velocity=task_Vel)  # drone starts moving down
                time.sleep(0.1)

            # while position_estimate_1[2] > max_ROM + 0.3 + init_H: # If the drone doesn't lower than the default take-off height (0.3 meter)
            while position_estimate_1[2] > 0.3 + init_H: # If the drone doesn't lower than the default take-off height (0.3 meter) + unit_H
                # print("keep going down")

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    mc.stop()
                    time.sleep(0.1)
                
                mc.start_down(velocity=task_Vel)
                time.sleep(0.1)
            
            print("lower than init height")
            # mc.stop()
            # time.sleep(0.1)

            # print("next turn ready!")
            
            

            '''
            ## Flex/Extend

            mc.start_linear_motion(-task_Vel, 0.0, task_Vel)  # drone starts moving up
            # time.sleep(0.3)


            while not event2.is_set(): # the current leg sensor's position hasn't reached the max ROM in z-axis
                
                # print("event2 is not set")
                # mc.start_up(velocity=task_Vel)

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    mc.stop()
                    time.sleep(0.1)
                
                # print("start up")
                mc.start_linear_motion(-task_Vel, 0.0, task_Vel)
                time.sleep(0.1)      # This line can't be blank!!!
        
            print("event2 is set (reached the target)") 
            # mc.stop()
            # time.sleep(0.1) # for subject's preparation

            print("start down")
            mc.start_linear_motion(task_Vel, 0.0, -task_Vel)  # drone starts moving down
            # time.sleep(0.5)
            
            # If the drone exceeds the upper limit, then moving down
            while position_estimate_1[2] - 0.3 - init_H > max_ROM - ori_pos:
                mc.start_down(velocity=task_Vel)  # drone starts moving down
                time.sleep(0.1)
            
            # while position_estimate_1[2] > max_ROM + 0.3 + init_H: # If the drone doesn't lower than the default take-off height (0.3 meter)
            while position_estimate_1[2] > 0.3 + init_H: # If the drone doesn't lower than the default take-off height (0.3 meter) + unit_H
                # print("keep going down")

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    mc.stop()
                    time.sleep(0.1)
                
                mc.start_linear_motion(task_Vel, 0.0, -task_Vel)
                time.sleep(0.1)
            
            print("lower than init height")
            # mc.stop()
            # time.sleep(0.1)

            # print("next turn ready!")

            '''

            '''
            ## Abduct/adduct

            mc.start_linear_motion(0.0, -task_Vel, task_Vel)  # drone starts moving up
            # time.sleep(0.3)


            while not event2.is_set(): # the current leg sensor's position hasn't reached the max ROM in z-axis
                
                # print("event2 is not set")
                # mc.start_up(velocity=task_Vel)

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    mc.stop()
                    time.sleep(0.1)
                
                # print("start up")
                mc.start_linear_motion(0.0, -task_Vel, task_Vel)
                time.sleep(0.1)      # This line can't be blank!!!
        
            print("event2 is set (reached the target)") 
            # mc.stop()
            # time.sleep(0.1) # for subject's preparation

            print("start down")
            mc.start_linear_motion(0.0, task_Vel, -task_Vel)  # drone starts moving down
            # time.sleep(0.5)
            
            # If the drone exceeds the upper limit, then moving down
            while position_estimate_1[2] - 0.3 - init_H > max_ROM - ori_pos:
                mc.start_down(velocity=task_Vel)  # drone starts moving down
                time.sleep(0.1)
            
            # while position_estimate_1[2] > max_ROM + 0.3 + init_H: # If the drone doesn't lower than the default take-off height (0.3 meter)
            while position_estimate_1[2] > 0.3 + init_H: # If the drone doesn't lower than the default take-off height (0.3 meter) + unit_H
                # print("keep going down")

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    mc.stop()
                    time.sleep(0.1)
                
                mc.start_linear_motion(0.0, task_Vel, -task_Vel)
                time.sleep(0.1)
            
            print("lower than init height")
            # mc.stop()
            # time.sleep(0.1)

            # print("next turn ready!")
            '''

                 
        print("Task done")
        # set the event for turning off the sound feedback process
        event1.set()


# # Feedback Section

def position_state_change(event1, event2, event3):
    print("position thread start")
    while not event1.is_set():  # the drone hasn't finished the guiding yet
        
        ## For Tip-toe

        if position_estimate_2[2] < max_ROM: # subject hasn't reached the max ROM yet
            # print("keep going")
            event2.clear()
        
            if abs(((position_estimate_2[2] - ori_pos)*3)-(position_estimate_1[2] - 0.3 - init_H)) < 0.04:  # subject follows the drone
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

            if abs((position_estimate_2[2] - ori_pos)-(position_estimate_1[2] - 0.3 - init_H)) < 0.04:  # subject follows the drone
            # if abs((position_estimate_2[2])-(position_estimate_1[2])) < 0.04:
                # print("good job")
                event3.clear()
            
            # elif abs((position_estimate_2[2] + 0.3 + init_H)-(position_estimate_1[2])) > 0.04:
            else:
                # print("please follow the drone")
                event3.set()
        
        '''
        ## For other movements

        if position_estimate_2[2] < max_ROM: # subject hasn't reached the max ROM yet
            # print("keep going")
            event2.clear()
        
            if abs((position_estimate_2[2] - ori_pos)-(position_estimate_1[2] - 0.3 - init_H)) < 0.04:  # subject follows the drone
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

            if abs((position_estimate_2[2] - ori_pos)-(position_estimate_1[2] - 0.3 - init_H)) < 0.04:  # subject follows the drone
            # if abs((position_estimate_2[2])-(position_estimate_1[2])) < 0.04:
                # print("good job")
                event3.clear()
            
            # elif abs((position_estimate_2[2] + 0.3 + init_H)-(position_estimate_1[2])) > 0.04:
            else:
                # print("please follow the drone")
                event3.set()
        '''

            

# In all cases, the mean and median Euclidean error of the Lighthouse positioning system are about 2-4 centimeters compared to our MoCap system as ground truth.
# Ref: https://www.bitcraze.io/2021/05/lighthouse-positioning-accuracy/ 



def sound_feedback(event1, event2, event3):
    print("sound thread started")
    while not event1.is_set():  # the drone hasn't finished the guiding yet
        
        if event2.is_set()==False: # the subject hasn't reached the max ROM yet
            
            ## For Tip-toe

            if event3.is_set()==True and (position_estimate_2[2] - ori_pos)*3 < position_estimate_1[2] - 0.3 - init_H:
            # if event3.is_set()==True and position_estimate_2[2] < position_estimate_1[2]:  # subject not follow the drone
                print("Too low")
                frequency = 1500  # Set Frequency To 2500 Hertz
                duration = 500  # Set Duration To 250 ms == 0.25 second
                winsound.Beep(frequency, duration)
            
            elif event3.is_set()==True and (position_estimate_2[2] - ori_pos)*3 > position_estimate_1[2] - 0.3 - init_H:
            # elif event3.is_set()==True and position_estimate_2[2] > position_estimate_1[2]:  # subject not follow the drone
                print("Too high")
                # winsound.PlaySound('_invalid-selection.mp3', winsound.SND_FILENAME)
                frequency = 1500  # Set Frequency To 2500 Hertz
                duration = 200  # Set Duration To 250 ms == 0.25 second
                winsound.Beep(frequency, duration)
            
            else:
                pass

            '''
            ## For other movements

            if event3.is_set()==True and position_estimate_2[2] - ori_pos < position_estimate_1[2] - 0.3 - init_H:
            # if event3.is_set()==True and position_estimate_2[2] < position_estimate_1[2]:  # subject not follow the drone
                print("Too low")
                frequency = 1500  # Set Frequency To 2500 Hertz
                duration = 500  # Set Duration To 250 ms == 0.25 second
                winsound.Beep(frequency, duration)
            
            elif event3.is_set()==True and position_estimate_2[2] - ori_pos > position_estimate_1[2] - 0.3 - init_H:
            # elif event3.is_set()==True and position_estimate_2[2] > position_estimate_1[2]:  # subject not follow the drone
                print("Too high")
                # winsound.PlaySound('_invalid-selection.mp3', winsound.SND_FILENAME)
                frequency = 1500  # Set Frequency To 2500 Hertz
                duration = 200  # Set Duration To 250 ms == 0.25 second
                winsound.Beep(frequency, duration)
            
            else:
                pass
            '''

        else:
            # print("You did it!")
            winsound.PlaySound('_short-success.mp3', winsound.SND_FILENAME)
            
        time.sleep(0.1)



# using other sounds, see in:  https://www.geeksforgeeks.org/python-winsound-module/
# correct sound download: https://pixabay.com/sound-effects/search/correct/ 

if __name__ == '__main__':

    # # initializing the queue and event object
    q = queue.Queue(maxsize=0)
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


        # # Drone Motion (MotionCommander)
            # Declaring threads for feedback providing
            pos_state_thread = threading.Thread(name='Position-State-Change-Thread', target=position_state_change, args=(e1, e2, e3))
            sound_thread = threading.Thread(name='Sound-Feedback-Thread', target=sound_feedback, args=(e1, e2, e3))

            # Starting threads for drone motion
            pos_state_thread.start()
            sound_thread.start()

            # Perform the drone guiding task
            drone_guide_mc(scf_1, e1, e2, e3)
            # drone_guide_mc(scf_1, e2)
            
            # Threads join
            pos_state_thread.join()
            sound_thread.join()
    
            
            time.sleep(3)

            logconf_1.stop()
            logconf_2.stop()

