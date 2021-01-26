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
USB driver for the Crazyradio USB dongle.
"""
import logging
import os
import platform

import usb

__author__ = 'Bitcraze AB'
__all__ = ['Crazyradio']

logger = logging.getLogger(__name__)

# USB parameters
CRADIO_VID = 0x1915
CRADIO_PID = 0x7777

# Dongle configuration requests
# See http://wiki.bitcraze.se/projects:crazyradio:protocol for documentation
SET_RADIO_CHANNEL = 0x01
SET_RADIO_ADDRESS = 0x02
SET_DATA_RATE = 0x03
SET_RADIO_POWER = 0x04
SET_RADIO_ARD = 0x05
SET_RADIO_ARC = 0x06
ACK_ENABLE = 0x10
SET_CONT_CARRIER = 0x20
SCANN_CHANNELS = 0x21
LAUNCH_BOOTLOADER = 0xFF

try:
    import usb.core

    pyusb_backend = None
    if os.name == 'nt':
        import usb.backend.libusb0 as libusb0

        pyusb_backend = libusb0.get_backend()
    pyusb1 = True
except Exception:
    pyusb1 = False


def _find_devices(serial=None):
    """
    Returns a list of CrazyRadio devices currently connected to the computer
    """
    ret = []

    if pyusb1:
        for d in usb.core.find(idVendor=0x1915, idProduct=0x7777, find_all=1,
                               backend=pyusb_backend):
            if serial is not None and serial == d.serial_number:
                return d
            ret.append(d)
    else:
        busses = usb.busses()
        for bus in busses:
            for device in bus.devices:
                if device.idVendor == CRADIO_VID:
                    if device.idProduct == CRADIO_PID:
                        if serial == device.serial_number:
                            return device
                        ret += [device, ]

    return ret


def get_serials():
    return tuple(map(lambda d: d.serial_number, _find_devices()))


class _radio_ack:
    ack = False
    powerDet = False
    retry = 0
    data = ()


class Crazyradio:
    """ Used for communication with the Crazyradio USB dongle """
    # configuration constants
    DR_250KPS = 0
    DR_1MPS = 1
    DR_2MPS = 2

    P_M18DBM = 0
    P_M12DBM = 1
    P_M6DBM = 2
    P_0DBM = 3

    def __init__(self, device=None, devid=0, serial=None):
        """ Create object and scan for USB dongle if no device is supplied """

        self.current_channel = None
        self.current_address = None
        self.current_datarate = None

        if device is None:
            try:
                if serial is None:
                    device = _find_devices()[devid]
                else:
                    device = _find_devices(serial)
            except Exception:
                if serial is None:
                    raise Exception('Cannot find a Crazyradio Dongle')
                else:
                    raise Exception('Cannot find Crazyradio {}'.format(serial))

        self.dev = device

        if (pyusb1 is True):
            self.dev.set_configuration(1)
            self.handle = self.dev
            self.version = float('{0:x}.{1:x}'.format(
                self.dev.bcdDevice >> 8, self.dev.bcdDevice & 0x0FF))
        else:
            self.handle = self.dev.open()
            self.handle.setConfiguration(1)
            self.handle.claimInterface(0)
            self.version = float(self.dev.deviceVersion)

        if self.version < 0.3:
            raise 'This driver requires Crazyradio firmware V0.3+'

        if self.version < 0.4:
            logger.warning('You should update to Crazyradio firmware V0.4+')

        # Reset the dongle to power up settings
        if platform.system() == 'Linux':
            self.handle.reset()
        self.set_data_rate(self.DR_2MPS)
        self.set_channel(2)
        self.arc = -1
        if self.version >= 0.4:
            self.set_cont_carrier(False)
            self.set_address((0xE7,) * 5)
            self.set_power(self.P_0DBM)
            self.set_arc(3)
            self.set_ard_bytes(32)
            self.set_ack_enable(True)

    def close(self):
        if (pyusb1 is False):
            if self.handle:
                self.handle.releaseInterface()
        else:
            if self.dev:
                usb.util.dispose_resources(self.dev)

        self.handle = None
        self.dev = None

        self.current_channel = None
        self.current_address = None
        self.current_datarate = None

    # Dongle configuration
    def set_channel(self, channel):
        """ Set the radio channel to be used """
        if channel != self.current_channel:
            _send_vendor_setup(self.handle, SET_RADIO_CHANNEL, channel, 0, ())
            self.current_channel = channel

    def set_address(self, address):
        """ Set the radio address to be used"""
        if len(address) != 5:
            raise Exception('Crazyradio: the radio address shall be 5'
                            ' bytes long')
        if address != self.current_address:
            _send_vendor_setup(self.handle, SET_RADIO_ADDRESS, 0, 0, address)
            self.current_address = address

    def set_data_rate(self, datarate):
        """ Set the radio datarate to be used """
        if datarate != self.current_datarate:
            _send_vendor_setup(self.handle, SET_DATA_RATE, datarate, 0, ())
            self.current_datarate = datarate

    def set_power(self, power):
        """ Set the radio power to be used """
        _send_vendor_setup(self.handle, SET_RADIO_POWER, power, 0, ())

    def set_arc(self, arc):
        """ Set the ACK retry count for radio communication """
        _send_vendor_setup(self.handle, SET_RADIO_ARC, arc, 0, ())
        self.arc = arc

    def set_ard_time(self, us):
        """ Set the ACK retry delay for radio communication """
        # Auto Retransmit Delay:
        # 0000 - Wait 250uS
        # 0001 - Wait 500uS
        # 0010 - Wait 750uS
        # ........
        # 1111 - Wait 4000uS

        # Round down, to value representing a multiple of 250uS
        t = int((us / 250) - 1)
        if (t < 0):
            t = 0
        if (t > 0xF):
            t = 0xF
        _send_vendor_setup(self.handle, SET_RADIO_ARD, t, 0, ())

    def set_ard_bytes(self, nbytes):
        _send_vendor_setup(self.handle, SET_RADIO_ARD, 0x80 | nbytes, 0, ())

    def set_cont_carrier(self, active):
        if active:
            _send_vendor_setup(self.handle, SET_CONT_CARRIER, 1, 0, ())
        else:
            _send_vendor_setup(self.handle, SET_CONT_CARRIER, 0, 0, ())

    def set_ack_enable(self, enable):
        if enable:
            _send_vendor_setup(self.handle, ACK_ENABLE, 1, 0, ())
        else:
            _send_vendor_setup(self.handle, ACK_ENABLE, 0, 0, ())

    def _has_fw_scan(self):
        # return self.version >= 0.5
        # FIXME: Mitigation for Crazyradio firmware bug #9
        return False

    def scan_selected(self, selected, packet):
        result = ()
        for s in selected:
            self.set_channel(s['channel'])
            self.set_data_rate(s['datarate'])
            status = self.send_packet(packet)
            if status and status.ack:
                result = result + (s,)

        return result

    def scan_channels(self, start, stop, packet):
        if self._has_fw_scan():  # Fast firmware-driven scan
            self.current_channel = None
            self.current_address = None
            self.current_datarate = None

            _send_vendor_setup(self.handle, SCANN_CHANNELS, start, stop,
                               packet)
            return tuple(_get_vendor_setup(self.handle, SCANN_CHANNELS,
                                           0, 0, 64))
        else:  # Slow PC-driven scan
            result = tuple()
            for i in range(start, stop + 1):
                self.set_channel(i)
                status = self.send_packet(packet)
                if status and status.ack:
                    result = result + (i,)
            return result

    # Data transfers
    def send_packet(self, dataOut):
        """ Send a packet and receive the ack from the radio dongle
            The ack contains information about the packet transmission
            and a data payload if the ack packet contained any """
        ackIn = None
        data = None
        try:
            if (pyusb1 is False):
                self.handle.bulkWrite(1, dataOut, 1000)
                data = self.handle.bulkRead(0x81, 64, 1000)
            else:
                self.handle.write(endpoint=1, data=dataOut, timeout=1000)
                data = self.handle.read(0x81, 64, timeout=1000)
        except usb.USBError:
            pass

        if data is not None:
            ackIn = _radio_ack()
            if data[0] != 0:
                ackIn.ack = (data[0] & 0x01) != 0
                ackIn.powerDet = (data[0] & 0x02) != 0
                ackIn.retry = data[0] >> 4
                ackIn.data = data[1:]
            else:
                ackIn.retry = self.arc

        return ackIn


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
