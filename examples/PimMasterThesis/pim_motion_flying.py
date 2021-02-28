import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander

URI = 'radio://0/80/2M/E7E7E7E702'
DEFAULT_HEIGHT = 0.5
BOX_LIMIT = 0.5
position_estimate = [0, 0, 0]

is_flow_deck_attached = False
is_led_deck_attached = False
is_dwm1000_deck_attached = False

logging.basicConfig(level=logging.ERROR)

def move_baduanjin_p1(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(1)
        mc.move_distance(0, 0, 0.7, velocity=0.05)   # so the final posistion (before landing) will be "height = 0.5(default h) + 0.7" 
        time.sleep(1)
        mc.move_distance(0, 0, -0.5, velocity=0.05)
        time.sleep(1)
        mc.move_distance(0, 0, -0.3, velocity=0.05)
        time.sleep(1)

def move_box_limit(scf): 
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        
        # mc.start_forward()

        # while (1):
        #     if position_estimate[0] > BOX_LIMIT:  
        #         print("Back")
        #         mc.start_back(velocity=0.2)
        #     elif position_estimate[0] < -BOX_LIMIT:  
        #         print("Forward")
        #         mc.start_forward(velocity=0.2)   
        #     time.sleep(0.1)    # without this line the CF cannot reach the order

        body_x_cmd = 0.2
        body_y_cmd = 0.1
        max_vel = 0.2

        while (1):
            if position_estimate[0] > BOX_LIMIT:
                body_x_cmd = -max_vel
            elif position_estimate[0] < -BOX_LIMIT:
                body_x_cmd = max_vel
            if position_estimate[1] > BOX_LIMIT:
                body_y_cmd = -max_vel
            elif position_estimate[1] < -BOX_LIMIT:
                body_y_cmd = max_vel

            mc.start_linear_motion(body_x_cmd, body_y_cmd, 0)

            time.sleep(0.1)

def move_linear_simple(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(1)
        mc.forward(0.5)
        time.sleep(1)
        mc.turn_left(180)
        time.sleep(1)
        mc.forward(0.5)
        time.sleep(1)

def take_off_simple(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(3)
        mc.stop()

def log_pos_callback(timestamp, data, logconf):
    print(data)
    global position_estimate
    position_estimate[0] = data['stateEstimate.x']
    position_estimate[1] = data['stateEstimate.y']
    position_estimate[2] = data['stateEstimate.z']

def param_deck_flow(name, value_str):
    value = int(value_str)
    # print(value)
    global is_flow_deck_attached
    if value:
        is_flow_deck_attached = True
        print('Flow Deck is attached!')
    else:
        is_flow_deck_attached = False
        print('Flow Deck is NOT attached!')

def param_deck_led(name, value_str):
    value = int(value_str)
    # print(value)
    global is_led_deck_attached
    if value:
        is_led_deck_attached = True
        print('LED Deck is attached!')
    else:
        is_led_deck_attached = False
        print('LED Deck is NOT attached!')

def param_deck_dwm1000(name, value_str):
    value = int(value_str)
    # print(value)
    global is_dwm1000_deck_attached
    if value:
        is_dwm1000_deck_attached = True
        print('DWM1000 Deck is attached!')
    else:
        is_dwm1000_deck_attached = False
        print('DWM1000 Deck is NOT attached!')


if __name__ == '__main__':
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:

        scf.cf.param.add_update_callback(group='deck', name='bcFlow2',
                                         cb=param_deck_flow)
        scf.cf.param.add_update_callback(group='deck', name='bcLedRing',
                                         cb=param_deck_led)
        scf.cf.param.add_update_callback(group='deck', name='bcDWM1000',
                                         cb=param_deck_dwm1000)
        time.sleep(1)

        logconf = LogConfig(name='Position', period_in_ms=10)
        logconf.add_variable('stateEstimate.x', 'float')
        logconf.add_variable('stateEstimate.y', 'float')
        logconf.add_variable('stateEstimate.z', 'float')
        scf.cf.log.add_config(logconf)
        logconf.data_received_cb.add_callback(log_pos_callback)

        if is_dwm1000_deck_attached:
            logconf.start()

            # take_off_simple(scf)
            # move_linear_simple(scf)
            # move_box_limit(scf)
            move_baduanjin_p1(scf)

            logconf.stop()

        else:
            print("CF cannot fly since there is no flow deck attached!")