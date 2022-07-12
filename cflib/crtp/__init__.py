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
"""Scans and creates communication interfaces."""
import logging
import os

from .exceptions import WrongUriType
from .prrtdriver import PrrtDriver
from .radiodriver import RadioDriver
from .serialdriver import SerialDriver
from .tcpdriver import TcpDriver
from .udpdriver import UdpDriver
from .usbdriver import UsbDriver

__author__ = 'Bitcraze AB'
__all__ = []

logger = logging.getLogger(__name__)


CLASSES = []


def init_drivers(enable_debug_driver=False, enable_serial_driver=False):
    """Initialize all the drivers."""

    env = os.getenv('USE_CFLINK')
    if env is not None and env == 'cpp':
        from .cflinkcppdriver import CfLinkCppDriver
        CLASSES.append(CfLinkCppDriver)
    else:
        CLASSES.extend([RadioDriver, UsbDriver])

    if enable_debug_driver:
        logger.warn('The debug driver is no longer supported!')

    if enable_serial_driver:
        CLASSES.append(SerialDriver)

    CLASSES.extend([UdpDriver, PrrtDriver, TcpDriver])


def scan_interfaces(address=None):
    """ Scan all the interfaces for available Crazyflies """
    available = []
    found = []
    for driverClass in CLASSES:
        try:
            logger.debug('Scanning: %s', driverClass)
            instance = driverClass()
            found = instance.scan_interface(address)
            available += found
        except Exception:
            raise
    return available


def get_interfaces_status():
    """Get the status of all the interfaces"""
    status = {}
    for driverClass in CLASSES:
        try:
            instance = driverClass()
            status[instance.get_name()] = instance.get_status()
        except Exception:
            raise
    return status


def get_link_driver(uri, link_quality_callback=None, link_error_callback=None):
    """Return the link driver for the given URI. Returns None if no driver
    was found for the URI or the URI was not well formatted for the matching
    driver."""
    for driverClass in CLASSES:
        try:
            instance = driverClass()
            instance.connect(uri, link_quality_callback, link_error_callback)
            return instance
        except WrongUriType:
            continue

    return None
