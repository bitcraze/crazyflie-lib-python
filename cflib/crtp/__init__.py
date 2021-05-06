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
"""Scans and creates communication interfaces."""
import logging
import os
import platform

from .exceptions import WrongUriType
from .prrtdriver import PrrtDriver
from .radiodriver import RadioDriver
from .serialdriver import SerialDriver
from .udpdriver import UdpDriver
from .usbdriver import UsbDriver

__author__ = 'Bitcraze AB'
__all__ = []

logger = logging.getLogger(__name__)


CLASSES = []


def init_drivers(enable_debug_driver=False, enable_serial_driver=False):
    """Initialize all the drivers."""

    def append_cpp():
        from .cflinkcppdriver import CfLinkCppDriver
        CLASSES.append(CfLinkCppDriver)

    def append_python():
        CLASSES.extend([RadioDriver, UsbDriver])

    env = os.getenv('USE_CFLINK')
    if env is None:  # this is default behavior
        mach = platform.machine()  # cflinkcpp only supports x86_64
        if mach in ['x86_64']:
            append_cpp()
        else:  # on non-x86_64 machines, fall-back to python
            append_python()

    else:  # if USE_CFLINK override is used, enforce it.
        if env == 'cpp':
            append_cpp()
        elif env == 'python':
            append_python()
        else:
            raise Exception('The cflink "{}" is not supported'.format(env))

    if enable_debug_driver:
        logger.warn('The debug driver is no longer supported!')

    if enable_serial_driver:
        CLASSES.append(SerialDriver)

    CLASSES.extend([UdpDriver, PrrtDriver])


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
