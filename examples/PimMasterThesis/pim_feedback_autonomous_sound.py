import logging
import time
import cflib.crtp
import concurrent.futures
import queue
import threading
import winsound

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.position_hl_commander import PositionHlCommander
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.mem import MemoryElement

# URI to the Crazyflie to connect to
uri_1 = 'radio://0/80/2M/E7E7E7E701'
uri_2 = 'radio://0/80/2M/E7E7E7E704'
uri_3 = 'radio://0/80/2M/E7E7E7E705' # always lost connection after few minutes (maybe only few seconds?) 

# Input params
print("Please Enter Default Height: ")
DEFAULT_HEIGHT = input()    # initial height level of Crazyflie after taking off (default = 0.7)
DEFAULT_HEIGHT = float(DEFAULT_HEIGHT)
print("Please Enter Absolute Distance: ")
d_abs = input()      
d_abs = float(d_abs)       # entire distance from initial to end (i.e. a distance from ground to subject's wrist when he lift his arm up at the maximum height)  
d_fly = d_abs - DEFAULT_HEIGHT       # flying distance of Crazyflie 
d_th = 0.2   # Threshold of error between WS sensor and Crazyflie (threshold = 0.1 m = 10 cm)

position_estimate_1 = [0, 0, 0]
position_estimate_2 = [0, 0, 0]
position_estimate_3 = [0, 0, 0]


# # Positioning Callback Section

def log_pos_callback_1(uri_1, timestamp, data, logconf_1):
    global position_estimate_1
    position_estimate_1[0] = data['kalman.stateX']
    position_estimate_1[1] = data['kalman.stateY']
    position_estimate_1[2] = data['kalman.stateZ']
    print("{}: {} is at pos: ({}, {}, {})".format(timestamp, uri_1, position_estimate_1[0], position_estimate_1[1],
                                            position_estimate_1[2]))

def log_pos_callback_2(uri_2, timestamp, data, logconf_2):
    global position_estimate_2
    position_estimate_2[0] = data['kalman.stateX']
    position_estimate_2[1] = data['kalman.stateY']
    position_estimate_2[2] = data['kalman.stateZ']
    print("{}: {} is at pos: ({}, {}, {})".format(timestamp, uri_2, position_estimate_2[0], 
                                              position_estimate_2[1], position_estimate_2[2]))

def log_pos_callback_3(uri_3, timestamp, data, logconf_3):
    global position_estimate_3
    position_estimate_3[0] = data['kalman.stateX']
    position_estimate_3[1] = data['kalman.stateY']
    position_estimate_3[2] = data['kalman.stateZ']
    print("{}: {} is at pos: ({}, {}, {})".format(timestamp, uri_3, position_estimate_3[0], position_estimate_3[1], 
                                              position_estimate_3[2]))


# # # Crazyflie Motion Section

# # Activate high level commander when using the PositionHlCommander
def activate_high_level_commander(cf):
    cf.param.set_value('commander.enHighLevel', '1')

# # Posture 1 (using MotionCommander)
def move_baduanjin_mc_p1(scf, event2):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:

        print("Target Height: {}".format(DEFAULT_HEIGHT))
        time.sleep(1)

        t_init = time.time()

        ## Go up: d_fly meter/6 sec
        print("Target Height: {}".format(d_abs))
        mc.move_distance(0, 0, d_fly, velocity=d_fly/6)   # the final posistion will be "d_abs = DEFAULT_HEIGHT + d_fly" 
        t1 = time.time() - t_init
        print("t1: ", t1)
        
        ## Delay 4 sec
        # mc.stop()
        time.sleep(4)
        t2 = time.time() - t_init
        print("t2: ", t2)

        ## Go down: d_fly meter/6 sec
        print("Target Height: {}".format(DEFAULT_HEIGHT))
        mc.move_distance(0, 0, -d_fly, velocity=d_fly/6)
        t3 = time.time() - t_init
        print("t3: ", t3)
        time.sleep(1)

        ## setting the event for turning off the LED feedback process
        event2.set()


# # Posture 1 (using PositionHlCommander)
def move_baduanjin_hl_p1(scf, event2):
    with PositionHlCommander(
            scf,
            x=1.4, y=2.2, z=0.0,
            default_velocity=0.5,
            default_height=0.7, # default = 0.7
            controller=PositionHlCommander.CONTROLLER_PID) as pc:
        
        print('Setting position [1.4, 2.2, {}]'.format(DEFAULT_HEIGHT))
        t_init = time.time()

        time.sleep(1)

        ## Go up: d_fly meter/6 sec
        print('Setting position [1.4, 2.2, {}]'.format(d_abs))
        pc.up(d_fly, velocity=d_fly/6)
        t1 = time.time() - t_init
        print("t1: ", t1)
        
        ## Delay 4 sec
        time.sleep(4)
        t2 = time.time() - t_init
        print("t2: ", t2)

        ## Go down: d_fly meter/6 sec
        print('Setting position [1.4, 2.2, {}]'.format(DEFAULT_HEIGHT))
        pc.down(d_fly, velocity=d_fly/6)
        t3 = time.time() - t_init
        print("t3: ", t3)
        time.sleep(1)

        # setting the event for turning off the LED feedback process
        event2.set()


