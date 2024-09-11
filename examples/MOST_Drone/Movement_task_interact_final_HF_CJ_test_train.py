import time
import logging
import cflib.crtp
import threading
import winsound
import math


from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.position_hl_commander import PositionHlCommander
from cflib.crazyflie.log import LogConfig

'''
Changing these parameters for every trials
1. uri_1: changing based on the drone's uri
2. init_H: changing based on the subject's chest position (No need for now)
3. rep: changing based on the how many trials the subject has to repeat (i.e., rep = 6 for testing 5 trials)
4. step: changing based on the movement 
    - Hip extension: step = 2
    - Hip flexion and knee flexion: step = 3
    - Hip abduction: step = 2
5. bt: adjusting break time between trials (No need to change)
6. max_ROM_x or max_ROM_y or max_ROM_z: changing based on subject's maximum ROM for that movement (get this value from Crazyflie Client's Lighthouse tab)
7. ori_pos_x or ori_pos_y or ori_pos_z:  changing based on subject's initial position for that movement (get this value from Crazyflie Client's Lighthouse tab)
8. (Line 774-789) uncommented the "pos_state_thread" and "drone_guide_pc_XX" according to the movement that subject has to perform

'''



# URI to the Crazyflie to connect to
uri_1 = 'radio://0/80/2M/E7E7E7E701' # Drone's uri
uri_2 = 'radio://0/80/2M/E7E7E7E7E9' # Leg sensor's uri

init_H = float(0.7)  # Initial drone's height; unit: m
start_pos_d = 0.3 + init_H   # start z-position for drone
start_x = float(1.0)  # initial pos_X of the drone; unit: m
start_y = float(0.0)  # initial pos_y of the drone; unit: m   #Left: 0.0; Right: -0.4

rep = 10   # trial = rep-1; for testing: rep=6, while for training: rep=11
step = 3 # changing according to the movement  
count = step + 1 # inner loop count

task_Vel = 0.2  # on-task velocity
bt = 2  # break time between trials; unit: second

# for hip extension 後抬腿 X (2 steps) 
max_ROM_x = -0.21     # change this variable according to the selected movement; unit: m
ori_pos_x = -0.09  # original leg's sensor position in x-axis; unit: m
move_dist_x = abs(ori_pos_x - max_ROM_x)  # total moving distant in x-axis for drone and leg's sensor
ds_x = move_dist_x/(step)  # moving distant in inner for loop

# for hip&knee flex 勾膝蓋/抬膝蓋 Z (3 steps)
max_ROM_z = 0.77  # change this variable according to the selected movement; unit: m
ori_pos_z = 0.41  # original leg's sensor height; unit: m
move_dist_z = abs(ori_pos_z - max_ROM_z)  # total moving distant in z-axis for drone and leg's sensor
ds_z = move_dist_z/(step)  # moving distant in inner for loop

# for hip abduction 側抬腿 Y (2 steps)
max_ROM_y = -0.25  # change this variable according to the selected movement; unit: m
ori_pos_y = -0.06  # original leg's sensor position in y-axis; unit: m
move_dist_y = abs(ori_pos_y - max_ROM_y)  # total moving distant in y-axis for drone and leg's sensor
ds_y = move_dist_y/(step)  # moving distant in inner for loop


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
                                              

