#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2019 Bitcraze AB
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
"""
Simple example of a synchronized swarm choreography using the High level commander.

The swarm takes off and flies a synchronous choreography before landing.
The take-of is relative to the start position but the Goto are absolute.
The sequence contains a list of commands to be executed at each step.

This example is intended to work with any absolute positioning system.
It aims at documenting how to use the High Level Commander together with
the Swarm class to achieve synchronous sequences.
"""
import time

import cflib.crtp
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncLogger import SyncLogger

from collections import namedtuple
import threading
from queue import Queue

# Time for one step in second
STEP_TIME = 1

# Possible commands, all times are in seconds
Takeoff = namedtuple('Takeoff', ['height', 'time'])
Land = namedtuple("Land", ['time'])
Goto = namedtuple('Goto', ['x', 'y', 'z', 'time'])
Ring = namedtuple('Ring', ['r', 'g', 'b', 'intensity', 'time'])   # RGB [0-255], Intensity [0.0-1.0]
Quit = namedtuple('Quit', []) # Reserved for the control loop, do not use in sequence

uris = [
    'radio://0/10/2M/E7E7E7E701',  # cf_id 0
    'radio://0/10/2M/E7E7E7E702',  # cf_id 1
    'radio://0/10/2M/E7E7E7E703',  # cf_id 3
    'radio://0/10/2M/E7E7E7E704',  # cf_id 4
    'radio://0/10/2M/E7E7E7E705',  # cf_id 5
    'radio://0/10/2M/E7E7E7E706',  # cf_id 6
    'radio://0/10/2M/E7E7E7E707',  # cf_id 7
    'radio://0/10/2M/E7E7E7E708',  # cf_id 8
    'radio://0/10/2M/E7E7E7E709',  # cf_id 9
    # Add more URIs if you want more copters in the swarm
]

Z_center = 1.5
Z_inner = 1
Z_outer = 0.5

X_inner = 0.4
X_outer = 0.8

