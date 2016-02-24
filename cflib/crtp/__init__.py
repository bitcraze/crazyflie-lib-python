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

from .radiodriver import RadioDriver
from .udpdriver import UdpDriver
from .serialdriver import SerialDriver
from .debugdriver import DebugDriver
from .usbdriver import UsbDriver
from .exceptions import WrongUriType

__author__ = 'Bitcraze AB'
__all__ = []

logger = logging.getLogger(__name__)


DRIVERS = [RadioDriver, SerialDriver, UdpDriver, DebugDriver, UsbDriver]
INSTANCES = []


def init_drivers(enable_debug_driver=False):
    """Initialize all the drivers."""
    for driver in DRIVERS:
        try:
            if driver != DebugDriver or enable_debug_driver:
                INSTANCES.append(driver())
        except Exception:  # pylint: disable=W0703
            continue


def scan_interfaces(address=None):
    """ Scan all the interfaces for available Crazyflies """
    available = []
    found = []
    for instance in INSTANCES:
        logger.debug("Scanning: %s", instance)
        try:
            found = instance.scan_interface(address)
            available += found
        except Exception:
            raise
    return available


def get_interfaces_status():
    """Get the status of all the interfaces"""
    status = {}
    for instance in INSTANCES:
        try:
            status[instance.get_name()] = instance.get_status()
        except Exception:
            raise
    return status


def get_link_driver(uri, link_quality_callback=None, link_error_callback=None):
    """Return the link driver for the given URI. Returns None if no driver
    was found for the URI or the URI was not well formatted for the matching
    driver."""
    for instance in INSTANCES:
        try:
            instance.connect(uri, link_quality_callback, link_error_callback)
            return instance
        except WrongUriType:
            continue

    return None
