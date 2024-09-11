import time
import logging
import cflib.crtp
import threading
import winsound

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.position_hl_commander import PositionHlCommander
from cflib.crazyflie.log import LogConfig

'''
Changing these parameters for every trials
1. uri_1: changing based on the drone's uri
2. uncomment Line 30-32 and comment Line 34-36 for right-side trial
   uncomment Line 34-36 and comment Line 30-32 for left-side trial 
3. bt: adjusting break time between trials (No need to change)
4. ori_pos_x: changing based on subject's initial position (get this value from Crazyflie Client's Lighthouse tab)
5. first_step_pos_x :  changing based on the position of the subject when doing one-step heel-to-toe and leaning forward to straigthening his/her leg (with tag) perpendicular to the ground (get this value from Crazyflie Client's Lighthouse tab)
'''

# URI to the Crazyflie to connect to
uri_1 = 'radio://0/80/2M/E7E7E7E701' # Drone's uri
uri_2 = 'radio://0/80/2M/E7E7E7E7E9' # Leg sensor1's uri


init_H = float(0.0)  # Initial drone's height; unit: m
start_pos_d = 0.3 + init_H   # start z-position for drone

# # # for right side lighthouse
# start_x = float(-0.29)  # initial pos_X of the drone; unit: m
# start_y = float(0.21)  # initial pos_y of the drone; unit: m

# for left side lighthouse
start_x = float(-0.31)  # initial pos_X of the drone; unit: m
start_y = float(-0.17)  # initial pos_y of the drone; unit: m

step = 6   # repeat = rep-1; same for both testing and training uwu
task_Vel = 0.1  # on-task velocity
#bt = 2  # break time between trials; unit: second

ori_pos_x = -0.85  # original tag position in x-axis; unit: m
first_step_pos_x = -0.38  # tag position in x-axis after first step; unit: m

# for heel-to-toe (5 steps)
dx = abs(ori_pos_x-first_step_pos_x)   # two step length
# tot_dist = step*dx    # total moving distance
ds = 2*dx   # one task length

diff_x = abs(start_x - ori_pos_x)  # initial diff between drone and tag (ideally constant)

position_estimate_1 = [0, 0, 0]  # Drone's pos
position_estimate_2 = [0, 0, 0]  # LS1's pos



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


def drone_guide_pc_HtH(scf, event1, event2): 

    with PositionHlCommander(
            scf,
            x=start_x, y=start_y, z=0.0,
            default_velocity=task_Vel,
            default_height=0.3,
            controller=PositionHlCommander.CONTROLLER_PID) as pc:

        t_zero = time.time()
        print("before going up") # the drone reaches the default take-off height 0.3 m

        pc.up(init_H)
        time.sleep(init_H/task_Vel)
        print(pc.get_position())

        print("start!!!")
        winsound.PlaySound('game-start-6104.wav', winsound.SND_FILENAME)

        for i in range(1,step):

            print("move forward, step: ", i)
            t_start = time.time()

            pc.move_distance(dx, 0.0, 0.0)
            time.sleep(abs(dx)/task_Vel)
            print(pc.get_position())

            # while not event2.is_set():  # the subject doesn't follow the drone's step
            #     print("please step forward to follow the drone")
            #     # time.sleep(0.1)

            # print("Half step already! Keep going!")
            # # winsound.PlaySound('Success.wav', winsound.SND_FILENAME)
            # time.sleep(2)

            # pc.move_distance(dx, 0.0, 0.0)
            # time.sleep(abs(dx)/task_Vel)
            # print(pc.get_position())


            while not event2.is_set():  # the subject doesn't follow the drone's step
                print("please step forward to follow the drone")
                # time.sleep(0.1)

            print("Good job! Next step!")
            winsound.PlaySound('Success.wav', winsound.SND_FILENAME)

            t_end = time.time()
            TpR = t_end - t_start   # total time per round (second)
            print("Total time per step ", i, ": ", TpR)
           # time.sleep(bt)      # break time between trials; unit: second
            print("next!!!")
            

        print("subject and drone reached the end point")
        winsound.PlaySound('_short-success.wav', winsound.SND_FILENAME)
        print(pc.get_position())

        # set the event for turning off the sound feedback process
        event1.set()

        print("Task done")
        TpT = t_end - t_zero
        print("Total time: ", TpT)

        

# # Feedback Section

def position_state_change(event1, event2):
    print("position thread start")
    while not event1.is_set():  # the drone hasn't finished the guiding yet
        
        
        if abs(abs(position_estimate_1[0]-position_estimate_2[0])-diff_x) < 0.05: 
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
