import time
import cflib.crtp
import threading
import os

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.log import LogConfig


# URI to the Crazyflie to connect to
uri_1 = 'radio://0/80/2M/E7E7E7E702'


# Input params for P2
print("Please enter the (default) height of your chest from the ground(m): ")
DEFAULT_HEIGHT_P2 = input()    # default height level for this movement (P2) i.e. 1.3 m
DEFAULT_HEIGHT_P2 = float(DEFAULT_HEIGHT_P2)
p2_h0 = DEFAULT_HEIGHT_P2 - 0.3  # (default take-off height of Crazyflie = 0.3 m)

print("Please enter the maximum length between both legs after widening out(m): ")
max_leg_length = input()
max_leg_length = float(max_leg_length)
s1_4 = max_leg_length/2

print("Please enter the maximum arm length (R_wrist - L_wrist) after stretching out(m): ")
max_arm_length = input()
max_arm_length = float(max_arm_length)
s2_5 = max_arm_length/2

s3_6 = max_leg_length  # 0.1 m = width of your foot


# Input params for P3
print("Please enter (default) height of your hand from the ground(m): ")
DEFAULT_HEIGHT_P3 = input()   # default height level for this movement (P3) i.e. 0.7 m
DEFAULT_HEIGHT_P3 = float(DEFAULT_HEIGHT_P3)
p3_h0 = DEFAULT_HEIGHT_P3 - 0.3  # (default take-off height of Crazyflie = 0.3 m)

print("Please enter the maximum height of your wrist from the ground after raising your hand up(m): ")
max_hand_raising = input()      
max_hand_raising = float(max_hand_raising)       
p3_h1 = max_hand_raising - DEFAULT_HEIGHT_P3  


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


# # # Crazyflie Motion Section

# # Posture 2 (using MotionCommander)
def move_baduanjin_mc_p2(scf): # default take-off height = 0.3 m
    
    with MotionCommander(scf) as mc:

        t_init = time.time()

        ## Go up: h0 meter/8 sec 
        print("Target Height: {}".format(p2_h0))
        # mc.up(p2_h0, velocity=p2_h0/4)
        mc.start_up(velocity=p2_h0/4)
        t1 = time.time() - t_init
        print("t1: ", t1)

        time.sleep(4)

        mc.stop()

        ## Delay 1 sec
        time.sleep(4)


        ## Go right: s1 meter/4 sec
        print("Target Length (right): {}".format(s1_4))
        # mc.right(s1_4, velocity=s1_4/2) 
        mc.start_right(velocity=s1_4/2)  
        t2 = time.time() - t_init
        print("t2: ", t2)

        time.sleep(2)

        mc.stop()
        
        ## Delay 1 sec
        time.sleep(2)

        ## Go right: s2 meter/3 sec
        print("Target Length (right): {}".format(s2_5))
        # mc.right(s2_5, velocity=s2_5/2)
        mc.start_right(velocity=s2_5/2)  
        t3 = time.time() - t_init
        print("t3: ", t3)

        time.sleep(2)

        mc.stop()

        ## Delay 1 sec
        time.sleep(2)
        
        ## Go left: s3 meter/5 sec
        print("Target Length (left): {}".format(s3_6))
        # mc.left(s3_6+0.1, velocity=(s3_6+0.1)/3) 
        mc.start_left(velocity=(s3_6+0.1)/3)  
        t4 = time.time() - t_init
        print("t4: ", t4)

        time.sleep(3)

        mc.stop()

        ## Delay 1 sec
        time.sleep(2)


        ### Move to another side (left side)
        
        ## Go left: s4 meter/2 sec
        print("Target Length (left): {}".format(s1_4))
        # mc.left(s1_4, velocity=s1_4/1.5)  
        mc.start_left(velocity=s1_4/1.5) 
        t5 = time.time() - t_init
        print("t5: ", t5)

        time.sleep(1.5)

        mc.stop()

        ## Delay 1 sec
        time.sleep(2)

        ## Go left: s5 meter/2 sec
        print("Target Length (left): {}".format(s2_5))
        # mc.left(s2_5, velocity=s2_5/2)
        mc.start_left(velocity=s2_5/2)  
        t6 = time.time() - t_init
        print("t6: ", t6)

        time.sleep(2)

        mc.stop()

        ## Delay 1 sec
        time.sleep(2)

        ## Go right: s6 meter/5 sec
        print("Target Length (right): {}".format(s3_6))
        # mc.right(s3_6+0.1, velocity=(s3_6+0.1)/3)  
        mc.start_right(velocity=(s3_6+0.1)/3) 
        t7 = time.time() - t_init
        print("t7: ", t7)

        time.sleep(3)

        mc.stop()

        ## Delay 5 sec
        time.sleep(3)

      

