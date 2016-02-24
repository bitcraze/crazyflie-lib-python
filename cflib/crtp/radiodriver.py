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
Crazyradio CRTP link driver.

This driver is used to communicate with the Crazyflie using the Crazyradio
USB dongle.
"""

import collections
import logging
import sys
from cflib.crtp.crtpdriver import CRTPDriver
from .crtpstack import CRTPPacket
from .exceptions import WrongUriType
import threading
import re
import array
import binascii
import struct

from cflib.drivers.crazyradio import Crazyradio
from usb import USBError

if sys.version_info < (3,):
    import Queue as queue
else:
    import queue


__author__ = 'Bitcraze AB'
__all__ = ['RadioDriver']

logger = logging.getLogger(__name__)


class RadioDriver(CRTPDriver):
    """ Crazyradio link driver """

    def __init__(self):
        """ Create the link driver """
        CRTPDriver.__init__(self)
        self.cradio = None
        self.uri = ""
        self.link_error_callback = None
        self.link_quality_callback = None
        self.in_queue = None
        self.out_queue = None
        self._thread = None
        self.needs_resending = True

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
        if not re.search("^radio://", uri):
            raise WrongUriType("Not a radio URI")

        # Open the USB dongle
        if not re.search("^radio://([0-9]+)((/([0-9]+))"
                         "((/(250K|1M|2M))?(/([A-F0-9]+))?)?)?$", uri):
            raise WrongUriType('Wrong radio URI format!')

        uri_data = re.search("^radio://([0-9]+)((/([0-9]+))"
                             "((/(250K|1M|2M))?(/([A-F0-9]+))?)?)?$", uri)

        self.uri = uri

        channel = 2
        if uri_data.group(4):
            channel = int(uri_data.group(4))

        datarate = Crazyradio.DR_2MPS
        if uri_data.group(7) == "250K":
            datarate = Crazyradio.DR_250KPS
        if uri_data.group(7) == "1M":
            datarate = Crazyradio.DR_1MPS
        if uri_data.group(7) == "2M":
            datarate = Crazyradio.DR_2MPS

        if self.cradio is None:
            self.cradio = Crazyradio(devid=int(uri_data.group(1)))
        else:
            raise Exception("Link already open!")

        if self.cradio.version >= 0.4:
            self.cradio.set_arc(10)
        else:
            logger.warning("Radio version <0.4 will be obsoleted soon!")

        self.cradio.set_channel(channel)

        self.cradio.set_data_rate(datarate)

        if uri_data.group(9):
            addr = str(uri_data.group(9))
            new_addr = struct.unpack("<BBBBB", binascii.unhexlify(addr))
            self.cradio.set_address(new_addr)

        # Prepare the inter-thread communication queue
        self.in_queue = queue.Queue()
        # Limited size out queue to avoid "ReadBack" effect
        self.out_queue = queue.Queue(1)

        # Launch the comm thread
        self._thread = _RadioDriverThread(self.cradio, self.in_queue,
                                          self.out_queue,
                                          link_quality_callback,
                                          link_error_callback,
                                          self)
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
        if (self.cradio is None):
            return

        try:
            self.out_queue.put(pk, True, 2)
        except queue.Full:
            if self.link_error_callback:
                self.link_error_callback("RadioDriver: Could not send packet"
                                         " to copter")

    def pause(self):
        self._thread.stop()
        self._thread = None

    def restart(self):
        if self._thread:
            return

        self._thread = _RadioDriverThread(self.cradio, self.in_queue,
                                          self.out_queue,
                                          self.link_quality_callback,
                                          self.link_error_callback,
                                          self)
        self._thread.start()

    def close(self):
        """ Close the link. """
        # Stop the comm thread
        self._thread.stop()

        # Close the USB dongle
        try:
            if self.cradio:
                self.cradio.close()
        except:
            # If we pull out the dongle we will not make this call
            pass
        self.cradio = None

        while not self.out_queue.empty():
            self.out_queue.get()

        # Clear callbacks
        self.link_error_callback = None
        self.link_quality_callback = None

    def _scan_radio_channels(self, start=0, stop=125):
        """ Scan for Crazyflies between the supplied channels. """
        return list(self.cradio.scan_channels(start, stop, (0xff,)))

    def scan_selected(self, links):
        to_scan = ()
        for l in links:
            one_to_scan = {}
            uri_data = re.search("^radio://([0-9]+)((/([0-9]+))"
                                 "(/(250K|1M|2M))?)?$",
                                 l)

            one_to_scan["channel"] = int(uri_data.group(4))

            datarate = Crazyradio.DR_2MPS
            if uri_data.group(6) == "250K":
                datarate = Crazyradio.DR_250KPS
            if uri_data.group(6) == "1M":
                datarate = Crazyradio.DR_1MPS
            if uri_data.group(6) == "2M":
                datarate = Crazyradio.DR_2MPS

            one_to_scan["datarate"] = datarate

            to_scan += (one_to_scan,)

        found = self.cradio.scan_selected(to_scan, (0xFF, 0xFF, 0xFF))

        ret = ()
        for f in found:
            dr_string = ""
            if f["datarate"] == Crazyradio.DR_2MPS:
                dr_string = "2M"
            if f["datarate"] == Crazyradio.DR_250KPS:
                dr_string = "250K"
            if f["datarate"] == Crazyradio.DR_1MPS:
                dr_string = "1M"

            ret += ("radio://0/{}/{}".format(f["channel"], dr_string),)

        return ret

    def scan_interface(self, address):
        """ Scan interface for Crazyflies """
        if self.cradio is None:
            try:
                self.cradio = Crazyradio()
            except Exception:
                return []
        else:
            raise Exception("Cannot scann for links while the link is open!")

        # FIXME: implements serial number in the Crazyradio driver!
        serial = "N/A"

        logger.info("v%s dongle with serial %s found", self.cradio.version,
                    serial)
        found = []

        if address is not None:
            addr = "{:X}".format(address)
            new_addr = struct.unpack("<BBBBB", binascii.unhexlify(addr))
            self.cradio.set_address(new_addr)

        self.cradio.set_arc(1)

        self.cradio.set_data_rate(self.cradio.DR_250KPS)

        if address is None or address == 0xE7E7E7E7E7:
            found += [["radio://0/{}/250K".format(c), ""]
                      for c in self._scan_radio_channels()]
            self.cradio.set_data_rate(self.cradio.DR_1MPS)
            found += [["radio://0/{}/1M".format(c), ""]
                      for c in self._scan_radio_channels()]
            self.cradio.set_data_rate(self.cradio.DR_2MPS)
            found += [["radio://0/{}/2M".format(c), ""]
                      for c in self._scan_radio_channels()]
        else:
            found += [["radio://0/{}/250K/{:X}".format(c, address), ""]
                      for c in self._scan_radio_channels()]
            self.cradio.set_data_rate(self.cradio.DR_1MPS)
            found += [["radio://0/{}/1M/{:X}".format(c, address), ""]
                      for c in self._scan_radio_channels()]
            self.cradio.set_data_rate(self.cradio.DR_2MPS)
            found += [["radio://0/{}/2M/{:X}".format(c, address), ""]
                      for c in self._scan_radio_channels()]

        self.cradio.close()
        self.cradio = None

        return found

    def get_status(self):
        if self.cradio is None:
            try:
                self.cradio = Crazyradio()
            except USBError as e:
                return "Cannot open Crazyradio. Permission problem?" \
                       " ({})".format(str(e))
            except Exception as e:
                return str(e)

        ver = self.cradio.version
        self.cradio.close()
        self.cradio = None

        return "Crazyradio version {}".format(ver)

    def get_name(self):
        return "radio"


# Transmit/receive radio thread
class _RadioDriverThread(threading.Thread):
    """
    Radio link receiver thread used to read data from the
    Crazyradio USB driver. """

    RETRYCOUNT_BEFORE_DISCONNECT = 10

    def __init__(self, cradio, inQueue, outQueue, link_quality_callback,
                 link_error_callback, link):
        """ Create the object """
        threading.Thread.__init__(self)
        self.cradio = cradio
        self.in_queue = inQueue
        self.out_queue = outQueue
        self.sp = False
        self.link_error_callback = link_error_callback
        self.link_quality_callback = link_quality_callback
        self.retryBeforeDisconnect = self.RETRYCOUNT_BEFORE_DISCONNECT
        self.retries = collections.deque()
        self.retry_sum = 0

        self.curr_up = 0
        self.curr_down = 1

        self.has_safelink = False
        self._link = link

    def stop(self):
        """ Stop the thread """
        self.sp = True
        try:
            self.join()
        except Exception:
            pass

    def _send_packet_safe(self, cr, packet):
        """
        Adds 1bit counter to CRTP header to guarantee that no ack (downlink)
        payload are lost and no uplink packet are duplicated.
        The caller should resend packet if not acked (ie. same as with a
        direct call to crazyradio.send_packet)
        """
        packet = bytearray(packet)
        packet[0] &= 0xF3
        packet[0] |= self.curr_up << 3 | self.curr_down << 2
        resp = cr.send_packet(packet)
        if resp and resp.ack and len(resp.data) and \
           (resp.data[0] & 0x04) == (self.curr_down << 2):
            self.curr_down = 1 - self.curr_down
        if resp and resp.ack:
            self.curr_up = 1 - self.curr_up

        return resp

    def run(self):
        """ Run the receiver thread """
        dataOut = array.array('B', [0xFF])
        waitTime = 0
        emptyCtr = 0

        # Try up to 10 times to enable the safelink mode
        for _ in range(10):
            resp = self.cradio.send_packet((0xff, 0x05, 0x01))
            if resp and resp.data and tuple(resp.data) == (0xff, 0x05, 0x01):
                self.has_safelink = True
                self.curr_up = 0
                self.curr_down = 0
                break
        logging.info("Has safelink: {}".format(self.has_safelink))
        self._link.needs_resending = not self.has_safelink

        while (True):
            if (self.sp):
                break

            try:
                if self.has_safelink:
                    ackStatus = self._send_packet_safe(self.cradio, dataOut)
                else:
                    ackStatus = self.cradio.send_packet(dataOut)
            except Exception as e:
                import traceback

                self.link_error_callback(
                    "Error communicating with crazy radio ,it has probably "
                    "been unplugged!\nException:%s\n\n%s" % (
                        e, traceback.format_exc()))

            # Analise the in data packet ...
            if ackStatus is None:
                if (self.link_error_callback is not None):
                    self.link_error_callback("Dongle communication error"
                                             " (ackStatus==None)")
                continue

            if (self.link_quality_callback is not None):
                # track the mean of a sliding window of the last N packets
                retry = 10 - ackStatus.retry
                self.retries.append(retry)
                self.retry_sum += retry
                if len(self.retries) > 100:
                    self.retry_sum -= self.retries.popleft()
                link_quality = float(self.retry_sum) / len(self.retries) * 10
                self.link_quality_callback(link_quality)

            # If no copter, retry
            if ackStatus.ack is False:
                self.retryBeforeDisconnect = self.retryBeforeDisconnect - 1
                if (self.retryBeforeDisconnect == 0 and
                        self.link_error_callback is not None):
                    self.link_error_callback("Too many packets lost")
                continue
            self.retryBeforeDisconnect = self.RETRYCOUNT_BEFORE_DISCONNECT

            data = ackStatus.data

            # If there is a copter in range, the packet is analysed and the
            # next packet to send is prepared
            if (len(data) > 0):
                inPacket = CRTPPacket(data[0], list(data[1:]))
                # print "<- " + inPacket.__str__()
                self.in_queue.put(inPacket)
                waitTime = 0
                emptyCtr = 0
            else:
                emptyCtr += 1
                if (emptyCtr > 10):
                    emptyCtr = 10
                    # Relaxation time if the last 10 packet where empty
                    waitTime = 0.01
                else:
                    waitTime = 0

            # get the next packet to send of relaxation (wait 10ms)
            outPacket = None
            try:
                outPacket = self.out_queue.get(True, waitTime)
            except queue.Empty:
                outPacket = None

            dataOut = array.array('B')

            if outPacket:
                # print "-> " + outPacket.__str__()
                dataOut.append(outPacket.header)
                for X in outPacket.data:
                    if type(X) == int:
                        dataOut.append(X)
                    else:
                        dataOut.append(ord(X))
            else:
                dataOut.append(0xFF)
