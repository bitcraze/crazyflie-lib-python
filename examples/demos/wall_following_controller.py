#!/usr/bin/env python
# license removed for brevity
import rospy
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from gazebo_msgs.msg import ModelStates
from hector_uav_msgs.srv import EnableMotors
from sensor_msgs.msg import LaserScan
from sensor_msgs.msg import Imu
from wall_follower_multi_ranger import WallFollower

import time
#import tf
import math
from _ast import IsNot
from amcl.cfg.AMCLConfig import inf




class WallFollowerController:
    wall_follower = WallFollower()
    ref_distance_from_wall = 1.0
    max_speed = 0.2
    front_range = 0.0
    right_range = 0.0
    max_rate = 0.5
    state_start_time = 0
    state = "FORWARD"
    previous_heading = 0.0;
    angle=2000
    calculate_angle_first_time = True;
    around_corner_first_turn = True;

    def init(self,new_ref_distance_from_wall,max_speed_ref = 0.2):
        self.ref_distance_from_wall = new_ref_distance_from_wall
        self.max_speed = max_speed_ref

        self.state = "FORWARD"

    def take_off(self):
        twist = Twist()
        twist.linear.z = 0.1;
        return twist

    def hover(self):
        twist = Twist()
        return twist


    def twistForward(self):
        v = self.max_speed
        w = 0
        twist = Twist()
        twist.linear.x = v
        twist.angular.z = w
        return twist





    def logicIsCloseTo(self,real_value = 0.0, checked_value =0.0, margin=0.05):

        if real_value> checked_value-margin and real_value< checked_value+margin:
            return True
        else:
            return False

    # Transition state and restart the timer
    def transition(self, newState):
        state = newState
        self.state_start_time = time.time()
        return state

    def stateMachine(self, front_range, right_range, left_range, current_heading, angle_goal, distance_goal):

        twist = Twist()

        if front_range == None:
            front_range = inf

        if right_range == None:
            right_range = inf

        # Handle State transition
        if self.state == "FORWARD":
            if front_range < self.ref_distance_from_wall+0.2:
                self.state = self.transition("WALL_FOLLOWING")
                self.wall_follower.init(self.ref_distance_from_wall,self.max_speed)
        # Handle actions
        if self.state == "FORWARD":
            twist=self.twistForward()
        elif self.state == "WALL_FOLLOWING":
            twist, state_WF = self.wall_follower.wall_follower(front_range,right_range, current_heading, 1)

        print(self.state)

        self.lastTwist = twist
        return twist



if __name__ == '__main__':
    try:
        wall_follower()
    except rospy.ROSInterruptException:
        pass
