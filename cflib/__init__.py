#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2013 Bitcraze AB
#
#  Crazyflie Nano Quadcopter Client
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
The Crazyflie Micro Quadcopter library API used to communicate with the
Crazyflie Micro Quadcopter via a communication link.

The API takes care of scanning, opening and closing the communication link
as well as sending/receiving data from the Crazyflie.

A link is described using an URI of the following format:
    <interface>://<interface defined data>.
See each link for the data that can be included in the URI for that interface.

The two main uses-cases are scanning for Crazyflies available on a
communication link and opening a communication link to a Crazyflie.

Example of scanning for available Crazyflies on all communication links:
cflib.crtp.init_drivers()
available = cflib.crtp.scan_interfaces()
for i in available:
    print "Found Crazyflie on URI [%s] with comment [%s]"
            % (available[0], available[1])

Example of connecting to a Crazyflie with know URI (radio dongle 0 and
radio channel 125):
cf = Crazyflie()
cf.open_link("radio://0/125")
...
cf.close_link()
"""
