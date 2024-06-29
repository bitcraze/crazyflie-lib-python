import time
import logging
import cflib.crtp
import math

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.positioning.position_hl_commander import PositionHlCommander


# URI to the Crazyflie to connect to
uri = 'radio://0/80/2M/E7E7E7E701'

start_x = float(0.0)  # initial pos_X of the drone; unit: m
start_y = float(0.0)  # initial pos_y of the drone; unit: m
take_off_vel = 0.3    # take off velocity; unit: m/s

f = open("conditions.txt", "rt")
data = f.read()

data_split = data.split()
h0 = float(data_split[0]) # Eyes level height (unit: meter)
T_fly_out = float(data_split[1]) # Fly out time (unit: sec)
V_fly_out = float(data_split[2]) # Fly out velocity (unit: m/s)
fly_out_x = float(data_split[3]) # Fly out position in x-axis (unit: m) 
fly_out_y = float(data_split[4]) # Fly out position in y-axis (unit: m)
fly_out_z = float(data_split[5]) # Fly out position in z-axis (unit: m)

dist = math.sqrt(fly_out_x*fly_out_x + fly_out_y*fly_out_y + fly_out_z*fly_out_z)

# # # Crazyflie Motion (using MotionCommander)
# drone stand's height: 0.15 m; ball and stick: 0.08 m (count from drone's legs)


def drone_move_mc(scf): # default take-off height = 0.3 m
    
    t_init = time.time()

    with MotionCommander(scf) as mc:

        t_take_off = time.time()
        print("start taking off at ", t_take_off-t_init)   
    
        ## Go up: h0 meter (at the eyes level)
        mc.up(h0 - 0.37, velocity=take_off_vel) # eye_level (h0)-init_takeoff(0.3)-drone_standing(0.15)-ball&stick(0.08)

        t1 = time.time()
        print("t take off: ", t1-t_take_off)

        ## hover before flying out      
        mc.stop()

        t0 = time.time()

        ## hovering time
        time.sleep(T_fly_out)

        t1 = time.time() - t0
        print("t wait: ", t1)

        # Timestamp before flying out
        t_fo = time.time() - t_take_off
        print("t fly out: ", t_fo)

        ## Fly out
        print("Start flying out")
        mc.move_distance(fly_out_x, fly_out_y, fly_out_z, velocity=V_fly_out) 
        # mc.up(fly_out_z, velocity=V_fly_out)

        t_f1 = time.time() - t_take_off
        print("t after fly out: ", t_f1)
       
        mc.stop()
        
        ## Delay 1 sec before landing
        time.sleep(1)


# # # Crazyflie Motion (using MotionCommander)

def drone_move_pc(scf): # default take-off height = 0.3 m
    
    t_init = time.time()

    with PositionHlCommander(
        scf,
        x=start_x, y=start_y, z=0.0,
        default_velocity=take_off_vel,
        default_height=0.3,
        controller=PositionHlCommander.CONTROLLER_PID) as pc:

        t_take_off = time.time()
        print("start taking off at ", t_take_off-t_init)   
    
        ## Go up: h0 meter (at the eyes level)
        pc.up(h0 - 0.37, velocity=take_off_vel)
        # time.sleep((h0 - 0.53)/take_off_vel)
        print(pc.get_position())
        
        t_prep = time.time()
        print("t take off: ", t_prep-t_take_off)

        ## Delay before flying out (*** maybe make it random for training purpose)
        time.sleep(T_fly_out)

        t_wait = time.time() - t_prep
        print("t wait: ", t_wait)

        # Timestamp before flying out
        t_fo = time.time() - t_take_off
        print("t fly out: ", t_fo)

        ## Fly out
        print("Start flying out")
        pc.move_distance(fly_out_x, fly_out_y, fly_out_z, velocity=V_fly_out) 
        # time.sleep(dist/V_fly_out)

        t_f1 = time.time() - t_take_off
        print("t after fly out: ", t_f1)
        
        ## Delay 1 sec before landing
        time.sleep(1)

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


if __name__ == '__main__':

    # # initializing Crazyflie 
    cflib.crtp.init_drivers(enable_debug_driver=False)
    
    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
 
        # Perform the movement
        # drone_move_mc(scf)
        drone_move_pc(scf)