sequence = [
    # Step,  CF_id,  action

    # Takeoff for outer square
    ( 0,     0,      Takeoff(Z_outer, 2)),
    ( 0,     1,      Takeoff(Z_outer, 2)),
    ( 0,     2,      Takeoff(Z_outer, 2)),
    ( 0,     3,      Takeoff(Z_outer, 2)),

    # Takeoff for inner square

    ( 2,     4,      Takeoff(Z_inner, 3)),
    ( 2,     5,      Takeoff(Z_inner, 3)),
    ( 2,     6,      Takeoff(Z_inner, 3)),
    ( 2,     7,      Takeoff(Z_inner, 3)),

    # Takeoff for center

    ( 5,     8,      Takeoff(Z_center, 3)),

    # Goto starting point
        # Outer square
    ( 8,     0,      Goto(X_outer, X_outer, Z_outer, 1)),
    ( 8,     1,      Goto(X_outer, -X_outer, Z_outer, 1)),
    ( 8,     2,      Goto(-X_outer, -X_outer, Z_outer, 1)),
    ( 8,     3,      Goto(-X_outer, X_outer, Z_outer, 1)),

        # Inner square
    ( 8,     4,      Goto(X_inner, X_inner, Z_inner, 1)),
    ( 8,     5,      Goto(X_inner, -X_inner, Z_inner, 1)),
    ( 8,     6,      Goto(-X_inner, -X_inner, Z_inner, 1)),
    ( 8,     7,      Goto(-X_inner, X_inner, Z_inner, 1)),

        # Center
    ( 8,     8,      Goto(0, 0, Z_center, 1)),

    # Turn lights on
        # Outer square

    ( 9,    0,      Ring(255, 255, 255, 1, 0)),
    ( 9,    1,      Ring(255, 255, 255, 1, 0)),
    ( 9,    2,      Ring(255, 255, 255, 1, 0)),
    ( 9,    3,      Ring(255, 255, 255, 1, 0)),

        # Inner square

    ( 11,    4,      Ring(128, 0, 128, 1, 0)),
    ( 11,    5,      Ring(128, 0, 128, 1, 0)),
    ( 11,    6,      Ring(128, 0, 128, 1, 0)),
    ( 11,    7,      Ring(128, 0, 128, 1, 0)),

        # Center

    ( 13,    8,      Ring(255, 0, 255, 1, 0)),    


    # Start rotation
    ( 16,    0,      Goto(X_outer, -X_outer, Z_outer, 2.5)),
    ( 16,    1,      Goto(-X_outer, -X_outer, Z_outer, 2.5)),
    ( 16,    2,      Goto(-X_outer, X_outer, Z_outer, 2.5)),
    ( 16,    3,      Goto(X_outer, X_outer, Z_outer, 2.5)),

    ( 16,    4,      Goto(X_inner, -X_inner, Z_inner, 2.5)),
    ( 16,    5,      Goto(-X_inner, -X_inner, Z_inner, 2.5)),
    ( 16,    6,      Goto(-X_inner, X_inner, Z_inner, 2.5)),
    ( 16,    7,      Goto(X_inner, X_inner, Z_inner, 2.5)),


    ( 18.5,    0,      Goto(-X_outer, -X_outer, Z_outer, 2.5)),
    ( 18.5,    1,      Goto(-X_outer, X_outer, Z_outer, 2.5)),
    ( 18.5,    2,      Goto(X_outer, X_outer, Z_outer, 2.5)),
    ( 18.5,    3,      Goto(X_outer, -X_outer, Z_outer, 2.5)),

    ( 18.5,    4,      Goto(-X_inner, -X_inner, Z_inner, 2.5)),
    ( 18.5,    5,      Goto(-X_inner, X_inner, Z_inner, 2.5)),
    ( 18.5,    6,      Goto(X_inner, X_inner, Z_inner, 2.5)),
    ( 18.5,    7,      Goto(X_inner, -X_inner, Z_inner, 2.5)),


    ( 21,    0,      Goto(-X_outer, X_outer, Z_outer, 2.5)),
    ( 21,    1,      Goto(X_outer, X_outer, Z_outer, 2.5)),
    ( 21,    2,      Goto(X_outer, -X_outer, Z_outer, 2.5)),
    ( 21,    3,      Goto(-X_outer, -X_outer, Z_outer, 2.5)),

    ( 21,    4,      Goto(-X_inner, X_inner, Z_inner, 2.5)),
    ( 21,    5,      Goto(X_inner, X_inner, Z_inner, 2.5)),
    ( 21,    6,      Goto(X_inner, -X_inner, Z_inner, 2.5)),
    ( 21,    7,      Goto(-X_inner, -X_inner, Z_inner, 2.5)),


    ( 23.5,    0,      Goto(X_outer, X_outer, Z_outer, 2.5)),
    ( 23.5,    1,      Goto(X_outer, -X_outer, Z_outer, 2.5)),
    ( 23.5,    2,      Goto(-X_outer, -X_outer, Z_outer, 2.5)),
    ( 23.5,    3,      Goto(-X_outer, X_outer, Z_outer, 2.5)),

    ( 23.5,    4,      Goto(X_inner, X_inner, Z_inner, 2.5)),
    ( 23.5,    5,      Goto(X_inner, -X_inner, Z_inner, 2.5)),
    ( 23.5,    6,      Goto(-X_inner, -X_inner, Z_inner, 2.5)),
    ( 23.5,    7,      Goto(-X_inner, X_inner, Z_inner, 2.5)),

    # Change color
        # Outer square

    ( 24.5,    0,      Ring(255, 0, 255, 1, 0)), 
    ( 24.5,    1,      Ring(255, 0, 255, 1, 0)), 
    ( 24.5,    2,      Ring(255, 0, 255, 1, 0)), 
    ( 24.5,    3,      Ring(255, 0, 255, 1, 0)), 

        # Inner square

    ( 25.5,    4,      Ring(255, 255, 255, 1, 0)),
    ( 25.5,    5,      Ring(255, 255, 255, 1, 0)),
    ( 25.5,    6,      Ring(255, 255, 255, 1, 0)),
    ( 25.5,    7,      Ring(255, 255, 255, 1, 0)),

        # Center

    ( 26.5,    8,      Ring(128, 0, 128, 1, 0)),  

    # Switch Z for outer and center

    ( 28,     0,      Goto(X_outer, X_outer, Z_center, 2.5)),
    ( 28,     1,      Goto(X_outer, -X_outer, Z_center, 2.5)),
    ( 28,     2,      Goto(-X_outer, -X_outer, Z_center, 2.5)),
    ( 28,     3,      Goto(-X_outer, X_outer, Z_center, 2.5)),

    ( 28,     8,      Goto(0, 0, Z_outer, 2.5)),  

    # Change lights on all crazyflies

    ( 31,    0,      Ring(0, 0, 255, 1, 0)), 
    ( 31,    1,      Ring(0, 0, 255, 1, 0)),  
    ( 31,    2,      Ring(0, 0, 255, 1, 0)),  
    ( 31,    3,      Ring(0, 0, 255, 1, 0)),  
    ( 31,    4,      Ring(0, 0, 255, 1, 0)), 
    ( 31,    5,      Ring(0, 0, 255, 1, 0)), 
    ( 31,    6,      Ring(0, 0, 255, 1, 0)), 
    ( 31,    7,      Ring(0, 0, 255, 1, 0)), 
    ( 31,    8,      Ring(0, 0, 255, 1, 0)),  


    # Start rotation - Opposite way

    ( 33,    0,      Goto(-X_outer, X_outer, Z_center, 2.5)),
    ( 33,    1,      Goto(X_outer, X_outer, Z_center, 2.5)),
    ( 33,    2,      Goto(X_outer, -X_outer, Z_center, 2.5)),
    ( 33,    3,      Goto(-X_outer, -X_outer, Z_center, 2.5)),

    ( 33,    4,      Goto(-X_inner, X_inner, Z_inner, 2.5)),
    ( 33,    5,      Goto(X_inner, X_inner, Z_inner, 2.5)),
    ( 33,    6,      Goto(X_inner, -X_inner, Z_inner, 2.5)),
    ( 33,    7,      Goto(-X_inner, -X_inner, Z_inner, 2.5)),

    ( 35.5,    0,      Goto(-X_outer, -X_outer, Z_center, 2.5)),
    ( 35.5,    1,      Goto(-X_outer, X_outer, Z_center, 2.5)),
    ( 35.5,    2,      Goto(X_outer, X_outer, Z_center, 2.5)),
    ( 35.5,    3,      Goto(X_outer, -X_outer, Z_center, 2.5)),

    ( 35.5,    4,      Goto(-X_inner, -X_inner, Z_inner, 2.5)),
    ( 35.5,    5,      Goto(-X_inner, X_inner, Z_inner, 2.5)),
    ( 35.5,    6,      Goto(X_inner, X_inner, Z_inner, 2.5)),
    ( 35.5,    7,      Goto(X_inner, -X_inner, Z_inner, 2.5)),

    ( 38,    0,      Goto(X_outer, -X_outer, Z_center, 2.5)),
    ( 38,    1,      Goto(-X_outer, -X_outer, Z_center, 2.5)),
    ( 38,    2,      Goto(-X_outer, X_outer, Z_center, 2.5)),
    ( 38,    3,      Goto(X_outer, X_outer, Z_center, 2.5)),

    ( 38,    4,      Goto(X_inner, -X_inner, Z_inner, 2.5)),
    ( 38,    5,      Goto(-X_inner, -X_inner, Z_inner, 2.5)),
    ( 38,    6,      Goto(-X_inner, X_inner, Z_inner, 2.5)),
    ( 38,    7,      Goto(X_inner, X_inner, Z_inner, 2.5)),

    ( 40.5,    0,      Goto(X_outer, X_outer, Z_center, 2.5)),
    ( 40.5,    1,      Goto(X_outer, -X_outer, Z_center, 2.5)),
    ( 40.5,    2,      Goto(-X_outer, -X_outer, Z_center, 2.5)),
    ( 40.5,    3,      Goto(-X_outer, X_outer, Z_center, 2.5)),

    ( 40.5,    4,      Goto(X_inner, X_inner, Z_inner, 2.5)),
    ( 40.5,    5,      Goto(X_inner, -X_inner, Z_inner, 2.5)),
    ( 40.5,    6,      Goto(-X_inner, -X_inner, Z_inner, 2.5)),
    ( 40.5,    7,      Goto(-X_inner, X_inner, Z_inner, 2.5)),

    # Go into cube formation

    ( 45,    0,      Goto(X_inner, X_inner, Z_outer, 2.5)),
    ( 45,    1,      Goto(X_inner, -X_inner, Z_outer, 2.5)),
    ( 45,    2,      Goto(-X_inner, -X_inner, Z_outer, 2.5)),
    ( 45,    3,      Goto(-X_inner, X_inner, Z_outer, 2.5)),

    ( 45,    4,      Goto(X_inner, X_inner, Z_center, 2.5)),
    ( 45,    5,      Goto(X_inner, -X_inner, Z_center, 2.5)),
    ( 45,    6,      Goto(-X_inner, -X_inner, Z_center, 2.5)),
    ( 45,    7,      Goto(-X_inner, X_inner, Z_center, 2.5)),   

    ( 45,    8,      Goto(0, 0, Z_inner, 2.5)),


    # Flash lights after each turn

    ( 48,    0,      Ring(255, 255, 255, 1, 0)), 
    ( 48,    1,      Ring(255, 255, 255, 1, 0)),  
    ( 48,    2,      Ring(255, 255, 255, 1, 0)),  
    ( 48,    3,      Ring(255, 255, 255, 1, 0)),  
    ( 48,    4,      Ring(255, 255, 255, 1, 0)), 
    ( 48,    5,      Ring(255, 255, 255, 1, 0)), 
    ( 48,    6,      Ring(255, 255, 255, 1, 0)), 
    ( 48,    7,      Ring(255, 255, 255, 1, 0)), 
    ( 48,    8,      Ring(255, 255, 255, 1, 0)),

    # Start rotation in the cube formation - Clockwise

    ( 50,    0,      Goto(X_inner, -X_inner, Z_outer, 2.5)),
    ( 50,    1,      Goto(-X_inner, -X_inner, Z_outer, 2.5)),
    ( 50,    2,      Goto(-X_inner, X_inner, Z_outer, 2.5)),
    ( 50,    3,      Goto(X_inner, X_inner, Z_outer, 2.5)),

    ( 50,    4,      Goto(X_inner, -X_inner, Z_center, 2.5)),
    ( 50,    5,      Goto(-X_inner, -X_inner, Z_center, 2.5)),
    ( 50,    6,      Goto(-X_inner, X_inner, Z_center, 2.5)),
    ( 50,    7,      Goto(X_inner, X_inner, Z_center, 2.5)),

    # Flash lights after each turn

    ( 50,    0,      Ring(0, 255, 0, 1, 0)), 
    ( 50,    1,      Ring(0, 255, 0, 1, 0)),  
    ( 50,    2,      Ring(0, 255, 0, 1, 0)),  
    ( 50,    3,      Ring(0, 255, 0, 1, 0)),  
    ( 50,    4,      Ring(0, 255, 0, 1, 0)), 
    ( 50,    5,      Ring(0, 255, 0, 1, 0)), 
    ( 50,    6,      Ring(0, 255, 0, 1, 0)), 
    ( 50,    7,      Ring(0, 255, 0, 1, 0)), 
    ( 50,    8,      Ring(0, 255, 0, 1, 0)),

    ( 52.5,    0,      Goto(-X_inner, -X_inner, Z_outer, 2.5)),
    ( 52.5,    1,      Goto(-X_inner, X_inner, Z_outer, 2.5)),
    ( 52.5,    2,      Goto(X_inner, X_inner, Z_outer, 2.5)),
    ( 52.5,    3,      Goto(X_inner, -X_inner, Z_outer, 2.5)),

    ( 52.5,    4,      Goto(-X_inner, -X_inner, Z_center, 2.5)),
    ( 52.5,    5,      Goto(-X_inner, X_inner, Z_center, 2.5)),
    ( 52.5,    6,      Goto(X_inner, X_inner, Z_center, 2.5)),
    ( 52.5,    7,      Goto(X_inner, -X_inner, Z_center, 2.5)),


    # Flash lights after each turn

    ( 52.5,    0,      Ring(255, 255, 0, 1, 0)), 
    ( 52.5,    1,      Ring(255, 255, 0, 1, 0)),  
    ( 52.5,    2,      Ring(255, 255, 0, 1, 0)),  
    ( 52.5,    3,      Ring(255, 255, 0, 1, 0)),  
    ( 52.5,    4,      Ring(255, 255, 0, 1, 0)), 
    ( 52.5,    5,      Ring(255, 255, 0, 1, 0)), 
    ( 52.5,    6,      Ring(255, 255, 0, 1, 0)), 
    ( 52.5,    7,      Ring(255, 255, 0, 1, 0)), 
    ( 52.5,    8,      Ring(255, 255, 0, 1, 0)),

    ( 55,    0,      Goto(-X_inner, X_inner, Z_outer, 2.5)),
    ( 55,    1,      Goto(X_inner, X_inner, Z_outer, 2.5)),
    ( 55,    2,      Goto(X_inner, -X_inner, Z_outer, 2.5)),
    ( 55,    3,      Goto(-X_inner, -X_inner, Z_outer, 2.5)),

    ( 55,    4,      Goto(-X_inner, X_inner, Z_center, 2.5)),
    ( 55,    5,      Goto(X_inner, X_inner, Z_center, 2.5)),
    ( 55,    6,      Goto(X_inner, -X_inner, Z_center, 2.5)),
    ( 55,    7,      Goto(-X_inner, -X_inner, Z_center, 2.5)),

    # Flash lights after each turn

    ( 55,    0,      Ring(0, 255, 255, 1, 0)), 
    ( 55,    1,      Ring(0, 255, 255, 1, 0)),  
    ( 55,    2,      Ring(0, 255, 255, 1, 0)),  
    ( 55,    3,      Ring(0, 255, 255, 1, 0)),  
    ( 55,    4,      Ring(0, 255, 255, 1, 0)), 
    ( 55,    5,      Ring(0, 255, 255, 1, 0)), 
    ( 55,    6,      Ring(0, 255, 255, 1, 0)), 
    ( 55,    7,      Ring(0, 255, 255, 1, 0)), 
    ( 55,    8,      Ring(0, 255, 255, 1, 0)),


    ( 57.5,    0,      Goto(X_inner, X_inner, Z_outer, 2.5)),
    ( 57.5,    1,      Goto(X_inner, -X_inner, Z_outer, 2.5)),
    ( 57.5,    2,      Goto(-X_inner, -X_inner, Z_outer, 2.5)),
    ( 57.5,    3,      Goto(-X_inner, X_inner, Z_outer, 2.5)),

    ( 57.5,    4,      Goto(X_inner, X_inner, Z_center, 2.5)),
    ( 57.5,    5,      Goto(X_inner, -X_inner, Z_center, 2.5)),
    ( 57.5,    6,      Goto(-X_inner, -X_inner, Z_center, 2.5)),
    ( 57.5,    7,      Goto(-X_inner, X_inner, Z_center, 2.5)), 

    # Flash lights after each turn

    ( 57.5,    0,      Ring(128, 0, 128, 1, 0)), 
    ( 57.5,    1,      Ring(128, 0, 128, 1, 0)),  
    ( 57.5,    2,      Ring(128, 0, 128, 1, 0)),  
    ( 57.5,    3,      Ring(128, 0, 128, 1, 0)),  
    ( 57.5,    4,      Ring(128, 0, 128, 1, 0)), 
    ( 57.5,    5,      Ring(128, 0, 128, 1, 0)), 
    ( 57.5,    6,      Ring(128, 0, 128, 1, 0)), 
    ( 57.5,    7,      Ring(128, 0, 128, 1, 0)), 
    ( 57.5,    8,      Ring(128, 0, 128, 1, 0)),    

    # Goto back to starting formation
    ( 60,     0,      Goto(X_outer, X_outer, Z_outer, 2.5)),
    ( 60,     1,      Goto(X_outer, -X_outer, Z_outer, 2.5)),
    ( 60,     2,      Goto(-X_outer, -X_outer, Z_outer, 2.5)),
    ( 60,     3,      Goto(-X_outer, X_outer, Z_outer, 2.5)),

    ( 65,    0,      Ring(255, 255, 255, 1, 0)), 
    ( 65,    1,      Ring(255, 255, 255, 1, 0)),  
    ( 65,    2,      Ring(255, 255, 255, 1, 0)),  
    ( 65,    3,      Ring(255, 255, 255, 1, 0)), 

    ( 67,     4,      Goto(X_inner, X_inner, Z_inner, 2.5)),
    ( 67,     5,      Goto(X_inner, -X_inner, Z_inner, 2.5)),
    ( 67,     6,      Goto(-X_inner, -X_inner, Z_inner, 2.5)),
    ( 67,     7,      Goto(-X_inner, X_inner, Z_inner, 2.5)),

    ( 69,    4,      Ring(255, 255, 255, 1, 0)), 
    ( 69,    5,      Ring(255, 255, 255, 1, 0)),  
    ( 69,    6,      Ring(255, 255, 255, 1, 0)),  
    ( 69,    7,      Ring(255, 255, 255, 1, 0)), 

    ( 71,     8,      Goto(0, 0, Z_center, 1)),
    ( 73,     8,      Ring(255, 255, 255, 1, 0)), 

    # Land all crazyflies

    ( 75,    0,      Land(3)),
    ( 75,    1,      Land(3)),
    ( 75,    2,      Land(3)),
    ( 75,    3,      Land(3)),
    ( 75,    4,      Land(3)),
    ( 75,    5,      Land(3)),
    ( 75,    6,      Land(3)),
    ( 75,    7,      Land(3)),
    ( 75,    8,      Land(3)),

    # Turn off lights on all crazyflies

    ( 78,    0,      Ring(0,0,0,0, 5)),
    ( 78,    1,      Ring(0,0,0,0, 5)),
    ( 78,    2,      Ring(0,0,0,0, 5)),
    ( 78,    3,      Ring(0,0,0,0, 5)),
    ( 78,    4,      Ring(0,0,0,0, 5)),
    ( 78,    5,      Ring(0,0,0,0, 5)), 
    ( 78,    6,      Ring(0,0,0,0, 5)),
    ( 78,    7,      Ring(0,0,0,0, 5)),
    ( 78,    8,      Ring(0,0,0,0, 5)),
]