def drone_guide_pc_KnF_HFKnF(scf, event1, event2, event3, event4): 


    with PositionHlCommander(
            scf,
            x=start_x, y=start_y, z=0.0,
            default_velocity=task_Vel,
            default_height=0.3,
            controller=PositionHlCommander.CONTROLLER_PID) as pc:

        # time.sleep(0.3/0.2)

        t_zero = time.time()
        print("before going up") # the drone reaches the default take-off height 0.3 m

        pc.up(init_H)
        time.sleep(init_H/task_Vel)
        print(pc.get_position())

        print("start!!!")
        winsound.PlaySound('game-start-6104.wav', winsound.SND_FILENAME)

        for i in range(1,rep):
            
            print("Round: ", i)
            
            t_start = time.time()

            for j in range(1,count):

                print("move up 4-5 cm, count: ", j)
                pc.up(ds_z) 
                time.sleep(ds_z/task_Vel)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.01)

            if position_estimate_1[2] > start_pos_d + move_dist_z:
                over_dist = position_estimate_1[2] - (start_pos_d + move_dist_z) 
                print("over the upper limit (m): ", over_dist)
                pc.down(over_dist)  # moving down to the start_pos_d + move_dist_z within 0.2 second
                time.sleep(over_dist/task_Vel)
                print("after adjusting")
                print(pc.get_position())


            while not event2.is_set():
                print("You haven't reached the target")
                # time.sleep(0.01)


            print("subject and drone reached the target!!!!")
            winsound.PlaySound('_short-success.wav', winsound.SND_FILENAME)
            print(pc.get_position())
            # time.sleep(0.1) # for subject's preparation

            
            ## Return process (with feedback)
            for k in range(1,count):

                print("move down 4-5 cm, count: ", k)
                pc.down(ds_z) 
                time.sleep(ds_z/task_Vel)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.5)


            # time.sleep(0.1)    

            if position_estimate_1[2] < start_pos_d:
                under_dist = start_pos_d - position_estimate_1[2] 
                print("under the lower limit (m): ", under_dist)
                pc.up(under_dist)  # moving down to the start_pos_d + move_dist_z within 0.2 second
                time.sleep(under_dist/task_Vel)
                print("after adjusting")
                print(pc.get_position())


            while not event4.is_set():
                print("You haven't returned to the start point")
                # time.sleep(0.01)


            print("subject and drone reached the start point!!!!")
            winsound.PlaySound('_short-success.wav', winsound.SND_FILENAME)
            print(pc.get_position())
            # time.sleep(0.02) # for subject's preparation

            
            # print("Ready?")
            # time.sleep(0.2)  # hovering for 0.5 sec
            
            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per round: ", TpR)
            time.sleep(bt)      # break time between trials
            print("next!!!")

        # set the event for turning off the sound feedback process
        event1.set()

        print("Task done")
        TpT = t_end - t_zero
        print("Total time: ", TpT)



def drone_guide_pc_HE(scf, event1, event2, event3, event4): 

    per = 1.0
    dist = math.sqrt((per*ds_x)*(per*ds_x) + ds_x*ds_x)
    
    with PositionHlCommander(
            scf,
            x=start_x, y=start_y, z=0.0,
            default_velocity=task_Vel,
            default_height=0.3,
            controller=PositionHlCommander.CONTROLLER_PID) as pc:

        # time.sleep(0.3/0.2)

        t_zero = time.time()
        print("before going up") # the drone reaches the default take-off height 0.3 m

        pc.up(init_H)
        time.sleep(init_H/task_Vel)
        print(pc.get_position())

        print("start!!!")
        winsound.PlaySound('game-start-6104.wav', winsound.SND_FILENAME)

        for i in range(1,rep):

            print("Round: ", i)
            t_start = time.time()

            for j in range(1,count):

                print("move up-backward 4-5 cm, count: ", j)
                pc.move_distance(-(per*ds_x), 0.0, ds_x)
                time.sleep(dist/task_Vel)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.01)


            if position_estimate_1[0] < start_x - move_dist_x:
                over_dist = abs(position_estimate_1[0] - (start_x - move_dist_x))
                print("exceed the upper bound (m): ", over_dist)
                pc.move_distance(per*over_dist, 0.0, -over_dist)  # moving down to the start_pos_d + move_dist_z within 0.2 second
                dist_o = math.sqrt((per*over_dist)*(per*over_dist) + over_dist*over_dist)
                time.sleep(dist_o/task_Vel)
                print("after adjusting")
                print(pc.get_position())


            while not event2.is_set():
                print("You haven't reached the target")
                # time.sleep(0.01)


            print("subject and drone reached the target")
            winsound.PlaySound('_short-success.wav', winsound.SND_FILENAME)
            print(pc.get_position())
            # time.sleep(0.2) # for subject's preparation

            
            ## Return process (with feedback)
            for k in range(1,count):

                print("move down-forward 4-5 cm, count: ", k)
                pc.move_distance((per*ds_x), 0.0, -ds_x)
                time.sleep(dist/task_Vel)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)


            # time.sleep(0.1)    

            if position_estimate_1[0] > start_x:
                under_dist = position_estimate_1[0] - start_x 
                print("exceed the lower bound (m): ", under_dist)
                pc.move_distance(-(per*under_dist), 0.0, under_dist)  # moving down to the start_pos_d + move_dist_z within 0.2 second
                dist_u = math.sqrt((per*under_dist)*(per*under_dist) + under_dist*under_dist)
                time.sleep(dist_u/task_Vel)
                print("after adjusting")
                print(pc.get_position())

            while not event4.is_set():
                print("You haven't returned to the start point")
                # time.sleep(0.05)

            print("subject and drone reached the start point")
            winsound.PlaySound('_short-success.wav', winsound.SND_FILENAME)
            print(pc.get_position())
            # time.sleep(0.05) # for subject's preparation

            
            # print("Ready?")
            # time.sleep(0.2)  # hovering for 0.5 sec
            
            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per round ", i, ": ", TpR)
            time.sleep(bt)      # break time between trials
            print("next!!!")

        # set the event for turning off the sound feedback process
        event1.set()

        print("Task done")
        TpT = t_end - t_zero
        print("Total time: ", TpT)



