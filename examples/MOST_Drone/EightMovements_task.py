import time
import cflib.crtp
import queue
import threading
import winsound

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.log import LogConfig


# URI to the Crazyflie to connect to
uri_1 = 'radio://0/80/2M/E7E7E7E706' # Drone's uri
uri_2 = 'radio://0/80/2M/E7E7E7E7E7' # Leg sensor's uri

init_H = float(0.7)  # Initial drone's height; unit: m
final_H = float(1.0)  # Final drone's height; unit: m
max_leg_raising = float(0.4)  # maximum leg raising; unit: m
init_Vel = 0.5  # Initial velocity
task_Vel = 0.5  # on-task velocity


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

def drone_guide_mc(scf, event2): # default take-off height = 0.3 m

    with MotionCommander(scf) as mc:
        mc.up(init_H, velocity=init_Vel)
        time.sleep(2)

        for i in range(1,6):
            print("Round: ", i)

            # mc.up(max_leg_raising, velocity=task_Vel)
            # time.sleep(0.8)
            # mc.down(max_leg_raising, velocity=task_Vel)
            # time.sleep(1.5)

            mc.move_distance(0.4, 0, 0.4, velocity=task_Vel)
            time.sleep(0.8)
            mc.move_distance(-0.4, 0, -0.4, velocity=task_Vel)
            time.sleep(1.5)

        # set the event for turning off the sound feedback process
        event2.set()


# # Feedback Section

def position_state_change(event1, event2):
    print("position thread start")
    while not event2.is_set():  # the drone hasn't finished the guiding yet
        if position_estimate_2[2] < max_leg_raising:
            event1.clear()
        
        else:
            event1.set() # subject reaches the target point


def sound_feedback(event1, event2):
    print("sound thread started")
    while not event2.is_set():  # the drone hasn't finished the guiding yet
        if event1.isSet()==True:  # subject reaches the target point
            print("Good Job!")
            frequency = 2500  # Set Frequency To 2500 Hertz
            duration = 500  # Set Duration To 250 ms == 0.25 second
            winsound.Beep(frequency, duration)
        else:
            pass
            
        time.sleep(0.1)


if __name__ == '__main__':

    # # initializing the queue and event object
    q = queue.Queue(maxsize=0)
    e1 = threading.Event()  # Checking whether the drone completes its task?
    e2 = threading.Event()  # Checking whether the Subject reaches the target height?

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
            sound_thread = threading.Thread(name='Sound-Feedback-Thread', target=sound_feedback, args=(e1, e2))

            # Starting threads for drone motion
            pos_state_thread.start()
            sound_thread.start()

            # Perform the drone guiding task
            drone_guide_mc(scf_1, e2)
            
            # Threads join
            pos_state_thread.join()
            sound_thread.join()
    
            
            time.sleep(3)

            logconf_1.stop()
            logconf_2.stop()