# # Posture 3 (using MotionCommander)
def move_baduanjin_mc_p3(scf, event2):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:

        print("Target Height: {}".format(DEFAULT_HEIGHT))
        t_init = time.time()

        ## Delay 6 sec
        time.sleep(6)
        t1 = time.time() - t_init
        print("t1: ", t1)

        ## Go up: d_fly meter/4.5 sec
        print("Target Height: {}".format(d_abs))
        mc.move_distance(0, 0, d_fly, velocity=d_fly/4.5)   # the final posistion will be "d_abs = DEFAULT_HEIGHT + d_fly" 
        t2 = time.time() - t_init
        print("t2: ", t2)
        
        ## Delay 2.5 sec
        time.sleep(2.5)
        t3 = time.time() - t_init
        print("t3: ", t3)

        ## Go down: d_fly meter/4.5 sec
        print("Target Height: {}".format(DEFAULT_HEIGHT))
        mc.move_distance(0, 0, -d_fly, velocity=d_fly/4.5)
        t4 = time.time() - t_init
        print("t4: ", t4)
        
        ## Delay 2.5 sec
        time.sleep(2.5)
        t5 = time.time() - t_init
        print("t5: ", t5)

        ## setting the event for turning off the LED feedback process
        event2.set()


# # Posture 3 (using PositionHlCommander)
def move_baduanjin_hl_p3(scf, event2):
    with PositionHlCommander(
            scf,
            x=1.4, y=2.2, z=0.0,
            default_velocity=0.5,
            default_height=0.7, # default = 0.7
            controller=PositionHlCommander.CONTROLLER_PID) as pc:
        
        print('Setting position [1.4, 2.2, {}]'.format(DEFAULT_HEIGHT))
        t_init = time.time()

        ## Delay 6 sec
        time.sleep(6)
        t1 = time.time() - t_init
        print("t1: ", t1)

        ## Go up: d_fly meter/4.5 sec
        print('Setting position [1.4, 2.2, {}]'.format(d_abs))
        pc.up(d_fly, velocity=d_fly/4.5)
        t2 = time.time() - t_init
        print("t2: ", t2)

        ## Delay 2.5 sec
        time.sleep(2.5)
        t3 = time.time() - t_init
        print("t3: ", t3)
        
        ## Go down: d_fly meter/4.5 sec
        print('Setting position [1.4, 2.2, {}]'.format(DEFAULT_HEIGHT))
        pc.down(d_fly, velocity=d_fly/4.5)
        t4 = time.time() - t_init
        print("t4: ", t4)

        ## Delay 2.5 sec
        time.sleep(2.5)
        t5 = time.time() - t_init
        print("t5: ", t5)  

        # setting the event for turning off the LED feedback process
        event2.set()

        

# # Feedback Section

def position_state_change(event1, event2):
    while not event2.is_set():
        # if abs(position_estimate_2[2]-position_estimate_1[2]) > d_th or abs(position_estimate_3[2]-position_estimate_1[2]) > d_th:
        #     # print("---Wrist Sensor is outbounded---")
        #     event1.set()
        if abs(position_estimate_2[2]-position_estimate_1[2]) < d_th or abs(position_estimate_3[2]-position_estimate_1[2]) < d_th:
            event1.clear()
        
        else:
            event1.set()

def sound_feedback(event1, event2):
    while not event2.is_set():
        if event1.isSet()==True:
            print("Beep!!")
            frequency = 2500  # Set Frequency To 2500 Hertz
            duration = 250  # Set Duration To 250 ms == 0.25 second
            winsound.Beep(frequency, duration)
        else:
            # print("Nothing")
            pass
            
        time.sleep(0.1)



if __name__ == '__main__':

    # # initializing the queue and event object
    q = queue.Queue(maxsize=0)
    e1 = threading.Event()
    e2 = threading.Event()

    # # initializing Crazyflie 
    cflib.crtp.init_drivers(enable_debug_driver=False)
       
    with SyncCrazyflie(uri_3, cf=Crazyflie(rw_cache='./cache')) as scf_3:
        logconf_3 = LogConfig(name='Position', period_in_ms=500)
        logconf_3.add_variable('kalman.stateX', 'float')
        logconf_3.add_variable('kalman.stateY', 'float')
        logconf_3.add_variable('kalman.stateZ', 'float')        
        scf_3.cf.log.add_config(logconf_3)
        logconf_3.data_received_cb.add_callback( lambda timestamp, data, logconf_3: log_pos_callback_2(uri_3, timestamp, data, logconf_3) )

        with SyncCrazyflie(uri_2, cf=Crazyflie(rw_cache='./cache')) as scf_2:
            logconf_2 = LogConfig(name='Position', period_in_ms=500)
            logconf_2.add_variable('kalman.stateX', 'float')
            logconf_2.add_variable('kalman.stateY', 'float')
            logconf_2.add_variable('kalman.stateZ', 'float')            
            scf_2.cf.log.add_config(logconf_2)
            logconf_2.data_received_cb.add_callback( lambda timestamp, data, logconf_2: log_pos_callback_3(uri_2, timestamp, data, logconf_2) )

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

                # Starting the LED-feedback thread
                pos_state_thread = threading.Thread(name='Position-State-Change-Thread', target=position_state_change, args=(e1, e2))
                sound_thread = threading.Thread(name='Sound-Feedback-Thread', target=sound_feedback, args=(e1, e2))

                pos_state_thread.start()
                sound_thread.start()


                # # Posture 1 (MotionCommander)
                # move_baduanjin_mc_p1(scf_1, e2)

                # # Posture 1 (PositioningHlCommander)
                # activate_high_level_commander(scf_1.cf)
                # move_baduanjin_hl_p1(scf_1, e2)


                # # Posture 3 (MotionCommander)
                move_baduanjin_mc_p3(scf_1, e2)

                # # Posture 3 (PositioningHlCommander)
                # activate_high_level_commander(scf_1.cf)
                # move_baduanjin_hl_p3(scf_1, e2)
                

                pos_state_thread.join()
                sound_thread.join()
                     
                
                # time.sleep(10)

                # logconf_2.stop()
                # logconf_3.stop()