def drone_guide_pc_HA_R(scf, event1, event2, event3, event4): 

    per = 1.0
    dist = math.sqrt((per*ds_y)*(per*ds_y) + ds_y*ds_y)
    
    with PositionHlCommander(
            scf,
            x=start_x, y=start_y, z=0.0,
            default_velocity=task_Vel,
            default_height=0.3,
            controller=PositionHlCommander.CONTROLLER_PID) as pc:

        # time.sleep(0.3/0.2)

        t_zero = time.time()
        print("before going up") # the drone reaches the default take-off height 0.3 m

        pc.up(init_H)
        time.sleep(init_H/task_Vel)
        print(pc.get_position())

        print("start!!!")
        winsound.PlaySound('game-start-6104.wav', winsound.SND_FILENAME)

        for i in range(1,rep):

            print("Round: ", i)
            t_start = time.time()

            for j in range(1,count):

                print("move up-right 4-5 cm, count: ", j)
                pc.move_distance(0.0, -(per*ds_y), ds_y)
                time.sleep(dist/task_Vel + 0.05)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            if position_estimate_1[1] < start_y - move_dist_y:
                over_dist = abs(position_estimate_1[1] - (start_y - move_dist_y))
                print("exceed the upper limit (m): ", over_dist)
                pc.move_distance(0.0, per*over_dist, -over_dist)  # moving down to the start_pos_d + move_dist_z within 0.2 second
                dist_o = math.sqrt((per*over_dist)*(per*over_dist) + over_dist*over_dist)
                time.sleep(dist_o/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())


            while not event2.is_set():
                print("You haven't reached the target")
                # time.sleep(0.05)


            print("subject and drone reached the target")
            winsound.PlaySound('_short-success.wav', winsound.SND_FILENAME)
            print(pc.get_position())
            # time.sleep(0.2) # for subject's preparation

            
            ## Return process (with feedback)
            for k in range(1,count):

                print("move down-left 5 cm, count: ", k)
                pc.move_distance(0.0, (per*ds_y), -ds_y)
                time.sleep(dist/task_Vel + 0.05)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)
                

            # time.sleep(0.1)    

            if position_estimate_1[1] > start_y:
                under_dist = position_estimate_1[1] - start_y
                print("exceed the lower limit (m): ", under_dist)
                pc.move_distance(0.0, -(per*under_dist), under_dist)  # moving down to the start_pos_d + move_dist_z within 0.2 second
                dist_u = math.sqrt((per*under_dist)*(per*under_dist) + under_dist*under_dist)
                time.sleep(dist_u/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())

            while not event4.is_set():
                print("You haven't returned to the start point")
                # time.sleep(0.05)

            print("subject and drone reached the start point")
            winsound.PlaySound('_short-success.wav', winsound.SND_FILENAME)
            print(pc.get_position())
            # time.sleep(0.05) # for subject's preparation

            
            # print("Ready?")
            # time.sleep(0.2)  # hovering for 0.5 sec
            
            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per round: ", TpR)
            time.sleep(bt)      # break time between trials
            print("next!!!")

        # set the event for turning off the sound feedback process
        event1.set()

        print("Task done")
        TpT = t_end - t_zero
        print("Total time: ", TpT)


