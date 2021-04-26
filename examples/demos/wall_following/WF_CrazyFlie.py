#!/usr/bin/env python
# license removed for brevity


import time
#import tf
import math
from _ast import IsNot
import logging
import sys

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils.multiranger import Multiranger
from cflib.crazyflie.syncLogger import SyncLogger

from cflib.crazyflie.log import LogConfig

from wall_following_controller import WallFollowerController, WallFollowingCommand

# Only output errors from the logging framework
#logging.basicConfig(level=logging.ERROR)

class WF_crazyflie:
    # Callbacks
    front_range = 0.0
    right_range = 0.0
    altitude = 0.0
    URI = 'radio://0/10/2M/E7E7E7E7E7'

    coord_index = 0

    if len(sys.argv) > 1:
        URI = sys.argv[1]

    # Only output errors from the logging framework
    logging.basicConfig(level=logging.ERROR)


    def data_received(self, timestamp, data, logconf):

        self.current_heading = math.radians(data['stabilizer.yaw'])

    def crazyFlieloop(self):

        command = WallFollowingCommand()
        cflib.crtp.init_drivers(enable_debug_driver=False)
        cf = Crazyflie(rw_cache='./cache')

        lg_states = LogConfig(name='estimates', period_in_ms=100)
        lg_states.add_variable('stabilizer.yaw')

        state_WF = "Idle"
        state_SM = "Idle"

        with SyncCrazyflie(self.URI, cf=cf) as scf:
            with MotionCommander(scf,0.5) as motion_commander:
                with Multiranger(scf) as multi_ranger:
                    with SyncLogger(scf, lg_states) as logger_states:
                        

                        
                        bug_controller = WallFollowerController()
                        bug_controller.init(0.5,0.5)


                        keep_flying = True
                        time.sleep(1)


                        command.vel_x = 0.2
                        command.vel_y = 0.0
                        command.ang_z = 0
                        heading = 0.0

                        while keep_flying:
                            
                            # crazyflie related stuff
                            for log_entry_1 in logger_states:
                                data = log_entry_1[1]

                                heading = math.radians(float(data["stabilizer.yaw"]));

                                break


                            time.sleep(0.1)
                            
                            command, state_SM, state_WF = bug_controller.stateMachine(multi_ranger.front,multi_ranger.right,multi_ranger.left,heading)
                            print(state_SM, state_WF)

                            motion_commander._set_vel_setpoint(command.vel_x,command.vel_y,0,-1*math.degrees(command.ang_z))
                            #motion_commander._set_vel_setpoint(0,0,0,0)

                            if multi_ranger.up is not None :
                                if multi_ranger.up < 0.2:
                                    print("up range is activated")
                                    keep_flying = False

                        motion_commander.stop()

                        print("demo terminated")
                        
                #time.sleep(10)


if __name__ == '__main__':



    WF_crazyflie = WF_crazyflie()

    WF_crazyflie.crazyFlieloop()
