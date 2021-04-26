#!/usr/bin/env python
# license removed for brevity
import time
#import tf
import math
from _ast import IsNot

def wraptopi(number):
    return  ( number + 3.14159) % (2 * 3.14159 ) - 3.14159

class WallFollowingCommand:

    def __init__(self, vel_x: float=0.0, vel_y: float=0.0, vel_z: float=0.0, ang_z: float=0.0):
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.vel_z = vel_z
        self.ang_z = ang_z

class WallFollower:

    ref_distance_from_wall = 1.0
    max_speed = 0.2
    front_range = 0.0
    side_range = 0.0
    max_rate = 0.5
    state_start_time = 0
    state = "FORWARD"
    previous_heading = 0.0;
    angle=2000
    calculate_angle_first_time = True;
    around_corner_first_turn = True;
    direction = 1
    around_corner_go_back = False

    def init(self,new_ref_distance_from_wall,max_speed_ref = 0.2):
        self.ref_distance_from_wall = new_ref_distance_from_wall
        self.state = "TURN_TO_FIND_WALL"
        self.max_speed = max_speed_ref  
        
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

    def commandForwardAlongWall(self, range):
        command = WallFollowingCommand()
        command.vel_x = self.max_speed
        if  self.logicIsCloseTo(self.ref_distance_from_wall, range, 0.1) == False:
            if range>self.ref_distance_from_wall:
                command.vel_y = self.direction*( - self.max_speed/3)
            else:
                command.vel_y = self.direction*self.max_speed /3

        return command

    def commandTurn(self,rate):
        v = 0.0
        w = self.direction*rate
        command = WallFollowingCommand()
        command.vel_x = v
        command.ang_z = w
        return command

    def commandTurnandAdjust(self,rate, range):
        v = 0.0
        w = self.direction*rate
        command = WallFollowingCommand()

        if  self.logicIsCloseTo(self.ref_distance_from_wall, range, 0.1) == False:
            if range>self.ref_distance_from_wall:
                command.vel_y = self.direction*( - self.max_speed/3)
            else:
                command.vel_y = self.direction*( self.max_speed /3)
        command.vel_x = v
        command.ang_z = w
        return command

    def commandTurnAroundCorner(self, radius):
        v = self.max_speed
        w = self.direction*(-v/radius)
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

    def wall_follower(self, front_range, side_range, current_heading, direction_turn=1):


        self.direction = direction_turn
        #handle state transitions
        if self.state == "FORWARD":
            if front_range < self.ref_distance_from_wall + 0.2:
                self.state = self.transition("TURN_TO_FIND_WALL")
        elif self.state == "HOVER":
            print(self.state)
        elif self.state == "TURN_TO_FIND_WALL":
            print(front_range,side_range)
            if (side_range < self.ref_distance_from_wall/math.cos(0.78)+0.2 and front_range < self.ref_distance_from_wall/math.cos(0.78)+0.2):
                self.previous_heading = current_heading;
                self.angle = self.direction*( 1.57 - math.atan(front_range/side_range) - 0.1)
                self.state = self.transition("TURN_TO_ALLIGN_TO_WALL")
            if (side_range < 1.0 and front_range > 2.0):
                self.around_corner_first_turn = True
                self.around_corner_go_back = False
                self.previous_heading = current_heading;
                self.state = self.transition("ROTATE_AROUND_WALL")
        elif self.state =="TURN_TO_ALLIGN_TO_WALL":
            print(wraptopi(current_heading-self.previous_heading),self.angle)
            if self.logicIsCloseTo(wraptopi(current_heading-self.previous_heading),self.angle, 0.1):
                self.state = self.transition("FORWARD_ALONG_WALL")

        elif self.state =="FORWARD_ALONG_WALL":
            if side_range >  self.ref_distance_from_wall + 0.3:
                self.around_corner_first_turn = True
                self.state = self.transition("ROTATE_AROUND_WALL")
            if front_range < self.ref_distance_from_wall+0.2:
                self.state = self.transition("ROTATE_IN_CORNER")
                self.previous_heading = current_heading;
        elif self.state =="ROTATE_AROUND_WALL":
            if front_range < self.ref_distance_from_wall+0.2:
                self.state = self.transition("TURN_TO_FIND_WALL")
        elif self.state == "ROTATE_IN_CORNER":
            print(current_heading-self.previous_heading)
            if self.logicIsCloseTo(math.fabs(wraptopi(current_heading-self.previous_heading)), 0.8, 0.1):
                self.state = self.transition("TURN_TO_FIND_WALL")


        #handle state ations
        if self.state == "TAKE_OFF":
            command = self.take_off()
        elif self.state == "FORWARD":
            command = self.commandForward()
        elif self.state == "HOVER":
            command = self.hover()
        elif self.state == "TURN_TO_FIND_WALL":
            command = self.hover()
            if (time.time() - self.state_start_time) > 1:
                command = self.commandTurn(self.max_rate);
        elif self.state =="TURN_TO_ALLIGN_TO_WALL":
            command = self.hover()
            if (time.time() - self.state_start_time) > 1:
                command = self.commandTurn(self.max_rate)
        elif self.state =="FORWARD_ALONG_WALL":
            command = self.commandForwardAlongWall(side_range)
        elif self.state == "ROTATE_AROUND_WALL":
            if self.around_corner_first_turn:
                print("regular_turn_first")
            #if side_range>self.ref_distance_from_wall+0.5 and self.around_corner_first_turn:
                command = self.commandTurn(-self.max_rate)
                if side_range<=self.ref_distance_from_wall+0.5:
                    self.around_corner_first_turn = False
                    self.previous_heading = current_heading;
            else:
                if side_range>self.ref_distance_from_wall+0.5:
                    print("commandTurnandAdjust")
                    print("headin diff", wraptopi(abs(current_heading - self.previous_heading)))
                    if wraptopi(abs(current_heading - self.previous_heading)) > 0.3:
                        self.around_corner_go_back = True
                    if  self.around_corner_go_back:
                        command = self.commandTurnandAdjust(self.max_rate,side_range)
                        print("go back")
                    else:
                        command = self.commandTurnandAdjust(-1*self.max_rate,side_range)
                        print("forward")
                else:
                    print("commandTurnAroundCorner")
                    self.previous_heading = current_heading;
                    command = self.commandTurnAroundCorner(self.ref_distance_from_wall)
                    self.previous_heading = current_heading
                    self.around_corner_go_back = False

        elif self.state == "ROTATE_IN_CORNER":
            command = self.commandTurn(self.max_rate);


        return command, self.state