def drone_guide_pc_HA_L(scf, event1, event2, event3, event4): 
    
    per = 1.0
    dist = math.sqrt((per*ds_y)*(per*ds_y) + ds_y*ds_y)

    with PositionHlCommander(
            scf,
            x=start_x, y=start_y, z=0.0,
            default_velocity=task_Vel,
            default_height=0.3,
            controller=PositionHlCommander.CONTROLLER_PID) as pc:

        # time.sleep(0.3/0.2)

        t_zero = time.time()
        print("before going up") # the drone reaches the default take-off height 0.3 m

        pc.up(init_H)
        time.sleep(init_H/task_Vel)
        print(pc.get_position())

        print("start!!!")
        winsound.PlaySound('game-start-6104.wav', winsound.SND_FILENAME)

        for i in range(1,rep):

            print("Round: ", i)
            t_start = time.time()

            for j in range(1,count):

                print("move up-left 4-5 cm, count: ", j)
                pc.move_distance(0.0, per*ds_y, ds_y)
                time.sleep(dist/task_Vel + 0.05)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            if position_estimate_1[1] > start_y + move_dist_y:
                over_dist = position_estimate_1[1] - (start_y + move_dist_y) 
                print("exceed the upper limit (m): ", over_dist)
                pc.move_distance(0.0, -per*over_dist, -over_dist)  # moving down to the start_pos_d + move_dist_z within 0.2 second
                dist_o = math.sqrt((per*over_dist)*(per*over_dist) + over_dist*over_dist)
                time.sleep(dist_o/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())


            while not event2.is_set():
                print("You haven't reached the target")
                # time.sleep(0.05)


            print("subject and drone reached the target")
            winsound.PlaySound('_short-success.wav', winsound.SND_FILENAME)
            print(pc.get_position())
            # time.sleep(0.2) # for subject's preparation

            
            ## Return process (with feedback)
            for k in range(1,count):

                print("move down-right 5 cm, count: ", k)
                pc.move_distance(0.0, -(per*ds_y), -ds_y)
                time.sleep(dist/task_Vel + 0.05)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)
                

            # time.sleep(0.1)    

            if position_estimate_1[1] < start_y:
                under_dist = start_y - position_estimate_1[1] 
                print("exceed the lower limit (m): ", under_dist)
                pc.move_distance(0.0, per*under_dist, under_dist)  # moving down to the start_pos_d + move_dist_z within 0.2 second
                dist_u = math.sqrt((per*under_dist)*(per*under_dist) + under_dist*under_dist)
                time.sleep(dist_u/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())

            while not event4.is_set():
                print("You haven't returned to the start point")
                # time.sleep(0.05)

            print("subject and drone reached the start point")
            winsound.PlaySound('_short-success.wav', winsound.SND_FILENAME)
            print(pc.get_position())
            # time.sleep(0.05) # for subject's preparation

            
            # print("Ready?")
            # time.sleep(0.2)  # hovering for 0.5 sec
            
            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per round: ", TpR)
            time.sleep(bt)      # break time between trials
            print("next!!!")

        # set the event for turning off the sound feedback process
        event1.set()

        print("Task done")
        TpT = t_end - t_zero
        print("Total time: ", TpT)


# # Feedback Section

