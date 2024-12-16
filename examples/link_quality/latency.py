# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2024 Bitcraze AB
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
import time

import cflib.crtp  # noqa
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

# Reads the CFLIB_URI environment variable for URI or uses default
uri = uri_helper.uri_from_env(default='radio://0/90/2M/E7E7E7E7E7')


def latency_callback(latency: float):
    """A callback to run when we get an updated latency estimate"""
    print(f'Latency: {latency:.3f} ms')


if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    # Create Crazyflie object, with cache to avoid re-reading param and log TOC
    cf = Crazyflie(rw_cache='./cache')

    # Add a callback to whenever we receive an updated latency estimate
    #
    # This could also be a Python lambda, something like:
    cf.link_statistics.latency.latency_updated.add_callback(latency_callback)

    # This will connect the Crazyflie with the URI specified above.
    with SyncCrazyflie(uri, cf=cf) as scf:
        print('[host] Connected, use ctrl-c to quit.')

        while True:
            time.sleep(1)
