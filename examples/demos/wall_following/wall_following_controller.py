#!/usr/bin/env python
# license removed for brevity
from wall_follower_multi_ranger import WallFollower
from wall_follower_multi_ranger import WallFollowingCommand

import time
#import tf
import math
from _ast import IsNot


class WallFollowerController:
    wall_follower = WallFollower()
    ref_distance_from_wall = 0.5
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
        command = WallFollowingCommand()
        command.vel_z = 0.1;
        return command

    def hover(self):
        command = WallFollowingCommand()
        return command

    def commandForward(self):
        v = self.max_speed
        w = 0
        command = WallFollowingCommand()
        command.vel_x = v
        command.ang_z = w
        return command


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

    def stateMachine(self, front_range, right_range, left_range, current_heading):

        command = WallFollowingCommand()
        state_WF = "idle"

        if front_range == None:
            front_range = 9999

        if right_range == None:
            right_range = 9999

        # Handle State transition
        if self.state == "FORWARD":
            if front_range < self.ref_distance_from_wall+0.2:
                self.state = self.transition("WALL_FOLLOWING")
                self.wall_follower.init(self.ref_distance_from_wall,self.max_speed)
        # Handle actions
        if self.state == "FORWARD":
            command=self.commandForward()
        elif self.state == "WALL_FOLLOWING":
            command, state_WF = self.wall_follower.wall_follower(front_range,left_range, current_heading, -1)

        self.lastcommand = command
        return command, self.state, state_WF

