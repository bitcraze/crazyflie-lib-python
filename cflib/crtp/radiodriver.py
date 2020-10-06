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
import array
import binascii
import collections
import logging
import queue
import re
import struct
import threading
from enum import Enum
from queue import Queue
from threading import Semaphore
from threading import Thread
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Tuple
from typing import Union

import cflib.drivers.crazyradio as crazyradio
from .crtpstack import CRTPPacket
from .exceptions import WrongUriType
from cflib.crtp.crtpdriver import CRTPDriver
from cflib.drivers.crazyradio import Crazyradio


__author__ = 'Bitcraze AB'
__all__ = ['RadioDriver']

logger = logging.getLogger(__name__)

_nr_of_retries = 100
_nr_of_arc_retries = 3

DEFAULT_ADDR_A = [0xe7, 0xe7, 0xe7, 0xe7, 0xe7]
DEFAULT_ADDR = 0xE7E7E7E7E7


class _RadioCommands(Enum):
    STOP = 0
    SEND_PACKET = 1
    SET_ARC = 2
    SCAN_SELECTED = 3
    SCAN_CHANNELS = 4


class _SharedRadioInstance():
    def __init__(self, instance_id: int,
                 cmd_queue: 'Queue[Tuple[int, _RadioCommands, Any]]',
                 rsp_queue: Queue,
                 version: float):
        self._instance_id = instance_id
        self._cmd_queue = cmd_queue
        self._rsp_queue = rsp_queue

        self._channel = 2
        self._address = [0xe7]*5
        self._datarate = crazyradio.Crazyradio.DR_2MPS

        self._opened = True

        self.version = version

    def set_channel(self, channel: int):
        self._channel = channel

    def set_address(self, address):
        self._address = address

    def set_data_rate(self, dr):
        self._datarate = dr

    def send_packet(self, data: List[int]) -> crazyradio._radio_ack:
        assert(self._opened)
        self._cmd_queue.put((self._instance_id,
                             _RadioCommands.SEND_PACKET,
                             (self._channel,
                              self._address,
                              self._datarate,
                              data)))
        ack = self._rsp_queue.get()  # type: crazyradio._radio_ack
        return ack

    def set_arc(self, arc):
        assert(self._opened)
        self._cmd_queue.put((self._instance_id,
                             _RadioCommands.SET_ARC,
                             arc))

    def scan_selected(self, selected, packet):
        assert(self._opened)
        self._cmd_queue.put((self._instance_id,
                             _RadioCommands.SCAN_SELECTED,
                             (self._datarate, self._address,
                              selected, packet)))
        return self._rsp_queue.get()

    def scan_channels(self, start: int, stop: int, packet: Iterable[int]):
        assert(self._opened)
        self._cmd_queue.put((self._instance_id,
                             _RadioCommands.SCAN_CHANNELS,
                             (self._datarate, self._address,
                              start, stop, packet)))
        return self._rsp_queue.get()

    def close(self):
        assert(self._opened)
        self._cmd_queue.put((self._instance_id, _RadioCommands.STOP, None))
        self._opened = False


class _SharedRadio(Thread):
    def __init__(self, devid: int):
        Thread.__init__(self)
        self._radio = Crazyradio(devid=devid)
        self._devid = devid
        self.version = self._radio.version

        self._cmd_queue = Queue()  # type: Queue[Tuple[int, _RadioCommands, Any]]  # noqa
        self._rsp_queues = {}  # type: Dict[int, Queue[Any]]
        self._next_instance_id = 0

        self._lock = Semaphore(1)

        self.start()

    def open_instance(self) -> _SharedRadioInstance:
        rsp_queue = Queue()
        with self._lock:
            instance_id = self._next_instance_id
            self._rsp_queues[instance_id] = rsp_queue
            self._next_instance_id += 1
        return _SharedRadioInstance(instance_id,
                                    self._cmd_queue,
                                    rsp_queue,
                                    self._radio.version)

    def run(self):
        while True:
            command = self._cmd_queue.get()

            if command[1] == _RadioCommands.STOP:
                with self._lock:
                    del self._rsp_queues[command[0]]
                    if len(self._rsp_queues) == 0:
                        self._radio.close()
                        _RadioManager.remove(self._devid)
                        return
            elif command[1] == _RadioCommands.SEND_PACKET:
                channel, address, datarate, data = command[2]
                self._radio.set_channel(channel)
                self._radio.set_address(address)
                self._radio.set_data_rate(datarate)
                ack = self._radio.send_packet(data)
                self._rsp_queues[command[0]].put(ack)
            elif command[1] == _RadioCommands.SET_ARC:
                self._radio.set_arc(command[2])
            elif command[1] == _RadioCommands.SCAN_SELECTED:
                datarate, address, selected, data = command[2]
                self._radio.set_data_rate(datarate)
                self._radio.set_address(address)
                resp = self._radio.scan_selected(selected, data)
                self._rsp_queues[command[0]].put(resp)
            elif command[1] == _RadioCommands.SCAN_CHANNELS:
                datarate, address, start, stop, packet = command[2]
                self._radio.set_data_rate(datarate)
                self._radio.set_address(address)
                resp = self._radio.scan_channels(start, stop, packet)
                self._rsp_queues[command[0]].put(resp)


