# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2014 Bitcraze AB
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
Simple example that connects to the first Crazyflie found, triggers
reading of all the parameters and displays their values. It then modifies
one parameter and reads back it's value. Finally it disconnects.
"""
import logging
import random
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


class ParamExample:
    """
    Simple logging example class that logs the Stabilizer from a supplied
    link uri and disconnects after 5s.
    """

    def __init__(self, link_uri):
        """ Initialize and run the example with the specified link_uri """

        # Create a Crazyflie object without specifying any cache dirs
        self._cf = Crazyflie()

        # Connect some callbacks from the Crazyflie API
        self._cf.connected.add_callback(self._connected)
        self._cf.disconnected.add_callback(self._disconnected)
        self._cf.connection_failed.add_callback(self._connection_failed)
        self._cf.connection_lost.add_callback(self._connection_lost)

        print('Connecting to %s' % link_uri)

        # Try to connect to the Crazyflie
        self._cf.open_link(link_uri)

        # Variable used to keep main loop occupied until disconnect
        self.is_connected = True

        self._param_check_list = []
        self._param_groups = []

        random.seed()

    def _connected(self, link_uri):
        """ This callback is called form the Crazyflie API when a Crazyflie
        has been connected and the TOCs have been downloaded."""
        print('Connected to %s' % link_uri)

        # Print the param TOC
        p_toc = self._cf.param.toc.toc
        for group in sorted(p_toc.keys()):
            print('{}'.format(group))
            for param in sorted(p_toc[group].keys()):
                print('\t{}'.format(param))
                self._param_check_list.append('{0}.{1}'.format(group, param))
            self._param_groups.append('{}'.format(group))
            # For every group, register the callback
            self._cf.param.add_update_callback(group=group, name=None,
                                               cb=self._param_callback)

        # You can also register a callback for a specific group.name combo
        self._cf.param.add_update_callback(group='cpu', name='flash',
                                           cb=self._cpu_flash_callback)

        print('')

    def _cpu_flash_callback(self, name, value):
        """Specific callback for the cpu.flash parameter"""
        print('The connected Crazyflie has {}kb of flash'.format(value))

    def _param_callback(self, name, value):
        """Generic callback registered for all the groups"""
        print('{0}: {1}'.format(name, value))

        # Remove each parameter from the list and close the link when
        # all are fetched
        self._param_check_list.remove(name)
        if len(self._param_check_list) == 0:
            print('Have fetched all parameter values.')

            # First remove all the group callbacks
            for g in self._param_groups:
                self._cf.param.remove_update_callback(group=g,
                                                      cb=self._param_callback)

            # Create a new random value [0.00,1.00] for pid_attitude.pitch_kd
            # and set it
            pkd = random.random()
            print('')
            print('Write: pid_attitude.pitch_kd={:.2f}'.format(pkd))
            self._cf.param.add_update_callback(group='pid_attitude',
                                               name='pitch_kd',
                                               cb=self._a_pitch_kd_callback)
            # When setting a value the parameter is automatically read back
            # and the registered callbacks will get the updated value
            self._cf.param.set_value('pid_attitude.pitch_kd',
                                     '{:.2f}'.format(pkd))

    def _a_pitch_kd_callback(self, name, value):
        """Callback for pid_attitude.pitch_kd"""
        print('Readback: {0}={1}'.format(name, value))

        # End the example by closing the link (will cause the app to quit)
        self._cf.close_link()

    def _connection_failed(self, link_uri, msg):
        """Callback when connection initial connection fails (i.e no Crazyflie
        at the specified address)"""
        print('Connection to %s failed: %s' % (link_uri, msg))
        self.is_connected = False

    def _connection_lost(self, link_uri, msg):
        """Callback when disconnected after a connection has been made (i.e
        Crazyflie moves out of range)"""
        print('Connection to %s lost: %s' % (link_uri, msg))

    def _disconnected(self, link_uri):
        """Callback when the Crazyflie is disconnected (called in all cases)"""
        print('Disconnected from %s' % link_uri)
        self.is_connected = False


if __name__ == '__main__':
    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)
    # Scan for Crazyflies and use the first one found
    print('Scanning interfaces for Crazyflies...')
    available = cflib.crtp.scan_interfaces()
    print('Crazyflies found:')
    for i in available:
        print(i[0])

    if len(available) > 0:
        pe = ParamExample(available[0][0])
        # The Crazyflie lib doesn't contain anything to keep the application
        # alive, so this is where your application should do something. In our
        # case we are just waiting until we are disconnected.
        while pe.is_connected:
            time.sleep(1)
    else:
        print('No Crazyflies found, cannot run example')
