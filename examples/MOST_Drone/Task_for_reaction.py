import time
import cflib.crtp
import winsound

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander


# URI to the Crazyflie to connect to
uri = 'radio://0/80/2M/E7E7E7E706'


f = open("conditions.txt", "rt")
data = f.read()
 
data_split = data.split()
h0 = float(data_split[0]) # Eyes level height (unit: meter)
T_fly_out = float(data_split[1]) # Fly out time (unit: sec)
V_fly_out = float(data_split[2]) # Fly out velocity (unit: m/s)
fly_out_x = float(data_split[3]) # Fly out position in x-axis (unit: m) 
fly_out_y = float(data_split[4]) # Fly out position in y-axis (unit: m)
fly_out_z = float(data_split[5]) # Fly out position in z-axis (unit: m)


# # # Crazyflie Motion (using MotionCommander)

def drone_move_mc(scf): # default take-off height = 0.3 m
    
    t_init = time.time()

    with MotionCommander(scf) as mc:

        t_take_off = time.time() - t_init
        print("start taking off at ", t_take_off)   
    
        ## Go up: h0 meter (at the eyes level)
        mc.up(h0 - 0.52, velocity=0.3)
        
        # mc.stop()

        # time.sleep(10)

        # mc.left(0.4)
       
        mc.stop()

        ## Delay before flying out
        time.sleep(T_fly_out)

        ## BEEP before flying out
        # print("Beep!!")
        # frequency = 1000  # Set Frequency To 2500 Hertz
        # duration = 250  # Set Duration To 250 ms == 0.25 second
        # winsound.Beep(frequency, duration)

        # time.sleep(0.1)

        # Timestamp before flying out
        t_fo = time.time() - t_init
        print("t fly out: ", t_fo)

        ## Fly out
        print("Start flying out")
        mc.move_distance(fly_out_x, fly_out_y, fly_out_z, velocity=V_fly_out) 
        # mc.up(fly_out_z, velocity=V_fly_out)

        t_f1 = time.time() - t_init
        print("t after fly out: ", t_f1)
       
        mc.stop()
        
        ## Delay 2 sec before landing
        time.sleep(0.5)

    

if __name__ == '__main__':

    # # initializing Crazyflie 
    cflib.crtp.init_drivers(enable_debug_driver=False)
    
    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
 
        # Perform the movement
        drone_move_mc(scf)


