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
An early serial link driver. This could still be used (after some fixing) to
run high-speed CRTP with the Crazyflie. The UART can be run at 2Mbit.
"""
import logging
import re
import sys
import threading

from .crtpstack import CRTPPacket
from .exceptions import WrongUriType
from cflib.crtp.crtpdriver import CRTPDriver

if sys.version_info < (3,):
    import Queue as queue
else:
    import queue

found_serial = True
try:
    import serial
except ImportError:
    found_serial = False

DEBUG_PACKET_OUTPUT = True
if DEBUG_PACKET_OUTPUT:
    import pandas as pd
    import numpy as np
    from os.path import expanduser
    from enum import Enum

    LOG_SIZE = 50000

    class Direction(Enum):
        EMPTY = 0
        IN = 1
        OUT = 2

__author__ = 'Bitcraze AB'
__all__ = ['SerialDriver']

logger = logging.getLogger(__name__)

MTU = 32
START_BYTE1 = 0xbc
START_BYTE2 = 0xcf
SYSLINK_RADIO_RAW = 0x00


def compute_cksum(list):
    cksum0, cksum1 = 0, 0
    for i in range(len(list)):
        cksum0 = (cksum0 + list[i]) & 0xff
        cksum1 = (cksum1 + cksum0) & 0xff
    return bytearray([cksum0, cksum1])


class SerialDriver(CRTPDriver):

    def __init__(self):
        CRTPDriver.__init__(self)
        self.ser = None
        self.uri = ''
        self.link_error_callback = None
        self.in_queue = None
        self.out_queue = None
        self._receive_thread = None
        self._send_thread = None
        logger.info('Initialized serial driver.')

    def connect(self, uri, linkQualityCallback, linkErrorCallback):
        # check if the URI is a serial URI
        if not re.search('^serial://', uri):
            raise WrongUriType('Not a serial URI')

        # Check if it is a valid serial URI
        uriRe = re.search('^serial://pi$', uri)
        if not uriRe:
            raise Exception('Invalid serial URI')

        if not found_serial:
            raise Exception('PySerial package is missing')

        self.uri = uri

        self.link_error_callback = linkErrorCallback

        # Prepare the inter-thread communication queue
        self.in_queue = queue.Queue()
        self.out_queue = queue.Queue(1)

        self.ser = serial.Serial('/dev/ttyAMA0', 512000, timeout=1)

        # Launch the comm thread
        self._receive_thread = _SerialReceiveThread(
            self.ser, self.in_queue, linkQualityCallback, linkErrorCallback)
        self._receive_thread.start()
        self._send_thread = _SerialSendThread(
            self.ser, self.out_queue, linkQualityCallback, linkErrorCallback)

        self._send_thread.start()

    def send_packet(self, pk):
        try:
            self.out_queue.put(pk, True, 2)
        except queue.Full:
            if self.link_error_callback:
                self.link_error_callback(
                    'RadioDriver: Could not send packet to copter')

    def receive_packet(self, wait=0):
        try:
            if wait == 0:
                pk = self.in_queue.get(False)
            elif wait < 0:
                pk = self.in_queue.get(True)
            else:
                pk = self.in_queue.get(True, wait)
        except queue.Empty:
            return None
        return pk

    def get_status(self):
        return 'No information available'

    def get_name(self):
        return 'serial'

    def scan_interface(self, address):
        if found_serial:
            return [['serial://pi', ''], ]
        else:
            return []

    def close(self):
        self._receive_thread.stop()
        self._send_thread.stop()

        if DEBUG_PACKET_OUTPUT:
            receive_log = self._receive_thread.get_log()
            send_log = self._send_thread.get_log()
            full_log = pd.DataFrame(np.append(receive_log, send_log, axis=0),
                                    columns=['timestamp', 'direction', 'port',
                                             'channel', 'data'])
            full_log = full_log.sort_values(
                by=['timestamp']).reset_index(drop=True)
            full_log.to_csv(
                expanduser('~/') + 'serial_log_' +
                str(pd.Timestamp.now().round('s')).replace(' ', '_') + '.csv')

        try:
            self._receive_thread.join()
            self._send_thread.join()
        except Exception:
            pass
        self.ser.close()


class _SerialReceiveThread(threading.Thread):

    def __init__(self, ser, inQueue, link_quality_callback,
                 link_error_callback):
        """ Create the object """
        threading.Thread.__init__(self)
        self.ser = ser
        self.in_queue = inQueue
        self._stop = False
        self.link_error_callback = link_error_callback

        if DEBUG_PACKET_OUTPUT:
            empty_row = np.array([pd.NaT, Direction.EMPTY, np.nan, np.nan,
                                  bytearray(31)])
            self.packet_log = np.array([empty_row]*LOG_SIZE)
            self.log_index = 0

    def stop(self):
        """ Stop the thread """
        self._stop = True

    def get_log(self):
        if DEBUG_PACKET_OUTPUT:
            return self.packet_log[:self.log_index]
        else:
            return None

    def run(self):
        """ Run the receiver thread """
        READ_END = bytes([START_BYTE1, START_BYTE2])
        received = bytearray(MTU + 4)
        received_header = memoryview(received)[0:2]
        while not self._stop:
            try:
                r = self.ser.read_until(READ_END)[-2:]
                if len(r) != 2:
                    continue

                if DEBUG_PACKET_OUTPUT:
                    timestamp = pd.Timestamp.now()

                if r[0] != START_BYTE1 or r[1] != START_BYTE2:
                    continue

                r = self.ser.readinto(received_header)
                if r != 2:
                    continue

                if not (0 < received_header[1] <= MTU):
                    continue

                expected = received_header[1] + 2

                received_data_chk = memoryview(received)[2:2+expected]
                r = self.ser.readinto(received_data_chk)
                if r != expected:
                    continue

                # NOTE: end is (expected - 2) as the lenght of the data +2 for
                # the header bytes
                cksum = compute_cksum(memoryview(received)[:expected])
                if cksum[0] != received_data_chk[-2] or \
                        cksum[1] != received_data_chk[-1]:
                    continue

                pk = CRTPPacket(received[2], received[3:expected])
                self.in_queue.put(pk)

                if DEBUG_PACKET_OUTPUT and self.log_index < LOG_SIZE:
                    row = [timestamp, Direction.IN, pk.port, pk.channel,
                           pk.data]
                    self.packet_log[self.log_index] = row
                    self.log_index += 1

            except Exception as e:
                import traceback
                if self.link_error_callback:
                    self.link_error_callback(
                        'Error communicating with the Crazyflie!\n'
                        'Exception:%s\n\n%s' % (e, traceback.format_exc()))


class _SerialSendThread(threading.Thread):

    def __init__(self, ser, outQueue, link_quality_callback,
                 link_error_callback):
        """ Create the object """
        threading.Thread.__init__(self)
        self.ser = ser
        self.out_queue = outQueue
        self._stop = False
        self.link_error_callback = link_error_callback

        if DEBUG_PACKET_OUTPUT:
            empty_row = np.array([pd.NaT, Direction.EMPTY, np.nan, np.nan,
                                  bytearray(31)])
            self.packet_log = np.array([empty_row] * LOG_SIZE)
            self.log_index = 0

    def stop(self):
        """ Stop the thread """
        self._stop = True

    def get_log(self):
        if DEBUG_PACKET_OUTPUT:
            return self.packet_log[:self.log_index]
        else:
            return None

    def run(self):
        """ Run the sender thread """
        out_data = bytearray(MTU + 6)
        out_data[0:3] = bytearray([START_BYTE1, START_BYTE2,
                                   SYSLINK_RADIO_RAW])

        empty_packet = CRTPPacket(header=0xFF)
        empty_packet_data_length = 0
        empty_packet_data = bytearray(7)
        empty_packet_data[0:5] = bytearray(
            [START_BYTE1, START_BYTE2, SYSLINK_RADIO_RAW, 0x01,
             empty_packet.header])

        empty_packet_data[5:7] = compute_cksum(empty_packet_data[2:5])

        while not self._stop:
            try:
                pk = self.out_queue.get(True, timeout=0.0003)
                data = pk.data
                len_data = len(data)
                end_of_payload = 5 + len_data

                out_data[3] = len_data + 1
                out_data[4] = pk.header
                out_data[5:end_of_payload] = data
                out_data[end_of_payload:end_of_payload +
                         2] = compute_cksum(out_data[2:end_of_payload])

                if DEBUG_PACKET_OUTPUT:
                    timestamp = pd.Timestamp.now()

                written = self.ser.write(out_data[0:end_of_payload + 2])

            except queue.Empty:
                pk = empty_packet
                len_data = empty_packet_data_length

                if DEBUG_PACKET_OUTPUT:
                    timestamp = pd.Timestamp.now()
                written = self.ser.write(empty_packet_data)

            if written != len_data + 7:
                if self.link_error_callback:
                    self.link_error_callback(
                        'SerialDriver: Could only send {:d}B bytes of {:d}B '
                        'packet to Crazyflie'.format(
                            written, len_data + 7)
                    )
            else:
                if DEBUG_PACKET_OUTPUT and self.log_index < LOG_SIZE:
                    row = [timestamp, Direction.OUT, pk.port, pk.channel,
                           pk.data]
                    self.packet_log[self.log_index] = row
                    self.log_index += 1
