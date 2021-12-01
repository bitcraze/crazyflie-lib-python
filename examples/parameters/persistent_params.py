# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2021 Bitcraze AB
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
Example to show the use of persistent parameters.

All persistent parameters are fectched and the current state is printed out.
Finallay the LED ring effect is set to a new value and stored.

Note: this script will change the value of the LED ring.effect parameter
"""
import logging
import sys
from threading import Event

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper


uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    cf = Crazyflie(rw_cache='./cache')
    with SyncCrazyflie(uri, cf=cf) as scf:
        wait_for_callback_event = Event()

        # Collect the names of all persistent parameters
        persistent_params = []
        for group_name, params in scf.cf.param.toc.toc.items():
            for param_name, element in params.items():
                if element.is_persistent():
                    complete_name = group_name + '.' + param_name
                    persistent_params.append(complete_name)

        if len(persistent_params) == 0:
            print('No persistent parameters')
            sys.exit(0)

        # Get state for the persistent parameters
        print('-- All persistent parameters --')

        def state_callback(complete_name, state):
            print(complete_name, state)

            persistent_params.pop(0)
            if len(persistent_params) > 0:
                scf.cf.param.persistent_get_state(persistent_params[0], state_callback)
            else:
                wait_for_callback_event.set()

        wait_for_callback_event.clear()
        # Request the state for the first parameter. The callback will pop the name from the list
        # and request the next
        scf.cf.param.persistent_get_state(persistent_params[0], state_callback)
        # Wait for all parameters to be done
        wait_for_callback_event.wait()

        print()
        print('-- Set the default LED ring effect --')
        led_ring_param_name = 'ring.effect'
        scf.cf.param.set_value(led_ring_param_name, 7)

        def is_stored_callback():
            print('New LED ring effect is persisted')
            wait_for_callback_event.set()

        wait_for_callback_event.clear()
        scf.cf.param.persistent_store(led_ring_param_name, callback=is_stored_callback)
        wait_for_callback_event.wait()
