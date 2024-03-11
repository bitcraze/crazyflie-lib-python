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
uri_1 = 'radio://0/80/2M/E7E7E7E710' # Drone's uri
uri_2 = 'radio://0/80/2M/E7E7E7E7E7' # Leg sensor's uri

init_H = float(0.7)  # Initial drone's height; unit: m

max_ROM = 0.83   # change this variable according to the selected movement
ori_pos = 0.46    # original leg's sensor height
move_dist = max_ROM - ori_pos  # total moving distant for drone and leg's sensor

start_pos_d = 0.3 + init_H   # start position for drone

task_Vel = 0.3  # on-task velocity

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
                                              

def drone_guide_pc_KnF_HFKnF_for(scf, event1, event2, event3): 
    with PositionHlCommander(
            scf,
            x=1.0, y=0.0, z=0.0,
            default_velocity=task_Vel,
            default_height=0.3,
            controller=PositionHlCommander.CONTROLLER_PID) as pc:

        # time.sleep(0.3/0.2)

        t_zero = time.time()
        print("before going up") # the drone reaches the default take-off height 0.3 m

        pc.up(init_H)
        time.sleep(0.5) # Hovering for 1 sec after reaching the init_H + 0.3 m

        print("start!!!")

        for i in range(1,6):

            print("Round: ", i)
            t_start = time.time()

            for j in range(1,6):

                print("move up 5 cm, round: ", j)
                pc.up(0.05) 
                time.sleep(0.05/task_Vel)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            if position_estimate_1[2] > start_pos_d + move_dist:
                over_dist = position_estimate_1[2] - (start_pos_d + move_dist) 
                print("over the upper limit (m): ", over_dist)
                pc.down(over_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                time.sleep(over_dist/task_Vel)
                print("after adjusting")
                print(pc.get_position())


            while not event2.is_set():
                print("You haven't reached the target")


            print("subject and drone reached the target")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            ## Return process (with feedback)
            for k in range(1,6):

                print("move down 5 cm, round: ", k)
                pc.down(0.05) 
                time.sleep(0.05/task_Vel)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            # time.sleep(0.1)    

            if position_estimate_1[2] < start_pos_d:
                under_dist = start_pos_d - position_estimate_1[2] 
                print("under the lower limit (m): ", under_dist)
                pc.up(under_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                time.sleep(under_dist/task_Vel)
                print("after adjusting")
                print(pc.get_position())


            while not event2.is_set():
                print("You haven't returned to the start point")


            print("subject and drone reached the start point")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            print("Ready?")
            time.sleep(0.2)  # hovering for 0.5 sec
            
            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per round: ", TpR)

            print("next!!!")

                 
        print("Task done")
        TpT = t_end - t_zero
        print("Total time: ", TpT)
        # set the event for turning off the sound feedback process
        event1.set()


def drone_guide_pc_KnF_HFKnF(scf, event1, event2, event3): 
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
        time.sleep(1) # Hovering for 1 sec after reaching the init_H + 0.3 m

        print("start!!!")

        for i in range(1,11):

            print("Round: ", i)
            t_start = time.time()

            while position_estimate_1[2] < start_pos_d + move_dist:

                print("move up 5 cm")
                pc.up(0.05) 
                time.sleep(0.05/task_Vel + 0.05)

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            if position_estimate_1[2] > start_pos_d + move_dist:
                over_dist = position_estimate_1[2] - (start_pos_d + move_dist) 
                print("over the upper limit (m): ", over_dist)
                pc.down(over_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                time.sleep(over_dist/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())


            while not event2.is_set():
                print("You haven't reached the target")


            print("subject and drone reached the target")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            ## Return process (with feedback)
            while position_estimate_1[2] > start_pos_d:

                print("move down 5 cm")
                pc.down(0.05) 
                time.sleep(0.05/task_Vel + 0.05)

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            # time.sleep(0.1)    

            if position_estimate_1[2] < start_pos_d:
                under_dist = start_pos_d - position_estimate_1[2] 
                print("under the lower limit (m): ", under_dist)
                pc.up(under_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                time.sleep(under_dist/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())


            while abs(position_estimate_2[2] - ori_pos) > 0.04:
                print("You haven't returned to the start point")


            print("subject and drone reached the start point")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            print("Ready?")
            time.sleep(0.5)  # hovering for 0.5 sec
            
            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per round: ", TpR)

            print("next!!!")

                 
        print("Task done")
        TpT = t_end - t_zero
        print("Total time: ", TpT)
        # set the event for turning off the sound feedback process
        event1.set()


def drone_guide_pc_HE_for(scf, event1, event2, event3): 
    
    dz = 0.05
    per = 0.7
    dist = math.sqrt((per*dz)*(per*dz) + dz*dz)
    
    with PositionHlCommander(
            scf,
            x=1.0, y=0.0, z=0.0,
            default_velocity=task_Vel,
            default_height=0.3,
            controller=PositionHlCommander.CONTROLLER_PID) as pc:

        time.sleep(0.3/0.2)

        t_zero = time.time()
        print("before going up") # the drone reaches the default take-off height 0.3 m

        pc.up(init_H)
        time.sleep(1) # Hovering for 1 sec after reaching the init_H + 0.3 m

        print("start!!!")

        for i in range(1,6):

            print("Round: ", i)
            t_start = time.time()

            for j in range(1,6):

                print("move up-backward 5 cm, round: ", j)
                pc.move_distance(-(per*dz), 0.0, dz)
                time.sleep(dist/task_Vel + 0.05)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            if position_estimate_1[2] > start_pos_d + move_dist:
                over_dist = position_estimate_1[2] - (start_pos_d + move_dist) 
                print("over the upper limit (m): ", over_dist)
                pc.move_distance(per*over_dist, 0.0, -over_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                dist_o = math.sqrt((per*over_dist)*(per*over_dist) + over_dist*over_dist)
                time.sleep(dist_o/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())


            while not event2.is_set():
                print("You haven't reached the target")


            print("subject and drone reached the target")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            ## Return process (with feedback)
            for k in range(1,6):

                print("move down-forward 5 cm, round: ", k)
                pc.move_distance((per*dz), 0.0, -dz)
                time.sleep(dist/task_Vel + 0.05)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            # time.sleep(0.1)    

            if position_estimate_1[2] < start_pos_d:
                under_dist = start_pos_d - position_estimate_1[2] 
                print("under the lower limit (m): ", under_dist)
                pc.move_distance(-(per*under_dist), 0.0, under_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                dist_u = math.sqrt((per*under_dist)*(per*under_dist) + under_dist*under_dist)
                time.sleep(dist_u/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())

            while not event2.is_set():
                print("You haven't returned to the start point")

            print("subject and drone reached the start point")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            print("Ready?")
            time.sleep(0.2)  # hovering for 0.5 sec
            
            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per round: ", TpR)

            print("next!!!")

                 
        print("Task done")
        TpT = t_end - t_zero
        print("Total time: ", TpT)
        # set the event for turning off the sound feedback process
        event1.set()


def drone_guide_pc_HE(scf, event1, event2, event3): 
    
    dz = 0.05
    dist = math.sqrt((0.7*dz)*(0.7*dz) + dz*dz)
    
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
        time.sleep(1) # Hovering for 1 sec after reaching the init_H + 0.3 m

        print("start!!!")

        for i in range(1,11):

            print("Round: ", i)
            t_start = time.time()

            while position_estimate_1[2] < start_pos_d + move_dist:

                print("move up-backward 5 cm")
                pc.move_distance(-(0.7*dz), 0.0, dz)
                time.sleep(dist/task_Vel + 0.05)

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            if position_estimate_1[2] > start_pos_d + move_dist:
                over_dist = position_estimate_1[2] - (start_pos_d + move_dist) 
                print("over the upper limit (m): ", over_dist)
                pc.move_distance(0.7*over_dist, 0.0, -over_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                dist_o = math.sqrt((0.7*over_dist)*(0.7*over_dist) + over_dist*over_dist)
                time.sleep(dist_o/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())


            while not event2.is_set():
                print("You haven't reached the target")


            print("subject and drone reached the target")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            ## Return process (with feedback)
            while position_estimate_1[2] > start_pos_d:

                print("move down-forward 5 cm")
                pc.move_distance((0.7*dz), 0.0, -dz)
                time.sleep(dist/task_Vel + 0.05)

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            # time.sleep(0.1)    

            if position_estimate_1[2] < start_pos_d:
                under_dist = start_pos_d - position_estimate_1[2] 
                print("under the lower limit (m): ", under_dist)
                pc.move_distance(-(0.7*under_dist), 0.0, under_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                dist_u = math.sqrt((0.7*under_dist)*(0.7*under_dist) + under_dist*under_dist)
                time.sleep(dist_u/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())

            while abs(position_estimate_2[2] - ori_pos) > 0.04:
                print("You haven't returned to the start point")

            print("subject and drone reached the start point")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            print("Ready?")
            time.sleep(0.5)  # hovering for 0.5 sec
            
            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per round: ", TpR)

            print("next!!!")

                 
        print("Task done")
        TpT = t_end - t_zero
        print("Total time: ", TpT)
        # set the event for turning off the sound feedback process
        event1.set()


def drone_guide_pc_HA_for(scf, event1, event2, event3): 
    
    dz = 0.05
    per = 1.0
    dist = math.sqrt((per*dz)*(per*dz) + dz*dz)
    
    with PositionHlCommander(
            scf,
            x=1.0, y=0.0, z=0.0,
            default_velocity=task_Vel,
            default_height=0.3,
            controller=PositionHlCommander.CONTROLLER_PID) as pc:

        time.sleep(0.3/0.2)

        t_zero = time.time()
        print("before going up") # the drone reaches the default take-off height 0.3 m

        pc.up(init_H)
        time.sleep(1) # Hovering for 1 sec after reaching the init_H + 0.3 m

        print("start!!!")

        for i in range(1,6):

            print("Round: ", i)
            t_start = time.time()

            for j in range(1,6):

                print("move up-right 5 cm, round: ", j)
                pc.move_distance(0.0, -(per*dz), dz)
                time.sleep(dist/task_Vel + 0.05)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            if position_estimate_1[2] > start_pos_d + move_dist:
                over_dist = position_estimate_1[2] - (start_pos_d + move_dist) 
                print("over the upper limit (m): ", over_dist)
                pc.move_distance(0.0, per*over_dist, -over_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                dist_o = math.sqrt((per*over_dist)*(per*over_dist) + over_dist*over_dist)
                time.sleep(dist_o/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())


            while not event2.is_set():
                print("You haven't reached the target")


            print("subject and drone reached the target")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            ## Return process (with feedback)
            for k in range(1,6):

                print("move down-left 5 cm, round: ", k)
                pc.move_distance(0.0, (per*dz), -dz)
                time.sleep(dist/task_Vel + 0.05)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            # time.sleep(0.1)    

            if position_estimate_1[2] < start_pos_d:
                under_dist = start_pos_d - position_estimate_1[2] 
                print("under the lower limit (m): ", under_dist)
                pc.move_distance(0.0, -(per*under_dist), under_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                dist_u = math.sqrt((per*under_dist)*(per*under_dist) + under_dist*under_dist)
                time.sleep(dist_u/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())

            while not event2.is_set():
                print("You haven't returned to the start point")

            print("subject and drone reached the start point")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            print("Ready?")
            time.sleep(0.2)  # hovering for 0.5 sec
            
            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per round: ", TpR)

            print("next!!!")

                 
        print("Task done")
        TpT = t_end - t_zero
        print("Total time: ", TpT)
        # set the event for turning off the sound feedback process
        event1.set()


def drone_guide_pc_HA(scf, event1, event2, event3): 
    
    dz = 0.05
    dist = math.sqrt(dz*dz + dz*dz)
    
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
        time.sleep(1) # Hovering for 1 sec after reaching the init_H + 0.3 m

        print("start!!!")

        for i in range(1,11):

            print("Round: ", i)
            t_start = time.time()

            while position_estimate_1[2] < start_pos_d + move_dist:

                print("move up-right 5 cm")
                pc.move_distance(0.0, -dz, dz)
                time.sleep(dist/task_Vel + 0.05)

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            if position_estimate_1[2] > start_pos_d + move_dist:
                over_dist = position_estimate_1[2] - (start_pos_d + move_dist) 
                print("over the upper limit (m): ", over_dist)
                pc.move_distance(0.0, over_dist, -over_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                dist_o = math.sqrt(over_dist*over_dist + over_dist*over_dist)
                time.sleep(dist_o/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())


            while not event2.is_set():
                print("You haven't reached the target")


            print("subject and drone reached the target")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            ## Return process (with feedback)
            while position_estimate_1[2] > start_pos_d:

                print("move down-left 5 cm")
                pc.move_distance(0.0, dz, -dz)
                time.sleep(dist/task_Vel + 0.05)

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            # time.sleep(0.1)    

            if position_estimate_1[2] < start_pos_d:
                under_dist = start_pos_d - position_estimate_1[2] 
                print("under the lower limit (m): ", under_dist)
                pc.move_distance(0.0, -under_dist, under_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                dist_u = math.sqrt(under_dist*under_dist + under_dist*under_dist)
                time.sleep(dist_u/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())

            while abs(position_estimate_2[2] - ori_pos) > 0.04:
                print("You haven't returned to the start point")

            print("subject and drone reached the start point")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            print("Ready?")
            time.sleep(0.5)  # hovering for 0.5 sec
            
            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per round: ", TpR)

            print("next!!!")

                 
        print("Task done")
        TpT = t_end - t_zero
        print("Total time: ", TpT)
        # set the event for turning off the sound feedback process
        event1.set()


def drone_guide_pc_tiptoe_for(scf, event1, event2, event3): 
    
    dz = 0.05
    per = 1.0
    dist = math.sqrt((per*dz)*(per*dz) + dz*dz)
    
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
        time.sleep(1) # Hovering for 1 sec after reaching the init_H + 0.3 m

        print("start!!!")

        for i in range(1,11):

            print("Round: ", i)
            t_start = time.time()

            for j in range(1,7):

                print("move up-forward 5 cm, round: ", j)
                pc.move_distance((per*dz), 0.0, dz)
                time.sleep(dist/task_Vel + 0.05)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            if position_estimate_1[2] > start_pos_d + move_dist:
                over_dist = position_estimate_1[2] - (start_pos_d + move_dist) 
                print("over the upper limit (m): ", over_dist)
                pc.move_distance(-per*over_dist, 0.0, -over_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                dist_o = math.sqrt((per*over_dist)*(per*over_dist) + over_dist*over_dist)
                time.sleep(dist_o/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())


            while not event2.is_set():
                print("You haven't reached the target")


            print("subject and drone reached the target")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            ## Return process (with feedback)
            for k in range(1,7):

                print("move down-backward 5 cm, round: ", k)
                pc.move_distance(-dz, 0.0, -dz)
                time.sleep(dist/task_Vel + 0.05)
                print(pc.get_position())

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            # time.sleep(0.1)    

            if position_estimate_1[2] < start_pos_d:
                under_dist = start_pos_d - position_estimate_1[2] 
                print("under the lower limit (m): ", under_dist)
                pc.move_distance((per*under_dist), 0.0, under_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                dist_u = math.sqrt((per*under_dist)*(per*under_dist) + under_dist*under_dist)
                time.sleep(dist_u/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())

            while not event2.is_set():
                print("You haven't returned to the start point")

            print("subject and drone reached the start point")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            print("Ready?")
            time.sleep(0.2)  # hovering for 0.5 sec
            
            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per round: ", TpR)

            print("next!!!")

                 
        print("Task done")
        TpT = t_end - t_zero
        print("Total time: ", TpT)
        # set the event for turning off the sound feedback process
        event1.set()


def drone_guide_pc_tiptoe(scf, event1, event2, event3): 
    
    dz = 0.05
    dist = math.sqrt(dz*dz + dz*dz)
    
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
        time.sleep(1) # Hovering for 1 sec after reaching the init_H + 0.3 m

        print("start!!!")

        for i in range(1,11):

            print("Round: ", i)
            t_start = time.time()

            while position_estimate_1[2] < start_pos_d + move_dist:

                print("move up-forward 5 cm")
                pc.move_distance(dz, 0.0, dz)
                time.sleep(dist/task_Vel + 0.05)

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            if position_estimate_1[2] > start_pos_d + move_dist:
                over_dist = position_estimate_1[2] - (start_pos_d + move_dist) 
                print("over the upper limit (m): ", over_dist)
                pc.move_distance(-over_dist, 0.0, -over_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                dist_o = math.sqrt(over_dist*over_dist + over_dist*over_dist)
                time.sleep(dist_o/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())


            while not event2.is_set():
                print("You haven't reached the target")


            print("subject and drone reached the target")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            ## Return process (with feedback)
            while position_estimate_1[2] > start_pos_d:

                print("move down-backward 5 cm")
                pc.move_distance(-dz, 0.0, -dz)
                time.sleep(dist/task_Vel + 0.05)

                while event3.is_set()==True:  # the subject doesn't follow the drone
                    print("please follow the drone")
                    # time.sleep(0.1)

            # time.sleep(0.1)    

            if position_estimate_1[2] < start_pos_d:
                under_dist = start_pos_d - position_estimate_1[2] 
                print("under the lower limit (m): ", under_dist)
                pc.move_distance(under_dist, 0.0, under_dist)  # moving down to the start_pos_d + move_dist within 0.2 second
                dist_u = math.sqrt(under_dist*under_dist + under_dist*under_dist)
                time.sleep(dist_u/task_Vel + 0.05)
                print("after adjusting")
                print(pc.get_position())

            while abs(position_estimate_2[2] - ori_pos) > 0.04:
                print("You haven't returned to the start point")

            print("subject and drone reached the start point")
            print(pc.get_position())
            time.sleep(0.2) # for subject's preparation

            
            print("Ready?")
            time.sleep(0.5)  # hovering for 0.5 sec
            
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
        
        # If the current leg sensor's position reaches the max ROM in z-axis
        if abs(position_estimate_2[2] - max_ROM) < 0.03 or abs(position_estimate_2[2] - ori_pos) < 0.03: # subject hasn't reached the max ROM yet
            # print("target reached!")
            event2.set()
        
            if abs(abs(position_estimate_2[2] - ori_pos)-abs(position_estimate_1[2] - start_pos_d)) < 0.03:  # subject follows the drone
                # print("good job")
                event3.clear()

            else:
                # print("please follow the drone")
                event3.set()
            
        else:   
            # print("keep going")
            event2.clear()

            if abs(abs(position_estimate_2[2] - ori_pos)-abs(position_estimate_1[2] - start_pos_d)) < 0.03:  # subject follows the drone
                # print("good job")
                event3.clear()

            else:
                # print("please follow the drone")
                event3.set()


    print("Finish guiding")

def sound_feedback(event1, event2, event3):
    print("sound thread started")
    while not event1.is_set():  # the drone hasn't finished the guiding yet
               
        if event3.is_set()==True and abs(position_estimate_2[2] - ori_pos) < abs(position_estimate_1[2] - start_pos_d):
            print("Too low")
            # frequency = 1500  # Set Frequency To 2500 Hertz
            # duration = 500  # Set Duration To 250 ms == 0.25 second
            # winsound.Beep(frequency, duration)
            winsound.PlaySound('Lower_Alarm.wav', winsound.SND_FILENAME)
        
        elif event3.is_set()==True and abs(position_estimate_2[2] - ori_pos) > abs(position_estimate_1[2] - start_pos_d):
            print("Too high")
            # frequency = 1500  # Set Frequency To 2500 Hertz
            # duration = 200  # Set Duration To 250 ms == 0.25 second
            # winsound.Beep(frequency, duration)
            winsound.PlaySound('Higher_Alarm.mp3', winsound.SND_FILENAME)
        
        # elif event3.is_set()==False and event2.is_set()==False:
        #     print("Good job!")
 
        elif event3.is_set()==False and event2.is_set()==True:
            print("You did it!")
            # winsound.PlaySound('_short-success.mp3', winsound.SND_FILENAME)
            winsound.PlaySound('Success.wav', winsound.SND_FILENAME)
       
        else:
            pass
            
        time.sleep(0.2)


# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


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


        # # Drone Motion (MotionCommander)
            # Declaring threads for feedback providing
            pos_state_thread = threading.Thread(name='Position-State-Change-Thread', target=position_state_change, args=(e1, e2, e3))
            sound_thread = threading.Thread(name='Sound-Feedback-Thread', target=sound_feedback, args=(e1, e2, e3))

            # Starting threads for drone motion
            pos_state_thread.start()
            sound_thread.start()

            # Perform the drone guiding task
            drone_guide_pc_KnF_HFKnF_for(scf_1, e1, e2, e3)
            # drone_guide_pc_KnF_HFKnF(scf_1, e1, e2, e3)
            # drone_guide_pc_HA_for(scf_1, e1, e2, e3)
            # drone_guide_pc_HA(scf_1, e1, e2, e3)
            # drone_guide_pc_HE_for(scf_1, e1, e2, e3)
            # drone_guide_pc_HE(scf_1, e1, e2, e3)
            # drone_guide_pc_tiptoe_for(scf_1, e1, e2, e3)
            # drone_guide_pc_tiptoe(scf_1, e1, e2, e3)
            
            # Threads join
            pos_state_thread.join()
            sound_thread.join()
    
            
            time.sleep(3)

            logconf_1.stop()
            logconf_2.stop()

