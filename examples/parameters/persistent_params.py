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

* All persistent parameters are fectched and the current state is printed out.
* The LED ring effect is set to a new value and stored.
* The LED ring effect persisted value is cleared.

Note: this script will change the value of the LED ring.effect parameter
"""
import logging
import sys
from threading import Event

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

# uri = uri_helper.uri_from_env(default='usb://0')
uri = uri_helper.uri_from_env(default='radio://0/30/2M/E7E7E7E7E7')

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


def get_persistent_state(cf, complete_param_name):
    wait_for_callback_event = Event()

    def state_callback(complete_name, state):
        print(f'{complete_name}: {state}')
        wait_for_callback_event.set()

    cf.param.persistent_get_state(complete_param_name, state_callback)
    wait_for_callback_event.wait()


def persist_parameter(cf, complete_param_name):
    wait_for_callback_event = Event()

    def is_stored_callback(complete_name, success):
        if success:
            print(f'Persisted {complete_name}!')
        else:
            print(f'Failed to persist {complete_name}!')
        wait_for_callback_event.set()

    cf.param.persistent_store(complete_param_name, callback=is_stored_callback)
    wait_for_callback_event.wait()


def clear_persistent_parameter(cf, complete_param_name):
    wait_for_callback_event = Event()

    def is_stored_cleared(complete_name, success):
        if success:
            print(f'Cleared {complete_name}!')
        else:
            print(f'Failed to clear {complete_name}!')
        wait_for_callback_event.set()

    cf.param.persistent_clear(complete_param_name, callback=is_stored_cleared)
    wait_for_callback_event.wait()


def get_all_persistent_param_names(cf):
    persistent_params = []
    for group_name, params in cf.param.toc.toc.items():
        for param_name, element in params.items():
            if element.is_persistent():
                complete_name = group_name + '.' + param_name
                persistent_params.append(complete_name)

    return persistent_params


if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    cf = Crazyflie(rw_cache='./cache')

    with SyncCrazyflie(uri, cf=cf) as scf:
        # Get the names of all parameters that can be persisted
        persistent_params = get_all_persistent_param_names(scf.cf)

        if not persistent_params:
            print('No persistent parameters')
            sys.exit(0)

        # Get the state of all persistent parameters
        print('-- All persistent parameters --')
        for complete_name in persistent_params:
            get_persistent_state(scf.cf, complete_name)

        print()
        param_name = 'ring.effect'
        param_value = 10

        print(f'Set parameter {param_name} to {param_value}')
        scf.cf.param.set_value(param_name, param_value)

        print()
        print('Store the new value in persistent memory')
        persist_parameter(scf.cf, param_name)

        print('The new state is:')
        get_persistent_state(scf.cf, param_name)

        print()
        print('Clear the persisted parameter')
        clear_persistent_parameter(scf.cf, param_name)

        print('The new state is:')
        get_persistent_state(scf.cf, param_name)
