#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2017 Bitcraze AB
#
#  Crazyflie Python Library
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
Example scipts that allows a user to "push" the Crazyflie 2.0 around
using their hands while it's hovering.

This examples uses the Flow and Multi-ranger decks to read out distances
in all directions and tries to keep away from anything that comes closer
than 0.2m by setting a velocity in the oposite direction.

The demo is ended by either pressing Ctrl-C or by "pushing" the Crazyflie 2.0
down so it get's closer than 0.1m to the surface it's hoving above.

For the example to run the following hardware is needed:
 * Crazyflie 2.0
 * Crazyradio PA
 * Flow deck
 * Multi-ranger deck
"""
import logging
import time
import sys

import cflib.crtp
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger

URI = 'radio://0/80/250K'

if len(sys.argv) > 1:
    URI = sys.argv[1]

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


if __name__ == '__main__':
    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(URI) as scf:
        cf = scf.cf

        # Reset Kalman filter on startup
        cf.param.set_value('kalman.resetEstimation', '1')
        time.sleep(0.1)
        cf.param.set_value('kalman.resetEstimation', '0')
        time.sleep(2)

        # Start logblock with distances in all directions at 100Hz
        lg_oa = LogConfig(name='OA', period_in_ms=10)
        lg_oa.add_variable('oa.front')
        lg_oa.add_variable('oa.back')
        lg_oa.add_variable('oa.up')
        lg_oa.add_variable('oa.left')
        lg_oa.add_variable('oa.right')
        lg_oa.add_variable('range.zrange')

        # The max ramp up velocity
        max_vel = 1.0 # m/s
        # The detection radius (front/back/left/right/up)
        radius = 0.2 # m
        # The hover height (down)
        height_sp = 0.2 # m
        # Threashold for switching off the Crazyflie when pushed down
        landing_height = 0.1 # m
        # Factor for raming up when keeping radius
        factor = max_vel / radius
        # Should we stop flying or not
        stop = False

        with SyncLogger(scf, lg_oa) as logger:
            # Running at 100Hz
            for log_entry in logger:
                # Various vabiables that are sent together with the
                # log data but not used in this example
                timestamp = log_entry[0]
                data = log_entry[1]
                logconf_name = log_entry[2]

                # Distances are reported in mm, convert into m
                fw_distance = data["oa.front"] / 1000.0
                bk_distance = data["oa.back"] / 1000.0
                r_distance = data["oa.right"] / 1000.0
                l_distance = data["oa.left"] / 1000.0
                up_distance = data["oa.up"] / 1000.0
                down_distance = data["range.zrange"] / 1000.0

                # Calculate the distance inside the radius
                #   X    <----)
                fw_o = radius - min(fw_distance, radius)
                bk_o = radius - min(bk_distance, radius)
                l_o = radius - min(l_distance, radius)
                r_o = radius - min(r_distance, radius)
                u_o = radius - min(up_distance, radius)

                # Weigh together oposite sides. I.e if you are getting close
                # on both sides they are both taken into account.
                fw_comp = (-1) * fw_o * factor
                bk_comp = bk_o * factor
                fw_vel = fw_comp + bk_comp

                l_comp = (-1) * l_o * factor
                r_comp = r_o * factor
                side_vel = l_comp + r_comp

                height = height_sp - u_o

                # If we should still be flying send the hover set-points
                # Note that these are in meters and meters/second
                if not stop:
                    cf.commander.send_hover_setpoint(fw_vel, side_vel, 0, height)

                # If we're pushing the Crazyflie towards the ground it will
                # shut down if you get close enough
                if down_distance < landing_height and height < height_sp:
                    stop = True
                    cf.commander.send_stop_setpoint()
                    print("Demo terminated!")
                    sys.exit(1)
