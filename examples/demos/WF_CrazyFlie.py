#!/usr/bin/env python
# license removed for brevity

from wall_follower_multi_ranger import WallFollower
import time
import tf
import math
from _ast import IsNot
import logging
import sys
import numpy as np

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils.multi_ranger import MultiRanger
from cflib.utils.stabilization import Stabilization
from cflib.crazyflie.syncLogger import SyncLogger

from cflib.crazyflie.log import LogConfig



def wraptopi(number):
    return  ( number + np.pi) % (2 * np.pi ) - np.pi

# Only output errors from the logging framework
#logging.basicConfig(level=logging.ERROR)

class WF_crazyflie:
    # Callbacks
    front_range = 0.0
    right_range = 0.0
    altitude = 0.0
    state = "TAKE_OFF"
    current_heading = 0.0

    URI = 'radio://0/60/2M/E7E7E7E7E7'

    if len(sys.argv) > 1:
        URI = sys.argv[1]

    # Only output errors from the logging framework
    logging.basicConfig(level=logging.ERROR)

            # Transition state and restart the timer
    def transition(self, newState):
        state = newState
        self.state_start_time = time.time()
        return state

    #def init(self):

    def data_received(self, timestamp, data, logconf):

        self.current_heading = math.radians(data['stabilizer.yaw'])

    def crazyFlieloop(self):
        wall_follower = WallFollower()
        wall_follower.init(0.5)




        #log_config.data_received_cb.add_callback(self.data_received)

        cflib.crtp.init_drivers(enable_debug_driver=False)
        cf = Crazyflie(rw_cache='./cache')

        lg_states = LogConfig(name='kalman_states', period_in_ms=100)
        lg_states.add_variable('stabilizer.yaw')
        lg_states.add_variable('kalman_states.ox')
        lg_states.add_variable('kalman_states.oy')
        state= "forward"

        with SyncCrazyflie(self.URI, cf=cf) as scf:
            with MotionCommander(scf,0.8) as motion_commander:
                with MultiRanger(scf) as multi_ranger:
                    with Stabilization(scf) as stabilization:
                        with SyncLogger(scf, lg_states) as logger_states:

                            keep_flying = True
                            vel_x = 0.2
                            vel_y = 0.0
                            ang_z =0.0


                            heading_prev = 0.0
                            heading = 0.0
                            angle_to_goal = 0.0;
                            kalman_x = 0.0
                            kalman_y = 0.0
                            already_reached_far_enough = False
                            while keep_flying:


                                for log_entry_1 in logger_states:
                                    data = log_entry_1[1]

                                    heading = math.radians(float(data["stabilizer.yaw"]));
                                    kalman_x =float(data["kalman_states.ox"])
                                    kalman_y =float(data["kalman_states.oy"])

                                    if already_reached_far_enough:
                                        angle_to_goal = wraptopi(np.pi+math.atan(kalman_y/kalman_x))
                                    else:
                                        angle_to_goal = wraptopi(math.atan(kalman_y/kalman_x))

                                    break


                                time.sleep(0.1)


                                if state == "forward":
                                    print(kalman_x, kalman_y, math.sqrt(math.pow(kalman_x,2) + math.pow(kalman_y,2)))
                                    print(state)

                                    if multi_ranger.front < 0.5 and multi_ranger.front is not None:
                                        state="wall_following"
                                        wall_follower.init(0.5)
                                    if math.sqrt(math.pow(kalman_x,2) + math.pow(kalman_y,2)) > 8 and already_reached_far_enough is False:
                                        vel_x = 0.0
                                        vel_y = 0.0
                                        ang_z = 0#np.pi*2 / 6
                                        state = "stop"#"turn_to_target"
                                        heading_prev = heading
                                        already_reached_far_enough = True
                                    if math.sqrt(math.pow(kalman_x,2) + math.pow(kalman_y,2)) < 0.4:
                                        state = "stop"
                                        vel_x = 0.0
                                        vel_y = 0.0
                                        ang_z = 0.0
                                    elif state == "wall_following":
                                        twist = wall_follower.wall_follower(multi_ranger.front,multi_ranger.right,stabilization.heading)
                                        if wraptopi(heading-heading_prev) < angle_to_goal and  multi_ranger.front > 1.2 :
                                            state = "forward"
                                elif state == "turn_to_target":
                                    if wraptopi(heading-heading_prev) < angle_to_goal:
                                        vel_x = 0.2
                                        vel_y = 0.0
                                        ang_z = 0.0
                                        state = "forward"
                                elif state == "stop":
                                    break

                                motion_commander._set_vel_setpoint(vel_x,vel_y,0,-1*math.degrees(ang_z))

                                if multi_ranger.up < 0.2 and multi_ranger.up is not None:
                                    print("up range is activated")
                                    keep_flying = False

                            motion_commander.stop()

                            print("demo terminated")



if __name__ == '__main__':

    WF_crazyflie = WF_crazyflie()

    WF_crazyflie.crazyFlieloop()
    #WF_crazyflie.init()