def position_state_change_KnF(event1, event2, event3, event4):
    print("position thread for hip/knee flexion start")
    while not event1.is_set():  # the drone hasn't finished the guiding yet
        
        # If the current leg sensor's position reaches the max ROM in z-axis
        if abs(position_estimate_2[2] - max_ROM_z) < 0.025 and abs(position_estimate_1[2] - (start_pos_d + move_dist_z)) < 0.025: # subject has reached the max ROM ?
            # print("target reached max ROM")
            event2.set()
        
            if abs(abs(position_estimate_2[2] - ori_pos_z)-abs(position_estimate_1[2] - start_pos_d)) < 0.025:  # subject follows the drone
                # print("good job")
                event3.clear()
                # winsound.PlaySound('Success.wav', winsound.SND_FILENAME)

            else:
                # print("please follow the drone")
                event3.set()

        # If the current leg sensor's position reaches the max ROM in z-axis
        elif abs(position_estimate_2[2] - ori_pos_z) and abs(position_estimate_1[2] - start_pos_d) < 0.025:
            # print("target returned")
            event4.set()
        
            if abs(abs(position_estimate_2[2] - ori_pos_z)-abs(position_estimate_1[2] - start_pos_d)) < 0.025:  # subject follows the drone
                # print("good job")
                event3.clear()
                # winsound.PlaySound('Success.wav', winsound.SND_FILENAME)

            else:
                # print("please follow the drone")
                event3.set()

        else:   
            # print("keep going")
            event2.clear()

            if abs(abs(position_estimate_2[2] - ori_pos_z)-abs(position_estimate_1[2] - start_pos_d)) < 0.025:  # subject follows the drone
                # print("good job")
                event3.clear()
                # winsound.PlaySound('Success.wav', winsound.SND_FILENAME)

            else:
                # print("please follow the drone")
                event3.set()

    print("Finish guiding")


def position_state_change_HE(event1, event2, event3, event4):
    print("position thread for hip extension start")
    while not event1.is_set():  # the drone hasn't finished the guiding yet
        
        # If the current leg sensor's position reaches the max ROM in x-axis
        if abs(position_estimate_2[0] - max_ROM_x) < 0.025 and abs(position_estimate_1[0] - (start_x- move_dist_x)) < 0.025: # subject has reached the max ROM ?
            # print("target reached max ROM")
            event2.set()
        
            if abs(abs(position_estimate_2[0] - ori_pos_x)-abs(position_estimate_1[0] - start_x)) < 0.025:  # subject follows the drone
                # print("good job")
                event3.clear()
                # winsound.PlaySound('Success.wav', winsound.SND_FILENAME)

            else:
                # print("please follow the drone")
                event3.set()

        # If the current leg sensor's position returns to the start point
        elif abs(position_estimate_2[0] - ori_pos_x) and abs(position_estimate_1[0] - start_x) < 0.025:
            # print("target returned")
            event4.set()
        
            if abs(abs(position_estimate_2[0] - ori_pos_x)-abs(position_estimate_1[0] - start_x)) < 0.025:  # subject follows the drone
                # print("good job")
                event3.clear()
                # winsound.PlaySound('Success.wav', winsound.SND_FILENAME)

            else:
                # print("please follow the drone")
                event3.set()

        else:   
            # print("keep going")
            event2.clear()

            if abs(abs(position_estimate_2[0] - ori_pos_x)-abs(position_estimate_1[0] - start_x)) < 0.025:  # subject follows the drone
                # print("good job")
                event3.clear()
                # winsound.PlaySound('Success.wav', winsound.SND_FILENAME)

            else:
                # print("please follow the drone")
                event3.set()


    print("Finish guiding")


def position_state_change_HA_R(event1, event2, event3, event4):
    print("position thread for hip abduction start")
    while not event1.is_set():  # the drone hasn't finished the guiding yet
        
        # If the current leg sensor's position reaches the max ROM in y-axis
        if abs(position_estimate_2[1] - max_ROM_y) < 0.025 and abs(position_estimate_1[1] - (start_y - move_dist_y)) < 0.025: # subject has reached the max ROM ?
            # print("target reached max ROM")
            event2.set()
        
            if abs(abs(position_estimate_2[1] - ori_pos_y)-abs(position_estimate_1[1] - start_y)) < 0.025:  # subject follows the drone
                # print("good job")
                event3.clear()
                # winsound.PlaySound('Success.wav', winsound.SND_FILENAME)

            else:
                # print("please follow the drone")
                event3.set()

        # If the current leg sensor's position returns to the start point
        elif abs(position_estimate_2[1] - ori_pos_y) and abs(position_estimate_1[1] - start_y) < 0.025:
            # print("target returned")
            event4.set()
        
            if abs(abs(position_estimate_2[1] - ori_pos_y)-abs(position_estimate_1[1] - start_y)) < 0.025:  # subject follows the drone
                # print("good job")
                event3.clear()
                # winsound.PlaySound('Success.wav', winsound.SND_FILENAME)

            else:
                # print("please follow the drone")
                event3.set()

        else:   
            # print("keep going")
            event2.clear()

            if abs(abs(position_estimate_2[1] - ori_pos_y)-abs(position_estimate_1[1] - start_y)) < 0.025:  # subject follows the drone
                
                # print("good job")
                event3.clear()
                # winsound.PlaySound('Success.wav', winsound.SND_FILENAME)
                # time.sleep(0.1)
                
            else:
                # print("please follow the drone")
                event3.set()

    print("Finish guiding")