"""
sequence = [
    # Step, CF_id,  action
    ( 0,    0,      Takeoff(0.5, 2.5)),
    ( 0,    2,      Takeoff(0.5, 2.5)),

    ( 1,    1,      Takeoff(1.0, 2)),
    
    ( 2,    0,      Goto(-0.5,  -0.5,   0.5, 1)),
    ( 2,    2,      Goto(0.5,  0.5,   0.5, 1)),
    
    ( 3,    1,      Goto(0,  0,   1, 1)),
    
    ( 4,    0,      Ring(255, 255, 255, 0.2, 0)),
    ( 4,    1,      Ring(255, 0, 0, 0.2, 0)),
    ( 4,    2,      Ring(255, 255, 255, 0.2, 0)),
    
    ( 5,    0,      Goto(0.5, -0.5, 0.5, 2)),
    ( 5,    2,      Goto(-0.5, 0.5, 0.5, 2)),

    ( 7,    0,      Goto(0.5, 0.5, 0.5, 2)),
    ( 7,    2,      Goto(-0.5, -0.5, 0.5, 2)),

    ( 9,    0,      Goto(-0.5, 0.5, 0.5, 2)),
    ( 9,    2,      Goto(0.5, -0.5, 0.5, 2)),

    ( 11,   0,      Goto(-0.5, -0.5, 0.5, 2)),
    ( 11,   2,      Goto(0.5, 0.5, 0.5, 2)),

    ( 13,    0,      Land(2)),
    ( 13,    1,      Land(2)),
    ( 13,    2,      Land(2)),
    
    ( 15,    0,      Ring(0,0,0,0, 5)),
    ( 15,    1,      Ring(0,0,0,0, 5)),
    ( 15,    2,      Ring(0,0,0,0, 5)),
]
"""
def wait_for_position_estimator(scf):
    print('Waiting for estimator to find position...')

    log_config = LogConfig(name='Kalman Variance', period_in_ms=500)
    log_config.add_variable('kalman.varPX', 'float')
    log_config.add_variable('kalman.varPY', 'float')
    log_config.add_variable('kalman.varPZ', 'float')

    var_y_history = [1000] * 10
    var_x_history = [1000] * 10
    var_z_history = [1000] * 10

    threshold = 0.001

    with SyncLogger(scf, log_config) as logger:
        for log_entry in logger:
            data = log_entry[1]

            var_x_history.append(data['kalman.varPX'])
            var_x_history.pop(0)
            var_y_history.append(data['kalman.varPY'])
            var_y_history.pop(0)
            var_z_history.append(data['kalman.varPZ'])
            var_z_history.pop(0)

            min_x = min(var_x_history)
            max_x = max(var_x_history)
            min_y = min(var_y_history)
            max_y = max(var_y_history)
            min_z = min(var_z_history)
            max_z = max(var_z_history)

            # print("{} {} {}".
            #       format(max_x - min_x, max_y - min_y, max_z - min_z))

            if (max_x - min_x) < threshold and (
                    max_y - min_y) < threshold and (
                    max_z - min_z) < threshold:
                break


