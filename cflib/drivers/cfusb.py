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
"""
USB driver for the Crazyflie.
"""
import logging
import os

import usb

__author__ = 'Bitcraze AB'
__all__ = ['CfUsb']

logger = logging.getLogger(__name__)

USB_VID = 0x0483
USB_PID = 0x5740

try:
    import usb.core

    pyusb_backend = None
    if os.name == 'nt':
        import usb.backend.libusb0 as libusb0

        pyusb_backend = libusb0.get_backend()
    pyusb1 = True

except Exception:
    pyusb1 = False


def _find_devices():
    """
    Returns a list of CrazyRadio devices currently connected to the computer
    """
    ret = []

    logger.info('Looking for devices....')

    if pyusb1:
        for d in usb.core.find(idVendor=USB_VID, idProduct=USB_PID, find_all=1,
                               backend=pyusb_backend):
            if d.manufacturer == 'Bitcraze AB':
                ret.append(d)
    else:
        busses = usb.busses()
        for bus in busses:
            for device in bus.devices:
                if device.idVendor == USB_VID:
                    if device.idProduct == USB_PID:
                        ret += [device, ]

    return ret


class CfUsb:
    """ Used for communication with the Crazyradio USB dongle """

    def __init__(self, device=None, devid=0):
        """ Create object and scan for USB dongle if no device is supplied """
        self.dev = None
        self.handle = None
        self._last_write = 0
        self._last_read = 0

        if device is None:
            devices = _find_devices()
            try:
                self.dev = devices[devid]
            except Exception:
                self.dev = None

        if self.dev:
            if (pyusb1 is True):
                self.dev.set_configuration(1)
                self.handle = self.dev
                self.version = float(
                    '{0:x}.{1:x}'.format(self.dev.bcdDevice >> 8,
                                         self.dev.bcdDevice & 0x0FF))
            else:
                self.handle = self.dev.open()
                self.handle.setConfiguration(1)
                self.handle.claimInterface(0)
                self.version = float(self.dev.deviceVersion)

    def get_serial(self):
        # The signature for get_string has changed between versions to 1.0.0b1,
        # 1.0.0b2 and 1.0.0. Try the old signature first, if that fails try
        # the newer one.
        try:
            return usb.util.get_string(self.dev, 255, self.dev.iSerialNumber)
        except (usb.core.USBError, ValueError):
            return usb.util.get_string(self.dev, self.dev.iSerialNumber)

    def close(self):
        if (pyusb1 is False):
            if self.handle:
                self.handle.releaseInterface()
        else:
            if self.dev:
                usb.util.dispose_resources(self.dev)

        self.handle = None
        self.dev = None

    def scan(self):
        # TODO: Currently only supports one device
        if self.dev:
            return [('usb://0', '')]
        return []

    def set_crtp_to_usb(self, crtp_to_usb):
        if crtp_to_usb:
            _send_vendor_setup(self.handle, 0x01, 0x01, 1, ())
        else:
            _send_vendor_setup(self.handle, 0x01, 0x01, 0, ())

    # Data transfers
    def send_packet(self, dataOut):
        """ Send a packet and receive the ack from the radio dongle
            The ack contains information about the packet transmission
            and a data payload if the ack packet contained any """
        try:
            if (pyusb1 is False):
                self.handle.bulkWrite(1, dataOut, 20)
            else:
                self.handle.write(endpoint=1, data=dataOut, timeout=20)
        except usb.USBError:
            pass

    def receive_packet(self):
        dataIn = ()
        try:
            if (pyusb1 is False):
                dataIn = self.handle.bulkRead(0x81, 64, 20)
            else:
                dataIn = self.handle.read(0x81, 64, timeout=20)
        except usb.USBError as e:
            try:
                if e.backend_error_code == -7 or e.backend_error_code == -116:
                    # Normal, the read was empty
                    pass
                else:
                    raise IOError('Crazyflie disconnected')
            except AttributeError:
                # pyusb < 1.0 doesn't implement getting the underlying error
                # number and it seems as if it's not possible to detect
                # if the cable is disconnected. So this detection is not
                # supported, but the "normal" case will work.
                pass

        return dataIn


# Private utility functions
def _send_vendor_setup(handle, request, value, index, data):
    if pyusb1:
        handle.ctrl_transfer(usb.TYPE_VENDOR, request, wValue=value,
                             wIndex=index, timeout=1000, data_or_wLength=data)
    else:
        handle.controlMsg(usb.TYPE_VENDOR, request, data, value=value,
                          index=index, timeout=1000)


def _get_vendor_setup(handle, request, value, index, length):
    if pyusb1:
        return handle.ctrl_transfer(usb.TYPE_VENDOR | 0x80, request,
                                    wValue=value, wIndex=index, timeout=1000,
                                    data_or_wLength=length)
    else:
        return handle.controlMsg(usb.TYPE_VENDOR | 0x80, request, length,
                                 value=value, index=index, timeout=1000)
