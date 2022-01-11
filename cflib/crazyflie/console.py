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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
Crazyflie console is used to receive characters printed using printf
from the firmware.
"""
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.callbacks import Caller

__author__ = 'Bitcraze AB'
__all__ = ['Console']


class Console:
    """
    Crazyflie console is used to receive characters printed using printf
    from the firmware.
    """

    def __init__(self, crazyflie):
        """
        Initialize the console and register it to receive data from the copter.
        """

        self.receivedChar = Caller()
        """
        This member variable is used to setup a callback that will be called
        when text is received from the CONSOLE port of CRTP (0).

        Example:
        ```python
        [...]

        def log_console(self, text):
            self.log_file.write(text)

        [...]

        self.cf.console.receivedChar.add_callback(self.log_console)
        ```
        """

        self.cf = crazyflie
        self.cf.add_port_callback(CRTPPort.CONSOLE, self._incoming)

    def _incoming(self, packet):
        """
        Callback for data received from the copter.
        """
        # This might be done prettier ;-)
        console_text = packet.data.decode('UTF-8')

        self.receivedChar.call(console_text)