def reset_estimator(scf):
    cf = scf.cf
    cf.param.set_value('kalman.resetEstimation', '1')
    time.sleep(0.1)
    cf.param.set_value('kalman.resetEstimation', '0')
    wait_for_position_estimator(scf)


def activate_high_level_commander(scf):
    scf.cf.param.set_value('commander.enHighLevel', '1')


def activate_mellinger_controller(scf, use_mellinger):
    controller = 1
    if use_mellinger:
        controller = 2
    scf.cf.param.set_value('stabilizer.controller', str(controller))


def set_ring_color(cf, r, g, b, intensity, time):
    cf.param.set_value('ring.fadeTime', str(time))

    r *= intensity
    g *= intensity
    b *= intensity

    color = (int(r) << 16) | (int(g) << 8) | int(b)

    cf.param.set_value('ring.fadeColor', str(color))


def crazyflie_control(scf):
    cf = scf.cf
    control = controlQueues[uris.index(cf.link_uri)]

    activate_mellinger_controller(scf, True)

    commander = scf.cf.high_level_commander

    # Set fade to color effect and reset to Led-ring OFF
    set_ring_color(cf, 0,0,0, 0, 0)
    cf.param.set_value('ring.effect', '14')

    while True:
        command = control.get()
        if type(command) is Quit:
            return
        elif type(command) is Takeoff:
            commander.takeoff(command.height, command.time)
        elif type(command) is Land:
            commander.land(0.0, command.time)
        elif type(command) is Goto:
            commander.go_to(command.x, command.y, command.z, 0, command.time)
        elif type(command) is Ring:
            set_ring_color(cf, command.r, command.g, command.b,
                          command.intensity, command.time)
            pass
        else:
            print("Warning! unknown command {} for uri {}".format(command,
                                                                  cf.uri))

def control_thread():
    pointer = 0
    step = 0
    stop = False

    while not stop:
        print("Step {}:".format(step))
        while sequence[pointer][0] <= step:
            cf_id = sequence[pointer][1]
            command = sequence[pointer][2]

            print(" - Running: {} on {}".format(command, cf_id))
            controlQueues[cf_id].put(command)
            pointer += 1

            if pointer >= len(sequence):
                print("Reaching the end of the sequence, stopping!")
                stop = True
                break

        step += 1
        time.sleep(STEP_TIME)
    
    for ctrl in controlQueues:
        ctrl.put(Quit())

if __name__ == '__main__':
    controlQueues = [Queue() for _ in range(len(uris))]
        
    cflib.crtp.init_drivers(enable_debug_driver=False)
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        swarm.parallel_safe(activate_high_level_commander)
        swarm.parallel_safe(reset_estimator)

        print("Starting sequence!")

        threading.Thread(target=control_thread).start()

        swarm.parallel_safe(crazyflie_control)

        time.sleep(1)
