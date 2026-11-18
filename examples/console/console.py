# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2026 Bitcraze AB
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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
Shows the consoles of a Crazyflie, such as the Crazyflie's own console
(cf:stm32) and the Camera Deck's console (deck:bcCam).

The example connects to a Crazyflie, lists its consoles and prints the output
of every console, each line prefixed with the console's path. It starts with
the output received since connection, such as startup messages, and then
prints new output until Ctrl+C is pressed.

To show only some consoles, pass their paths as arguments:

    python console.py deck:bcCam

Firmware older than CRTP protocol version 13 only has the cf:stm32 console.

Change the URI variable to your Crazyflie configuration.
"""
import logging
import sys
import time
from contextlib import ExitStack

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.console import ConsoleError
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

# URI to the Crazyflie to connect to
uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


def print_with_prefix(path):
    """Return a callback that prints each console line with its path."""
    def print_line(line):
        print(f'[{path}] {line}')
    return print_line


if __name__ == '__main__':
    cflib.crtp.init_drivers()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        console = scf.cf.console

        available = console.list()
        print('Consoles on this Crazyflie:', ', '.join(available))

        paths = sys.argv[1:] or available

        # ExitStack closes every opened console when the block ends. Closing
        # the last handle of a console asks the Crazyflie to stop sending it.
        with ExitStack() as opened:
            for path in paths:
                try:
                    handle = console.open(path, line_cb=print_with_prefix(path))
                except ConsoleError as e:
                    print(f'Could not open {path}: {e}')
                    continue
                opened.enter_context(handle)

            print('Printing console output, press Ctrl+C to stop')
            try:
                while True:
                    print(scf.cf.param.get_value('supervisor.infdmp'))
                    if scf.cf.param.get_value('supervisor.infdmp') == '0':
                        scf.cf.param.set_value('supervisor.infdmp', '1')
                        time.sleep(0.3)
                    else:
                        scf.cf.param.set_value('supervisor.infdmp', '0')
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