# # Posture 3 (using MotionCommander)
def move_baduanjin_mc_p3(scf):


    with MotionCommander(scf) as mc:

        t_init = time.time()

        ## Go up: p3_h0 meter/8 sec
        print("Target Height: {}".format(p3_h0))
        # mc.up(p3_h0, velocity=p3_h0/3) 
        mc.start_up(velocity=p3_h0/3) 
        t1 = time.time() - t_init
        print("t1: ", t1)

        time.sleep(3)

        mc.stop()
        
        ## Delay 2 sec
        time.sleep(5.5)
        t2 = time.time() - t_init
        print("t2: ", t2)


        ## Go up: p3_h1 meter/5 sec
        print("Target Height: {}".format(p3_h1))
        # mc.up(p3_h1, velocity=p3_h1/5)  
        mc.start_up(velocity=p3_h1/3.75)  
        t3 = time.time() - t_init
        print("t3: ", t3)
        
        time.sleep(3.75)

        mc.stop()


        ## Delay 3 sec
        time.sleep(3.5)
        t4 = time.time() - t_init
        print("t4: ", t4)

        ## Go down: p3_h1 meter/4 sec
        print("Target Height: {}".format(p3_h1))
        # mc.down(p3_h1, velocity=p3_h1/3) 
        mc.start_down(velocity=(p3_h1-0.1)/3)  
        t5 = time.time() - t_init
        print("t5: ", t5)

        time.sleep(3)

        mc.stop()


        ## Delay 2 sec
        time.sleep(3)
        t6 = time.time() - t_init
        print("t6: ", t6)


        ### Move to another side (left side)

        ## Go up: p3_h1 meter/5 sec
        print("Target Height: {}".format(p3_h1))
        # mc.up(p3_h1, velocity=p3_h1/3.5)  
        mc.start_up(velocity=p3_h1/3.5) 
        t7 = time.time() - t_init
        print("t7: ", t7)

        time.sleep(3.5)

        mc.stop()

        ## Delay 2 sec
        time.sleep(3.75)
        t8 = time.time() - t_init
        print("t8: ", t8)

        ## Go down: p3_h1 meter/5 sec
        print("Target Height: {}".format(p3_h1))
        # mc.down(p3_h1, velocity=(p3_h1-0.1)/3.25)  
        mc.start_down(velocity=(p3_h1-0.1)/3.25)
        t9 = time.time() - t_init
        print("t9: ", t9)

        time.sleep(3.25)

        mc.stop()

        ## Delay 5 sec
        time.sleep(2)




# # Open Baduanjin Sound

def open_baduanjin_sound_p2():
    os.startfile('p2_1_2.mp4')

def open_baduanjin_sound_p3():
    os.startfile('p3_1_2.mp4')



if __name__ == '__main__':

    # # initializing Crazyflie 
    cflib.crtp.init_drivers(enable_debug_driver=False)
       
    
    with SyncCrazyflie(uri_1, cf=Crazyflie(rw_cache='./cache')) as scf_1:
        logconf_1 = LogConfig(name='Position', period_in_ms=500)
        logconf_1.add_variable('kalman.stateX', 'float')
        logconf_1.add_variable('kalman.stateY', 'float')
        logconf_1.add_variable('kalman.stateZ', 'float')        
        scf_1.cf.log.add_config(logconf_1)
        logconf_1.data_received_cb.add_callback( lambda timestamp, data, logconf_1: log_pos_callback_1(uri_1, timestamp, data, logconf_1) )

        logconf_1.start()

        time.sleep(3)


    # # Movement no.2 (MotionCommander)
        # Declaring feedback threads for movement no.2
        baduanjin_sound_thread_p2 = threading.Thread(name='P2-Baduanjin-Sound-Thread', target=open_baduanjin_sound_p2, args=()) 
        
        # Starting threads for movement no.2
        baduanjin_sound_thread_p2.start()

        # Perform the movement
        move_baduanjin_mc_p2(scf_1)
        
        # Threads join
        baduanjin_sound_thread_p2.join()



    # # # Movement no.3 (MotionCommander)
    #     # Declaring feedback threads for movement no.3
    #     baduanjin_sound_thread_p3 = threading.Thread(name='P2-Baduanjin-Sound-Thread', target=open_baduanjin_sound_p3, args=()) 
        
    
    #     # Starting threads for movement no.3
    #     baduanjin_sound_thread_p3.start()
 
    #     # Perform the movement
    #     move_baduanjin_mc_p3(scf_1)

    #     # Threads join  
    #     baduanjin_sound_thread_p3.join()
        
        

        time.sleep(3)

        logconf_1.stop()