def position_state_change_HA_L(event1, event2, event3, event4):
    print("position thread for hip abduction start")
    while not event1.is_set():  # the drone hasn't finished the guiding yet
        
        # If the current leg sensor's position reaches the max ROM in y-axis
        if abs(position_estimate_2[1] - max_ROM_y) < 0.025 and abs(position_estimate_1[1] - (start_y + move_dist_y)) < 0.025: # subject has reached the max ROM ?
            # print("target reached max ROM")
            event2.set()
        
            if abs(abs(position_estimate_2[1] - ori_pos_y)-abs(position_estimate_1[1] - start_y)) < 0.025:  # subject follows the drone
                # print("good job")
                event3.clear()
                # winsound.PlaySound('Success.wav', winsound.SND_FILENAME)

            else:
                # print("please follow the drone")
                event3.set()

        # If the current leg sensor's position returns to the start point
        elif abs(position_estimate_2[1] - ori_pos_y) and abs(position_estimate_1[1] - start_y) < 0.025:
            # print("target returned")
            event4.set()
        
            if abs(abs(position_estimate_2[1] - ori_pos_y)-abs(position_estimate_1[1] - start_y)) < 0.025:  # subject follows the drone
                # print("good job")
                event3.clear()
                # winsound.PlaySound('Success.wav', winsound.SND_FILENAME)

            else:
                # print("please follow the drone")
                event3.set()

        else:   
            # print("keep going")
            event2.clear()

            if abs(abs(position_estimate_2[1] - ori_pos_y)-abs(position_estimate_1[1] - start_y)) < 0.025:  # subject follows the drone
                # print("good job")
                event3.clear()
                # winsound.PlaySound('Success.wav', winsound.SND_FILENAME)

            else:
                # print("please follow the drone")
                event3.set()

    print("Finish guiding")
    


# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


if __name__ == '__main__':

    # # initializing the queue and event object
    e1 = threading.Event()  # Checking whether the drone completes its task
    e2 = threading.Event()  # Checking whether the Subject reaches the maximum ROM
    e3 = threading.Event()  # Checking whether the Subject follows the drone guide
    e4 = threading.Event()  # Checking whether the Subject returns to the original point


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
            # # Declaring threads for feedback providing
            pos_state_thread = threading.Thread(name='Position-State-Change-Thread', target=position_state_change_HE, args=(e1, e2, e3, e4))
            # pos_state_thread = threading.Thread(name='Position-State-Change-Thread', target=position_state_change_KnF, args=(e1, e2, e3, e4))
            # pos_state_thread = threading.Thread(name='Position-State-Change-Thread', target=position_state_change_HA_R, args=(e1, e2, e3, e4))
            # pos_state_thread = threading.Thread(name='Position-State-Change-Thread', target=position_state_change_HA_L, args=(e1, e2, e3, e4))


            # Starting threads for drone motion
            pos_state_thread.start()

            # Perform the drone guiding task
            drone_guide_pc_HE(scf_1, e1, e2, e3, e4)
            # drone_guide_pc_KnF_HFKnF(scf_1, e1, e2, e3, e4)
            # drone_guide_pc_HA_R(scf_1, e1, e2, e3, e4)
            # drone_guide_pc_HA_L(scf_1, e1, e2, e3, e4)

            
            # Threads join
            pos_state_thread.join()
    
            time.sleep(3)

            # logconf_1.stop()
            logconf_2.stop()

