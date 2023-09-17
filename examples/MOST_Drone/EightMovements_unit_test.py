import time
import cflib.crtp

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.log import LogConfig


# URI to the Crazyflie to connect to
uri_1 = 'radio://0/80/2M/E7E7E7E706'

init_H = float(0.3)  # Initial drone's height; unit: m
# final_H = float(0.7)  # Final drone's height; unit: m


init_Vel = 0.5  # Initial velocity
task_Vel = 0.3  # on-task velocity


position_estimate_1 = [0, 0, 0]  # Drone's pos


# # Positioning Callback Section
def log_pos_callback_1(uri_1, timestamp, data, logconf_1):
    global position_estimate_1
    position_estimate_1[0] = data['kalman.stateX']
    position_estimate_1[1] = data['kalman.stateY']
    position_estimate_1[2] = data['kalman.stateZ']
    print("{}: {} is at pos: ({}, {}, {})".format(timestamp, uri_1, position_estimate_1[0], position_estimate_1[1],
                                            position_estimate_1[2]))


# # Crazyflie Motion Section

def drone_guide_mc(scf): # default take-off height = 0.3 m

    with MotionCommander(scf) as mc:
        mc.up(init_H, velocity=init_Vel)
        time.sleep(2)

        for i in range(1,10):
            print("Round: ", i)

            ## Movement (a) Hip exten & (c) Knee flex
            mc.move_distance(0.5, 0, 0.5, velocity=task_Vel)  # moving up-front (refers to the drone)
            # mc.up(0.5, velocity=task_Vel)  # moving up-front (refers to the drone)
            time.sleep(0.8)

            mc.move_distance(-0.5, 0, -0.5, velocity=task_Vel)  # moving back
            # mc.down(0.5, velocity=task_Vel)  # moving back
            time.sleep(1.5)


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
        
        # Perform the drone guiding task
        drone_guide_mc(scf_1)

        time.sleep(5)

        logconf_1.stop()

