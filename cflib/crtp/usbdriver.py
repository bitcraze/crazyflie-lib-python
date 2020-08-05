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
Crazyflie USB driver.

This driver is used to communicate with the Crazyflie using the USB connection.
"""
import logging
import queue
import re
import threading

from .crtpstack import CRTPPacket
from .exceptions import WrongUriType
from cflib.crtp.crtpdriver import CRTPDriver
from cflib.drivers.cfusb import CfUsb

__author__ = 'Bitcraze AB'
__all__ = ['UsbDriver']

logger = logging.getLogger(__name__)


class UsbDriver(CRTPDriver):
    """ Crazyradio link driver """

    def __init__(self):
        """ Create the link driver """
        CRTPDriver.__init__(self)
        self.cfusb = None
        self.uri = ''
        self.link_error_callback = None
        self.link_quality_callback = None
        self.in_queue = None
        self.out_queue = None
        self._thread = None
        self.needs_resending = False

    def connect(self, uri, link_quality_callback, link_error_callback):
        """
        Connect the link driver to a specified URI of the format:
        radio://<dongle nbr>/<radio channel>/[250K,1M,2M]

        The callback for linkQuality can be called at any moment from the
        driver to report back the link quality in percentage. The
        callback from linkError will be called when a error occurs with
        an error message.
        """

        # check if the URI is a radio URI
        if not re.search('^usb://', uri):
            raise WrongUriType('Not a radio URI')

        # Open the USB dongle
        if not re.search('^usb://([0-9]+)$',
                         uri):
            raise WrongUriType('Wrong radio URI format!')

        uri_data = re.search('^usb://([0-9]+)$',
                             uri)

        self.uri = uri

        if self.cfusb is None:
            self.cfusb = CfUsb(devid=int(uri_data.group(1)))
            if self.cfusb.dev:
                self.cfusb.set_crtp_to_usb(True)
            else:
                self.cfusb = None
                raise Exception('Could not open {}'.format(self.uri))

        else:
            raise Exception('Link already open!')

        # Prepare the inter-thread communication queue
        self.in_queue = queue.Queue()
        # Limited size out queue to avoid "ReadBack" effect
        self.out_queue = queue.Queue(50)

        # Launch the comm thread
        self._thread = _UsbReceiveThread(self.cfusb, self.in_queue,
                                         link_quality_callback,
                                         link_error_callback)
        self._thread.start()

        self.link_error_callback = link_error_callback

    def receive_packet(self, time=0):
        """
        Receive a packet though the link. This call is blocking but will
        timeout and return None if a timeout is supplied.
        """
        if time == 0:
            try:
                return self.in_queue.get(False)
            except queue.Empty:
                return None
        elif time < 0:
            try:
                return self.in_queue.get(True)
            except queue.Empty:
                return None
        else:
            try:
                return self.in_queue.get(True, time)
            except queue.Empty:
                return None

    def send_packet(self, pk):
        """ Send the packet pk though the link """
        # if self.out_queue.full():
        #    self.out_queue.get()
        if (self.cfusb is None):
            return

        try:
            dataOut = (pk.header,)
            dataOut += pk.datat
            self.cfusb.send_packet(dataOut)
        except queue.Full:
            if self.link_error_callback:
                self.link_error_callback(
                    'UsbDriver: Could not send packet to Crazyflie')

    def pause(self):
        self._thread.stop()
        self._thread = None

    def restart(self):
        if self._thread:
            return

        self._thread = _UsbReceiveThread(self.cfusb, self.in_queue,
                                         self.link_quality_callback,
                                         self.link_error_callback)
        self._thread.start()

    def close(self):
        """ Close the link. """
        # Stop the comm thread
        self._thread.stop()

        # Close the USB dongle
        try:
            if self.cfusb:
                self.cfusb.set_crtp_to_usb(False)
                self.cfusb.close()
        except Exception as e:
            # If we pull out the dongle we will not make this call
            logger.info('Could not close {}'.format(e))
            pass
        self.cfusb = None

    def scan_interface(self, address):
        """ Scan interface for Crazyflies """
        if self.cfusb is None:
            try:
                self.cfusb = CfUsb()
            except Exception as e:
                logger.warn(
                    'Exception while scanning for Crazyflie USB: {}'.format(
                        str(e)))
                return []
        else:
            raise Exception('Cannot scan for links while the link is open!')

        # FIXME: implements serial number in the Crazyradio driver!
        # serial = "N/A"

        found = self.cfusb.scan()

        self.cfusb.close()
        self.cfusb = None

        return found

    def get_status(self):
        return 'No information available'

    def get_name(self):
        return 'UsbCdc'


# Transmit/receive radio thread
class _UsbReceiveThread(threading.Thread):
    """
    Radio link receiver thread used to read data from the
    Crazyradio USB driver. """

    def __init__(self, cfusb, inQueue, link_quality_callback,
                 link_error_callback):
        """ Create the object """
        threading.Thread.__init__(self)
        self.cfusb = cfusb
        self.in_queue = inQueue
        self.sp = False
        self.link_error_callback = link_error_callback
        self.link_quality_callback = link_quality_callback

    def stop(self):
        """ Stop the thread """
        self.sp = True
        try:
            self.join()
        except Exception:
            pass

    def run(self):
        """ Run the receiver thread """

        while (True):
            if (self.sp):
                break
            try:
                # Blocking until USB data available
                data = self.cfusb.receive_packet()
                if len(data) > 0:
                    pk = CRTPPacket(data[0], list(data[1:]))
                    self.in_queue.put(pk)
            except Exception as e:
                import traceback

                self.link_error_callback(
                    'Error communicating with the Crazyflie'
                    ' ,it has probably been unplugged!\n'
                    'Exception:%s\n\n%s' % (e,
                                            traceback.format_exc()))
