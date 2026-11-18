#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2026 Bitcraze AB
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
import codecs

from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.callbacks import Caller

__author__ = 'Bitcraze AB'
__all__ = ['Console']

LOCAL_CHANNEL = 0


def _new_decoder():
    """
    Return an incremental UTF-8 decoder. It keeps a character split across
    packets until its last byte arrives, and replaces invalid bytes instead of
    raising.
    """
    return codecs.getincrementaldecoder('utf-8')(errors='replace')


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
        when text is received from the Crazyflie's own console (CRTP port 0,
        channel 0). This works with every firmware version.

        The text arrives in chunks of up to 30 bytes. A chunk can end in the
        middle of a line, so do not add a newline after each one.

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
        self._local_decoder = _new_decoder()
        self.cf.add_header_callback(self._incoming, CRTPPort.CONSOLE, LOCAL_CHANNEL)
        self.cf.disconnected.add_callback(self._disconnected)

    def _disconnected(self, link_uri):
        # Do not complete a character with bytes from another connection
        self._local_decoder = _new_decoder()

    def _incoming(self, packet):
        """
        Callback for data received from the copter.
        """
        console_text = self._local_decoder.decode(packet.data)
        if console_text:
            self.receivedChar.call(console_text)