class _RadioManager:
    _radios = []  # type: List[Union[_SharedRadio, None]]
    _lock = Semaphore(1)

    @staticmethod
    def open(devid: int) -> _SharedRadioInstance:
        with _RadioManager._lock:
            if len(_RadioManager._radios) <= devid:
                padding = [None] * (devid - len(_RadioManager._radios) + 1)
                _RadioManager._radios.extend(padding)

            shared_radio = _RadioManager._radios[devid]
            if not shared_radio:
                shared_radio = _SharedRadio(devid)
                _RadioManager._radios[devid] = shared_radio

        return shared_radio.open_instance()

    @staticmethod
    def remove(devid: int):
        with _RadioManager._lock:
            _RadioManager._radios[devid] = None


class RadioDriver(CRTPDriver):
    """ Crazyradio link driver """

    def __init__(self):
        """ Create the link driver """
        CRTPDriver.__init__(self)
        self._radio = None
        self.uri = ''
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

        devid, channel, datarate, address = self.parse_uri(uri)
        self.uri = uri

        if self._radio is None:
            self._radio = _RadioManager.open(devid)
            self._radio.set_channel(channel)
            self._radio.set_data_rate(datarate)
            self._radio.set_address(address)
        else:
            raise Exception('Link already open!')

        if self._radio.version >= 0.4:
            self._radio.set_arc(_nr_of_arc_retries)
        else:
            logger.warning('Radio version <0.4 will be obsoleted soon!')

        # Prepare the inter-thread communication queue
        self.in_queue = queue.Queue()
        # Limited size out queue to avoid "ReadBack" effect
        self.out_queue = queue.Queue(1)

        # Launch the comm thread
        self._thread = _RadioDriverThread(self._radio,
                                          self.in_queue,
                                          self.out_queue,
                                          link_quality_callback,
                                          link_error_callback,
                                          self)
        self._thread.start()

        self.link_error_callback = link_error_callback

    @staticmethod
    def parse_uri(uri):
        # check if the URI is a radio URI
        if not re.search('^radio://', uri):
            raise WrongUriType('Not a radio URI')

        # Open the USB dongle
        if not re.search('^radio://([0-9a-fA-F]+)((/([0-9]+))'
                         '((/(250K|1M|2M))?(/([A-F0-9]+))?)?)?$', uri):
            raise WrongUriType('Wrong radio URI format!')

        uri_data = re.search('^radio://([0-9a-fA-F]+)((/([0-9]+))'
                             '((/(250K|1M|2M))?(/([A-F0-9]+))?)?)?$', uri)

        if len(uri_data.group(1)) < 10 and uri_data.group(1).isdigit():
            devid = int(uri_data.group(1))
        else:
            try:
                devid = crazyradio.get_serials().index(
                    uri_data.group(1).upper())
            except ValueError:
                raise Exception('Cannot find radio with serial {}'.format(
                    uri_data.group(1)))

        channel = 2
        if uri_data.group(4):
            channel = int(uri_data.group(4))

        datarate = Crazyradio.DR_2MPS
        if uri_data.group(7) == '250K':
            datarate = Crazyradio.DR_250KPS
        if uri_data.group(7) == '1M':
            datarate = Crazyradio.DR_1MPS
        if uri_data.group(7) == '2M':
            datarate = Crazyradio.DR_2MPS

        address = DEFAULT_ADDR_A
        if uri_data.group(9):
            addr = str(uri_data.group(9))
            new_addr = struct.unpack('<BBBBB', binascii.unhexlify(addr))
            address = new_addr

        return devid, channel, datarate, address

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
        try:
            self.out_queue.put(pk, True, 2)
        except queue.Full:
            if self.link_error_callback:
                self.link_error_callback('RadioDriver: Could not send packet'
                                         ' to copter')

    def pause(self):
        self._thread.stop()
        self._thread = None

    def restart(self):
        if self._thread:
            return

        self._thread = _RadioDriverThread(self._radio, self.in_queue,
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
        if self._radio:
            self._radio.close()
        self._radio = None

        while not self.out_queue.empty():
            self.out_queue.get()

        # Clear callbacks
        self.link_error_callback = None
        self.link_quality_callback = None

    def _scan_radio_channels(self, radio: _SharedRadioInstance,
                             start=0, stop=125):
        """ Scan for Crazyflies between the supplied channels. """
        return list(radio.scan_channels(start, stop, (0xff,)))

    def scan_selected(self, links):
        to_scan = ()
        for link in links:
            one_to_scan = {}
            uri_data = re.search('^radio://([0-9]+)((/([0-9]+))'
                                 '(/(250K|1M|2M))?)?$',
                                 link)

            one_to_scan['channel'] = int(uri_data.group(4))

            datarate = Crazyradio.DR_2MPS
            if uri_data.group(6) == '250K':
                datarate = Crazyradio.DR_250KPS
            if uri_data.group(6) == '1M':
                datarate = Crazyradio.DR_1MPS
            if uri_data.group(6) == '2M':
                datarate = Crazyradio.DR_2MPS

            one_to_scan['datarate'] = datarate

            to_scan += (one_to_scan,)

        found = self._radio.scan_selected(to_scan, (0xFF, 0xFF, 0xFF))

        ret = ()
        for f in found:
            dr_string = ''
            if f['datarate'] == Crazyradio.DR_2MPS:
                dr_string = '2M'
            if f['datarate'] == Crazyradio.DR_250KPS:
                dr_string = '250K'
            if f['datarate'] == Crazyradio.DR_1MPS:
                dr_string = '1M'

            ret += ('radio://0/{}/{}'.format(f['channel'], dr_string),)

        return ret

    def scan_interface(self, address):
        """ Scan interface for Crazyflies """

        if self._radio is None:
            try:
                self._radio = _RadioManager.open(0)
            except Exception as e:
                print(e)
                return []

        # FIXME: implements serial number in the Crazyradio driver!
        serial = 'N/A'

        logger.info('v%s dongle with serial %s found', self._radio.version,
                    serial)
        found = []

        if address is not None:
            addr = '{:X}'.format(address)
            new_addr = struct.unpack('<BBBBB', binascii.unhexlify(addr))
            self._radio.set_address(new_addr)

        self._radio.set_arc(1)

        self._radio.set_data_rate(crazyradio.Crazyradio.DR_250KPS)

        if address is None or address == DEFAULT_ADDR:
            found += [['radio://0/{}/250K'.format(c), '']
                      for c in self._scan_radio_channels(self._radio)]
            self._radio.set_data_rate(crazyradio.Crazyradio.DR_1MPS)
            found += [['radio://0/{}/1M'.format(c), '']
                      for c in self._scan_radio_channels(self._radio)]
            self._radio.set_data_rate(crazyradio.Crazyradio.DR_2MPS)
            found += [['radio://0/{}/2M'.format(c), '']
                      for c in self._scan_radio_channels(self._radio)]
        else:
            found += [['radio://0/{}/250K/{:X}'.format(c, address), '']
                      for c in self._scan_radio_channels(self._radio)]
            self._radio.set_data_rate(crazyradio.Crazyradio.DR_1MPS)
            found += [['radio://0/{}/1M/{:X}'.format(c, address), '']
                      for c in self._scan_radio_channels(self._radio)]
            self._radio.set_data_rate(crazyradio.Crazyradio.DR_2MPS)
            found += [['radio://0/{}/2M/{:X}'.format(c, address), '']
                      for c in self._scan_radio_channels(self._radio)]

        self._radio.close()
        self._radio = None

        return found

    def get_status(self):
        try:
            radio = _RadioManager.open(0)

            ver = radio.version

            radio.close()

            return 'Crazyradio version {}'.format(ver)
        except Exception:
            return 'Crazyradio not found'

    def get_name(self):
        return 'radio'


# Transmit/receive radio thread
class _RadioDriverThread(threading.Thread):
    """
    Radio link receiver thread used to read data from the
    Crazyradio USB driver. """

    def __init__(self, radio, inQueue, outQueue,
                 link_quality_callback, link_error_callback, link):
        """ Create the object """
        threading.Thread.__init__(self)
        self._radio = radio
        self._in_queue = inQueue
        self._out_queue = outQueue
        self._sp = False
        self._link_error_callback = link_error_callback
        self._link_quality_callback = link_quality_callback
        self._retry_before_disconnect = _nr_of_retries
        self._retries = collections.deque()
        self._retry_sum = 0

        self._curr_up = 0
        self._curr_down = 1

        self._has_safelink = False
        self._link = link

    def stop(self):
        """ Stop the thread """
        self._sp = True
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
        # packet = bytearray(packet)
        packet[0] &= 0xF3
        packet[0] |= self._curr_up << 3 | self._curr_down << 2
        resp = cr.send_packet(packet)
        if resp and resp.ack and len(resp.data) and \
           (resp.data[0] & 0x04) == (self._curr_down << 2):
            self._curr_down = 1 - self._curr_down
        if resp and resp.ack:
            self._curr_up = 1 - self._curr_up

        return resp

    def run(self):
        """ Run the receiver thread """
        dataOut = array.array('B', [0xFF])
        waitTime = 0
        emptyCtr = 0
        ackStatus = None

        # Try up to 10 times to enable the safelink mode
        for _ in range(10):
            resp = self._radio.send_packet((0xff, 0x05, 0x01))
            if resp and resp.data and tuple(resp.data) == (
                    0xff, 0x05, 0x01):
                self._has_safelink = True
                self._curr_up = 0
                self._curr_down = 0
                break
        self._link.needs_resending = not self._has_safelink

        while (True):
            if (self._sp):
                break

            try:
                if self._has_safelink:
                    ackStatus = self._send_packet_safe(self._radio, dataOut)
                else:
                    ackStatus = self._radio.send_packet(dataOut)
            except Exception as e:
                import traceback

                self._link_error_callback(
                    'Error communicating with crazy radio ,it has '
                    'probably been unplugged!\nException:%s\n\n%s' % (
                        e, traceback.format_exc()))

            # Analyse the in data packet ...
            if ackStatus is None:
                logger.info('Dongle reported ACK status == None')
                continue

            if (self._link_quality_callback is not None):
                # track the mean of a sliding window of the last N packets
                retry = 10 - ackStatus.retry
                self._retries.append(retry)
                self._retry_sum += retry
                if len(self._retries) > 100:
                    self._retry_sum -= self._retries.popleft()
                link_quality = float(self._retry_sum) / len(self._retries) * 10
                self._link_quality_callback(link_quality)

            # If no copter, retry
            if ackStatus.ack is False:
                self._retry_before_disconnect = \
                    self._retry_before_disconnect - 1
                if (self._retry_before_disconnect == 0 and
                        self._link_error_callback is not None):
                    self._link_error_callback('Too many packets lost')
                continue
            self._retry_before_disconnect = _nr_of_retries

            data = ackStatus.data

            # If there is a copter in range, the packet is analysed and the
            # next packet to send is prepared
            if (len(data) > 0):
                inPacket = CRTPPacket(data[0], list(data[1:]))
                self._in_queue.put(inPacket)
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
                outPacket = self._out_queue.get(True, waitTime)
            except queue.Empty:
                outPacket = None

            dataOut = array.array('B')

            if outPacket:
                dataOut.append(outPacket.header)
                for X in outPacket.data:
                    if type(X) == int:
                        dataOut.append(X)
                    else:
                        dataOut.append(ord(X))
            else:
                dataOut.append(0xFF)


def set_retries_before_disconnect(nr_of_retries):
    global _nr_of_retries
    _nr_of_retries = nr_of_retries


def set_retries(nr_of_arc_retries):
    global _nr_of_arc_retries
    _nr_of_arc_retries = nr_of_arc_retries
