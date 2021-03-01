import time
import cflib.crtp

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.position_hl_commander import PositionHlCommander
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.log import LogConfig
from csv import DictWriter


# URI to the Crazyflie to connect to
uri_1 = 'radio://0/80/2M/E7E7E7E701'


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

# # Create a csv file section

# # Create a csv file
with open('pos_callback.csv', 'w', newline='') as csv_file:
    field_names = ['timestamp', 'uri', 'x(m)', 'y(m)', 'z(m)']
    writer = DictWriter(csv_file, fieldnames=field_names)
    # Write a header of the csv
    writer.writeheader()
    
# # append data into csv 
def append_dict_as_row(file_name, dict_of_elem, field_names):
    # Open file in append mode
    with open(file_name, 'a+', newline='') as write_obj:
        # Create a writer object from csv module
        dict_writer = DictWriter(write_obj, fieldnames=field_names)
        # Add dictionary as row in the csv
        dict_writer.writerow(dict_of_elem)  

        
# # Positioning Callback Section

def log_pos_callback_1(uri_1, timestamp, data, logconf_1):
    global position_estimate_1
    position_estimate_1[0] = data['kalman.stateX']
    position_estimate_1[1] = data['kalman.stateY']
    position_estimate_1[2] = data['kalman.stateZ']
    print("{}: {} is at pos: ({}, {}, {})".format(timestamp, uri_1, position_estimate_1[0], position_estimate_1[1],
                                            position_estimate_1[2]))
    
    field_names = ['timestamp', 'uri', 'x(m)', 'y(m)', 'z(m)']
    row_dict = {'timestamp': timestamp, 'uri': uri_1, 'x(m)': position_estimate_1[0], 'y(m)': position_estimate_1[1], 'z(m)': position_estimate_1[2]}
    append_dict_as_row('pos_callback.csv', row_dict, field_names)


# # # Crazyflie Motion Section

# # Activate high level commander when using the PositionHlCommander
def activate_high_level_commander(cf):
    cf.param.set_value('commander.enHighLevel', '1')

# # Posture 1 (using MotionCommander)
def move_baduanjin_mc_p1(scf):
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



# # Posture 1 (using PositionHlCommander)
def move_baduanjin_hl_p1(scf):
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



# # Posture 3 (using MotionCommander)
def move_baduanjin_mc_p3(scf):
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

  


# # Posture 3 (using PositionHlCommander)
def move_baduanjin_hl_p3(scf):
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


        


if __name__ == '__main__':

    # # initializing Crazyflie 
    cflib.crtp.init_drivers(enable_debug_driver=False)
       

    with SyncCrazyflie(uri_1, cf=Crazyflie(rw_cache='./cache')) as scf_1:
        logconf_1 = LogConfig(name='Position', period_in_ms=500)
        logconf_1.add_variable('kalman.stateX', 'float')
        logconf_1.add_variable('kalman.stateY', 'float')
        logconf_1.add_variable('kalman.stateZ', 'float')        
        scf_1.cf.log.add_config(logconf_1)
        logconf_1.data_received_cb.add_callback(lambda timestamp, data, logconf_1: log_pos_callback_1(uri_1, timestamp, data, logconf_1) )

        logconf_1.start()
        
        time.sleep(3)

        
        # # Posture 1 (MotionCommander)
        # move_baduanjin_mc_p1(scf_1, e2)

        # # Posture 1 (PositioningHlCommander)
        # activate_high_level_commander(scf_1.cf)
        # move_baduanjin_hl_p1(scf_1, e2)


        # # Posture 3 (MotionCommander)
        move_baduanjin_mc_p3(scf_1)

        # # Posture 3 (PositioningHlCommander)
        # activate_high_level_commander(scf_1.cf)
        # move_baduanjin_hl_p3(scf_1, e2)
        

