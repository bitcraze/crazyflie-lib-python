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
Fake link driver used to debug the UI without using the Crazyflie.

The operation of this driver can be controlled in two ways, either by
connecting to different URIs or by sending messages to the DebugDriver port
though CRTP once connected.

For normal connections a console thread is also started that will send
generated console output via CRTP.
"""
import errno
import logging
import random
import re
import string
import struct
import sys
import time
from datetime import datetime
from threading import Thread

from .crtpdriver import CRTPDriver
from .crtpstack import CRTPPacket
from .crtpstack import CRTPPort
from .exceptions import WrongUriType
from cflib.crazyflie.log import LogTocElement
from cflib.crazyflie.param import ParamTocElement
if sys.version_info < (3,):
    import Queue as queue
else:
    import queue

__author__ = 'Bitcraze AB'
__all__ = ['DebugDriver']

logger = logging.getLogger(__name__)

# This setup is used to debug raw memory logging
memlogging = {0x01: {'min': 0, 'max': 255, 'mod': 1, 'vartype': 1},
              0x02: {'min': 0, 'max': 65000, 'mod': 100, 'vartype': 2},
              0x03: {'min': 0, 'max': 100000, 'mod': 1000, 'vartype': 3},
              0x04: {'min': -100, 'max': 100, 'mod': 1, 'vartype': 4},
              0x05: {'min': -10000, 'max': 10000, 'mod': 2000, 'vartype': 5},
              0x06: {'min': -50000, 'max': 50000, 'mod': 1000, 'vartype': 6},
              0x07: {'min': 0, 'max': 255, 'mod': 1, 'vartype': 1}}


class FakeMemory:
    TYPE_I2C = 0
    TYPE_1W = 1

    def __init__(self, type, size, addr, data=None):
        self.type = type
        self.size = size
        self.addr = addr
        self.data = [0] * size
        if data:
            for i in range(len(data)):
                self.data[i] = data[i]

    def erase(self):
        self.data = [0] * self.size


class DebugDriver(CRTPDriver):
    """ Debug driver used for debugging UI/communication without using a
    Crazyflie"""

    def __init__(self):
        self.fakeLoggingThreads = []
        self._fake_mems = []
        self.needs_resending = False
        # Fill up the fake logging TOC with values and data
        self.fakeLogToc = []
        self.fakeLogToc.append({'varid': 0, 'vartype': 5, 'vargroup': 'imu',
                                'varname': 'gyro_x', 'min': -10000,
                                'max': 10000, 'mod': 1000})
        self.fakeLogToc.append({'varid': 1, 'vartype': 5, 'vargroup': 'imu',
                                'varname': 'gyro_y', 'min': -10000,
                                'max': 10000, 'mod': 150})
        self.fakeLogToc.append({'varid': 2, 'vartype': 5, 'vargroup': 'imu',
                                'varname': 'gyro_z', 'min': -10000,
                                'max': 10000, 'mod': 200})
        self.fakeLogToc.append({'varid': 3, 'vartype': 5, 'vargroup': 'imu',
                                'varname': 'acc_x', 'min': -1000,
                                'max': 1000, 'mod': 15})
        self.fakeLogToc.append({'varid': 4, 'vartype': 5, 'vargroup': 'imu',
                                'varname': 'acc_y', 'min': -1000,
                                'max': 1000, 'mod': 10})
        self.fakeLogToc.append({'varid': 5, 'vartype': 5, 'vargroup': 'imu',
                                'varname': 'acc_z', 'min': -1000,
                                'max': 1000, 'mod': 20})
        self.fakeLogToc.append({'varid': 6, 'vartype': 7,
                                'vargroup': 'stabilizer', 'varname': 'roll',
                                'min': -90, 'max': 90, 'mod': 2})
        self.fakeLogToc.append({'varid': 7, 'vartype': 7,
                                'vargroup': 'stabilizer', 'varname': 'pitch',
                                'min': -90, 'max': 90, 'mod': 1.5})
        self.fakeLogToc.append({'varid': 8, 'vartype': 7,
                                'vargroup': 'stabilizer', 'varname': 'yaw',
                                'min': -90, 'max': 90, 'mod': 2.5})
        self.fakeLogToc.append({'varid': 9, 'vartype': 7, 'vargroup': 'pm',
                                'varname': 'vbat', 'min': 3.0,
                                'max': 4.2, 'mod': 0.1})
        self.fakeLogToc.append({'varid': 10, 'vartype': 6, 'vargroup': 'motor',
                                'varname': 'm1', 'min': 0, 'max': 65000,
                                'mod': 1000})
        self.fakeLogToc.append({'varid': 11, 'vartype': 6, 'vargroup': 'motor',
                                'varname': 'm2', 'min': 0, 'max': 65000,
                                'mod': 1000})
        self.fakeLogToc.append({'varid': 12, 'vartype': 6, 'vargroup': 'motor',
                                'varname': 'm3', 'min': 0, 'max': 65000,
                                'mod': 1000})
        self.fakeLogToc.append({'varid': 13, 'vartype': 6, 'vargroup': 'motor',
                                'varname': 'm4', 'min': 0, 'max': 65000,
                                'mod': 1000})
        self.fakeLogToc.append({'varid': 14, 'vartype': 2,
                                'vargroup': 'stabilizer', 'varname': 'thrust',
                                'min': 0, 'max': 65000, 'mod': 1000})
        self.fakeLogToc.append({'varid': 15, 'vartype': 7,
                                'vargroup': 'baro', 'varname': 'asl',
                                'min': 540, 'max': 545, 'mod': 0.5})
        self.fakeLogToc.append({'varid': 16, 'vartype': 7,
                                'vargroup': 'baro', 'varname': 'aslRaw',
                                'min': 540, 'max': 545, 'mod': 1.0})
        self.fakeLogToc.append({'varid': 17, 'vartype': 7,
                                'vargroup': 'posEstimatorAlt',
                                'varname': 'estimatedZ',
                                'min': 540, 'max': 545, 'mod': 0.5})
        self.fakeLogToc.append({'varid': 18, 'vartype': 7,
                                'vargroup': 'baro', 'varname': 'temp',
                                'min': 26, 'max': 38, 'mod': 1.0})
        self.fakeLogToc.append({'varid': 19, 'vartype': 7,
                                'vargroup': 'posCtlAlt',
                                'varname': 'targetZ',
                                'min': 542, 'max': 543, 'mod': 0.1})
        self.fakeLogToc.append({'varid': 20, 'vartype': 6,
                                'vargroup': 'gps', 'varname': 'lat',
                                'min': 556112190, 'max': 556112790,
                                'mod': 10})
        self.fakeLogToc.append({'varid': 21, 'vartype': 6,
                                'vargroup': 'gps', 'varname': 'lon',
                                'min': 129945110, 'max': 129945710,
                                'mod': 10})
        self.fakeLogToc.append({'varid': 22, 'vartype': 6,
                                'vargroup': 'gps', 'varname': 'hMSL',
                                'min': 0, 'max': 100000,
                                'mod': 1000})
        self.fakeLogToc.append({'varid': 23, 'vartype': 6,
                                'vargroup': 'gps', 'varname': 'heading',
                                'min': -10000000, 'max': 10000000,
                                'mod': 100000})
        self.fakeLogToc.append({'varid': 24, 'vartype': 6,
                                'vargroup': 'gps', 'varname': 'gSpeed',
                                'min': 0, 'max': 1000,
                                'mod': 100})
        self.fakeLogToc.append({'varid': 25, 'vartype': 3,
                                'vargroup': 'gps', 'varname': 'hAcc',
                                'min': 0, 'max': 5000,
                                'mod': 100})
        self.fakeLogToc.append({'varid': 26, 'vartype': 1,
                                'vargroup': 'gps', 'varname': 'fixType',
                                'min': 0, 'max': 5,
                                'mod': 1})

        # Fill up the fake logging TOC with values and data
        self.fakeParamToc = []
        self.fakeParamToc.append({'varid': 0, 'vartype': 0x08,
                                  'vargroup': 'blah', 'varname': 'p',
                                  'writable': True, 'value': 100})
        self.fakeParamToc.append({'varid': 1, 'vartype': 0x0A,
                                  'vargroup': 'info', 'varname': 'cid',
                                  'writable': False, 'value': 1234})
        self.fakeParamToc.append({'varid': 2, 'vartype': 0x06,
                                  'vargroup': 'rpid', 'varname': 'prp',
                                  'writable': True, 'value': 1.5})
        self.fakeParamToc.append({'varid': 3, 'vartype': 0x06,
                                  'vargroup': 'rpid', 'varname': 'pyaw',
                                  'writable': True, 'value': 2.5})
        self.fakeParamToc.append({'varid': 4, 'vartype': 0x06,
                                  'vargroup': 'rpid', 'varname': 'irp',
                                  'writable': True, 'value': 3.5})
        self.fakeParamToc.append({'varid': 5, 'vartype': 0x06,
                                  'vargroup': 'rpid', 'varname': 'iyaw',
                                  'writable': True, 'value': 4.5})
        self.fakeParamToc.append({'varid': 6, 'vartype': 0x06,
                                  'vargroup': 'pid_attitude',
                                  'varname': 'pitch_kd', 'writable': True,
                                  'value': 5.5})
        self.fakeParamToc.append({'varid': 7, 'vartype': 0x06,
                                  'vargroup': 'rpid', 'varname': 'dyaw',
                                  'writable': True, 'value': 6.5})
        self.fakeParamToc.append({'varid': 8, 'vartype': 0x06,
                                  'vargroup': 'apid', 'varname': 'prp',
                                  'writable': True, 'value': 7.5})
        self.fakeParamToc.append({'varid': 9, 'vartype': 0x06,
                                  'vargroup': 'apid', 'varname': 'pyaw',
                                  'writable': True, 'value': 8.5})
        self.fakeParamToc.append({'varid': 10, 'vartype': 0x06,
                                  'vargroup': 'apid', 'varname': 'irp',
                                  'writable': True, 'value': 9.5})
        self.fakeParamToc.append({'varid': 11, 'vartype': 0x06,
                                  'vargroup': 'apid', 'varname': 'iyaw',
                                  'writable': True, 'value': 10.5})
        self.fakeParamToc.append({'varid': 12, 'vartype': 0x06,
                                  'vargroup': 'apid', 'varname': 'drp',
                                  'writable': True, 'value': 11.5})
        self.fakeParamToc.append({'varid': 13, 'vartype': 0x06,
                                  'vargroup': 'apid', 'varname': 'dyaw',
                                  'writable': True, 'value': 12.5})
        self.fakeParamToc.append({'varid': 14, 'vartype': 0x08,
                                  'vargroup': 'flightctrl',
                                  'varname': 'xmode', 'writable': True,
                                  'value': 1})
        self.fakeParamToc.append({'varid': 15, 'vartype': 0x08,
                                  'vargroup': 'flightctrl',
                                  'varname': 'ratepid', 'writable': True,
                                  'value': 1})
        self.fakeParamToc.append({'varid': 16, 'vartype': 0x08,
                                  'vargroup': 'imu_sensors',
                                  'varname': 'HMC5883L', 'writable': False,
                                  'value': 1})
        self.fakeParamToc.append({'varid': 17, 'vartype': 0x08,
                                  'vargroup': 'imu_sensors',
                                  'varname': 'MS5611', 'writable': False,
                                  'value': 1})
        self.fakeParamToc.append({'varid': 18, 'vartype': 0x0A,
                                  'vargroup': 'firmware',
                                  'varname': 'revision0', 'writable': False,
                                  'value': 0xdeb})
        self.fakeParamToc.append({'varid': 19, 'vartype': 0x09,
                                  'vargroup': 'firmware',
                                  'varname': 'revision1', 'writable': False,
                                  'value': 0x99})
        self.fakeParamToc.append({'varid': 20, 'vartype': 0x08,
                                  'vargroup': 'firmware',
                                  'varname': 'modified', 'writable': False,
                                  'value': 1})
        self.fakeParamToc.append({'varid': 21, 'vartype': 0x08,
                                  'vargroup': 'imu_tests',
                                  'varname': 'MPU6050', 'writable': False,
                                  'value': 1})
        self.fakeParamToc.append({'varid': 22, 'vartype': 0x08,
                                  'vargroup': 'imu_tests',
                                  'varname': 'HMC5883L', 'writable': False,
                                  'value': 1})
        self.fakeParamToc.append({'varid': 23, 'vartype': 0x08,
                                  'vargroup': 'imu_tests',
                                  'varname': 'MS5611', 'writable': False,
                                  'value': 1})

        self.fakeflash = {}
        self._random_answer_delay = True
        self.queue = queue.Queue()
        self._packet_handler = _PacketHandlingThread(self.queue,
                                                     self.fakeLogToc,
                                                     self.fakeParamToc,
                                                     self._fake_mems)
        self._packet_handler.start()

    def scan_interface(self, address):
        return [['debug://0/0', 'Normal connection'],
                ['debug://0/1', 'Fail to connect'],
                ['debug://0/2', 'Incomplete log TOC download'],
                ['debug://0/3', 'Insert random delays on replies'],
                ['debug://0/4',
                 'Insert random delays on replies and random TOC CRCs'],
                ['debug://0/5', 'Normal but random TOC CRCs'],
                ['debug://0/6', 'Normal but empty I2C and OW mems']]

    def get_status(self):
        return 'Ok'

    def get_name(self):
        return 'debug'

    def connect(self, uri, linkQualityCallback, linkErrorCallback):

        if not re.search('^debug://', uri):
            raise WrongUriType('Not a debug URI')

        self._packet_handler.linkErrorCallback = linkErrorCallback
        self._packet_handler.linkQualityCallback = linkQualityCallback

        # Debug-options for this driver that
        # is set by using different connection URIs
        self._packet_handler.inhibitAnswers = False
        self._packet_handler.doIncompleteLogTOC = False
        self._packet_handler.bootloader = False
        self._packet_handler._random_answer_delay = False
        self._packet_handler._random_toc_crcs = False

        if (re.search('^debug://.*/1\Z', uri)):
            self._packet_handler.inhibitAnswers = True
        if (re.search('^debug://.*/110\Z', uri)):
            self._packet_handler.bootloader = True
        if (re.search('^debug://.*/2\Z', uri)):
            self._packet_handler.doIncompleteLogTOC = True
        if (re.search('^debug://.*/3\Z', uri)):
            self._packet_handler._random_answer_delay = True
        if (re.search('^debug://.*/4\Z', uri)):
            self._packet_handler._random_answer_delay = True
            self._packet_handler._random_toc_crcs = True
        if (re.search('^debug://.*/5\Z', uri)):
            self._packet_handler._random_toc_crcs = True

        if len(self._fake_mems) == 0:
            # Add empty EEPROM
            self._fake_mems.append(FakeMemory(type=0, size=100, addr=0))
            # Add EEPROM with settings
            self._fake_mems.append(
                FakeMemory(type=0, size=100, addr=0,
                           data=[48, 120, 66, 67, 1, 8, 0, 0, 0, 0,
                                 0, 0, 0, 0, 0, 231, 8, 231, 231, 231, 218]))
            # Add 1-wire memory with settings for LED-ring
            self._fake_mems.append(
                FakeMemory(type=1, size=112, addr=0x1234567890ABCDEF,
                           data=[0xeb, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01,
                                 0x44, 0x00, 0x0e,
                                 0x01, 0x09, 0x62, 0x63, 0x4c, 0x65, 0x64,
                                 0x52, 0x69, 0x6e,
                                 0x67, 0x02, 0x01, 0x62, 0x55]))
            # Add 1-wire memory with settings for LED-ring but bad CRC
            self._fake_mems.append(
                FakeMemory(type=1, size=112, addr=0x1234567890ABCDEF,
                           data=[0xeb, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01,
                                 0x44, 0x00, 0x0e,
                                 0x01, 0x09, 0x62, 0x63, 0x4c, 0x65, 0x64,
                                 0x52, 0x69, 0x6e,
                                 0x67, 0x02, 0x01, 0x62, 0x56]))
            # Add empty 1-wire memory
            self._fake_mems.append(
                FakeMemory(type=1, size=112, addr=0x1234567890ABCDEE,
                           data=[0x00 for a in range(112)]))

        if (re.search('^debug://.*/6\Z', uri)):
            logger.info('------------->Erasing memories on connect')
            for m in self._fake_mems:
                m.erase()

        self.fakeConsoleThread = None

        if (not self._packet_handler.inhibitAnswers and
                not self._packet_handler.bootloader):
            self.fakeConsoleThread = FakeConsoleThread(self.queue)
            self.fakeConsoleThread.start()

        if (self._packet_handler.linkQualityCallback is not None):
            self._packet_handler.linkQualityCallback(0)

    def receive_packet(self, time=0):
        if time == 0:
            try:
                return self.queue.get(False)
            except queue.Empty:
                return None
        elif time < 0:
            try:
                return self.queue.get(True)
            except queue.Empty:
                return None
        else:
            try:
                return self.queue.get(True, time)
            except queue.Empty:
                return None

    def send_packet(self, pk):
        self._packet_handler.handle_packet(pk)

    def close(self):
        logger.info('Closing debugdriver')
        for f in self._packet_handler.fakeLoggingThreads:
            f.stop()
        if self.fakeConsoleThread:
            self.fakeConsoleThread.stop()


class _PacketHandlingThread(Thread):
    """Thread for handling packets asynchronously"""

    def __init__(self, out_queue, fake_log_toc, fake_param_toc, fake_mems):
        Thread.__init__(self)
        self.setDaemon(True)
        self.queue = out_queue
        self.fakeLogToc = fake_log_toc
        self.fakeParamToc = fake_param_toc
        self._fake_mems = fake_mems
        self._in_queue = queue.Queue()

        self.inhibitAnswers = False
        self.doIncompleteLogTOC = False
        self.bootloader = False
        self._random_answer_delay = False
        self._random_toc_crcs = False

        self.linkErrorCallback = None
        self.linkQualityCallback = None
        random.seed(None)
        self.fakeLoggingThreads = []

        self._added_blocks = []

        self.nowAnswerCounter = 4

    def handle_packet(self, pk):
        self._in_queue.put(pk)

    def run(self):
        while (True):
            pk = self._in_queue.get(True)
            if (self.inhibitAnswers):
                self.nowAnswerCounter = self.nowAnswerCounter - 1
                logger.debug(
                    'Not answering with any data, will send link errori'
                    ' in %d retries', self.nowAnswerCounter)
                if (self.nowAnswerCounter == 0):
                    self.linkErrorCallback('Nothing is answering, and it'
                                           " shouldn't")
            else:
                if (pk.port == 0xFF):
                    self._handle_bootloader(pk)
                elif (pk.port == CRTPPort.DEBUGDRIVER):
                    self._handle_debugmessage(pk)
                elif (pk.port == CRTPPort.COMMANDER):
                    pass
                elif (pk.port == CRTPPort.LOGGING):
                    self._handle_logging(pk)
                elif (pk.port == CRTPPort.PARAM):
                    self.handleParam(pk)
                elif (pk.port == CRTPPort.MEM):
                    self._handle_mem_access(pk)
                else:
                    logger.warning(
                        'Not handling incoming packets on port [%d]',
                        pk.port)

    def _handle_mem_access(self, pk):
        chan = pk.channel
        cmd = pk.data[0]
        payload = pk.data[1:]

        if chan == 0:  # Info channel
            p_out = CRTPPacket()
            p_out.set_header(CRTPPort.MEM, 0)
            if cmd == 1:  # Request number of memories
                p_out.data = (1, len(self._fake_mems))
            if cmd == 2:
                id = payload[0]
                logger.info('Getting mem {}'.format(id))
                m = self._fake_mems[id]
                p_out.data = struct.pack(
                    '<BBBIQ', 2, id, m.type, m.size, m.addr)
            self._send_packet(p_out)

        if chan == 1:  # Read channel
            id = cmd
            addr = struct.unpack('I', payload[0:4])[0]
            length = payload[4]
            status = 0
            logger.info('MEM: Read {}bytes at 0x{:X} from memory {}'.format(
                length, addr, id))
            m = self._fake_mems[id]
            p_out = CRTPPacket()
            p_out.set_header(CRTPPort.MEM, 1)
            p_out.data = struct.pack('<BIB', id, addr, status)
            p_out.data += struct.pack('B' * length,
                                      *m.data[addr:addr + length])
            self._send_packet(p_out)

        if chan == 2:  # Write channel
            id = cmd
            addr = struct.unpack('I', payload[0:4])[0]
            data = payload[4:]
            logger.info('MEM: Write {}bytes at 0x{:X} to memory {}'.format(
                len(data), addr, id))
            m = self._fake_mems[id]

            for i in range(len(data)):
                m.data[addr + i] = data[i]

            status = 0

            p_out = CRTPPacket()
            p_out.set_header(CRTPPort.MEM, 2)
            p_out.data = struct.pack('<BIB', id, addr, status)
            self._send_packet(p_out)

    def _handle_bootloader(self, pk):
        cmd = pk.data[1]
        if (cmd == 0x10):  # Request info about copter
            p = CRTPPacket()
            p.set_header(0xFF, 0xFF)
            pageSize = 1024
            buffPages = 10
            flashPages = 100
            flashStart = 1
            p.data = struct.pack('<BBHHHH', 0xFF, 0x10, pageSize, buffPages,
                                 flashPages, flashStart)
            p.data += struct.pack('B' * 12, 0xA0A1A2A3A4A5)
            self._send_packet(p)
            logging.info('Bootloader: Sending info back info')
        elif (cmd == 0x14):  # Upload buffer
            [page, addr] = struct.unpack('<HH', p.data[0:4])
        elif (cmd == 0x18):  # Flash page
            p = CRTPPacket()
            p.set_header(0xFF, 0xFF)
            p.data = struct.pack('<BBH', 0xFF, 0x18, 1)
            self._send_packet(p)
        elif (cmd == 0xFF):  # Reset to firmware
            logger.info('Bootloader: Got reset command')
        else:
            logger.warning('Bootloader: Unknown command 0x%02X', cmd)

    def _handle_debugmessage(self, pk):
        if (pk.channel == 0):
            cmd = struct.unpack('B', pk.data[0])[0]
            if (cmd == 0):  # Fake link quality
                newLinkQuality = struct.unpack('B', pk.data[1])[0]
                self.linkQualityCallback(newLinkQuality)
            elif (cmd == 1):
                self.linkErrorCallback('DebugDriver was forced to disconnect!')
            else:
                logger.warning('Debug port: Not handling cmd=%d on channel 0',
                               cmd)
        else:
            logger.warning('Debug port: Not handling channel=%d',
                           pk.channel)

    def _handle_toc_access(self, pk):
        chan = pk.channel
        cmd = pk.data[0]
        logger.info('TOC access on port %d', pk.port)
        if (chan == 0):  # TOC Access
            cmd = pk.data[0]
            if (cmd == 0):  # Reqest variable info
                p = CRTPPacket()
                p.set_header(pk.port, 0)
                varIndex = 0
                if (len(pk.data) > 1):
                    varIndex = pk.data[1]
                    logger.debug('TOC[%d]: Requesting ID=%d', pk.port,
                                 varIndex)
                else:
                    logger.debug('TOC[%d]: Requesting first index..surprise,'
                                 ' it 0 !', pk.port)

                if (pk.port == CRTPPort.LOGGING):
                    entry = self.fakeLogToc[varIndex]
                if (pk.port == CRTPPort.PARAM):
                    entry = self.fakeParamToc[varIndex]

                vartype = entry['vartype']
                if (pk.port == CRTPPort.PARAM and entry['writable'] is True):
                    vartype = vartype | (0x10)

                p.data = struct.pack('<BBB', cmd, entry['varid'], vartype)
                for ch in entry['vargroup']:
                    p.data.append(ord(ch))
                p.data.append(0)
                for ch in entry['varname']:
                    p.data.append(ord(ch))
                p.data.append(0)
                if (self.doIncompleteLogTOC is False):
                    self._send_packet(p)
                elif (varIndex < 5):
                    self._send_packet(p)
                else:
                    logger.info('TOC: Doing incomplete TOC, stopping after'
                                ' varIndex => 5')

            if (cmd == 1):  # TOC CRC32 request
                fakecrc = 0
                if (pk.port == CRTPPort.LOGGING):
                    tocLen = len(self.fakeLogToc)
                    fakecrc = 0xAAAAAAAA
                if (pk.port == CRTPPort.PARAM):
                    tocLen = len(self.fakeParamToc)
                    fakecrc = 0xBBBBBBBB

                if self._random_toc_crcs:
                    fakecrc = int(''.join(
                        random.choice('ABCDEF' + string.digits) for x in
                        range(8)), 16)
                    logger.debug('Generated random TOC CRC: 0x%x', fakecrc)
                logger.info('TOC[%d]: Requesting TOC CRC, sending back fake'
                            ' stuff: %d', pk.port, len(self.fakeLogToc))
                p = CRTPPacket()
                p.set_header(pk.port, 0)
                p.data = struct.pack('<BBIBB', 1, tocLen, fakecrc, 16, 24)
                self._send_packet(p)

    def handleParam(self, pk):
        chan = pk.channel
        cmd = pk.data[0]
        logger.debug('PARAM: Port=%d, Chan=%d, cmd=%d', pk.port,
                     chan, cmd)
        if (chan == 0):  # TOC Access
            self._handle_toc_access(pk)
        elif (chan == 2):  # Settings access
            varId = pk.data[0]
            formatStr = ParamTocElement.types[
                self.fakeParamToc[varId]['vartype']][1]
            newvalue = struct.unpack(formatStr, pk.data[1:])[0]
            self.fakeParamToc[varId]['value'] = newvalue
            logger.info('PARAM: New value [%s] for param [%d]', newvalue,
                        varId)
            # Send back the new value
            p = CRTPPacket()
            p.set_header(pk.port, 2)
            p.data += struct.pack('<B', varId)
            p.data += struct.pack(formatStr, self.fakeParamToc[varId]['value'])
            self._send_packet(p)
        elif (chan == 1):
            p = CRTPPacket()
            p.set_header(pk.port, 1)
            varId = cmd
            p.data.append(varId)
            formatStr = ParamTocElement.types[
                self.fakeParamToc[varId]['vartype']][1]
            p.data += struct.pack(formatStr, self.fakeParamToc[varId]['value'])
            logger.info('PARAM: Getting value for %d', varId)
            self._send_packet(p)

    def _handle_logging(self, pk):
        chan = pk.channel
        cmd = pk.data[0]
        logger.debug('LOG: Chan=%d, cmd=%d', chan, cmd)
        if (chan == 0):  # TOC Access
            self._handle_toc_access(pk)
        elif (chan == 1):  # Settings access
            if (cmd == 0):
                blockId = pk.data[1]
                if blockId not in self._added_blocks:
                    self._added_blocks.append(blockId)
                    logger.info('LOG:Adding block id=%d', blockId)
                    listofvars = pk.data[3:]
                    fakeThread = _FakeLoggingDataThread(self.queue, blockId,
                                                        listofvars,
                                                        self.fakeLogToc)
                    self.fakeLoggingThreads.append(fakeThread)
                    fakeThread.start()
                    # Anser that everything is ok
                    p = CRTPPacket()
                    p.set_header(5, 1)
                    p.data = struct.pack('<BBB', 0, blockId, 0x00)
                    self._send_packet(p)
                else:
                    p = CRTPPacket()
                    p.set_header(5, 1)
                    p.data = struct.pack('<BBB', 0, blockId, errno.EEXIST)
                    self._send_packet(p)
            if (cmd == 1):
                logger.warning('LOG: Appending block not implemented!')
            if (cmd == 2):
                blockId = pk.data[1]
                logger.info('LOG: Should delete block %d', blockId)
                success = False
                for fb in self.fakeLoggingThreads:
                    if (fb.blockId == blockId):
                        fb._disable_logging()
                        fb.stop()

                        p = CRTPPacket()
                        p.set_header(5, 1)
                        p.data = struct.pack('<BBB', cmd, blockId, 0x00)
                        self._send_packet(p)
                        logger.info('LOG: Deleted block=%d', blockId)
                        success = True
                if (success is False):
                    logger.warning('LOG: Could not delete block=%d, not found',
                                   blockId)
                    # TODO: Send back error code

            if (cmd == 3):
                blockId = pk.data[1]
                period = pk.data[2] * 10  # Sent as multiple of 10 ms
                logger.info('LOG:Starting block %d', blockId)
                success = False
                for fb in self.fakeLoggingThreads:
                    if (fb.blockId == blockId):
                        fb._enable_logging()
                        fb.period = period
                        p = CRTPPacket()
                        p.set_header(5, 1)
                        p.data = struct.pack('<BBB', cmd, blockId, 0x00)
                        self._send_packet(p)
                        logger.info('LOG:Started block=%d', blockId)
                        success = True
                if (success is False):
                    logger.info('LOG:Could not start block=%d, not found',
                                blockId)
                    # TODO: Send back error code
            if (cmd == 4):
                blockId = pk.data[1]
                logger.info('LOG:Pausing block %d', blockId)
                success = False
                for fb in self.fakeLoggingThreads:
                    if (fb.blockId == blockId):
                        fb._disable_logging()
                        p = CRTPPacket()
                        p.set_header(5, 1)
                        p.data = struct.pack('<BBB', cmd, blockId, 0x00)
                        self._send_packet(p)
                        logger.info('LOG:Pause block=%d', blockId)
                        success = True
                if (success is False):
                    logger.warning('LOG:Could not pause block=%d, not found',
                                   blockId)
                    # TODO: Send back error code
            if (cmd == 5):
                logger.info('LOG: Reset logging, but doing nothing')
                p = CRTPPacket()
                p.set_header(5, 1)
                p.data = struct.pack('<BBB', cmd, 0x00, 0x00)
                self._send_packet(p)

        elif (chan > 1):
            logger.warning('LOG: Uplink packets with channels > 1 not'
                           ' supported!')

    def _send_packet(self, pk):
        # Do not delay log data
        if (self._random_answer_delay and pk.port != 0x05 and
                pk.channel != 0x02):
            # Calculate a delay between 0ms and 250ms
            delay = random.randint(0, 250) / 1000.0
            logger.debug('Delaying answer %.2fms', delay * 1000)
            time.sleep(delay)
        self.queue.put(pk)


class _FakeLoggingDataThread(Thread):
    """Thread that will send back fake logging data via CRTP"""

    def __init__(self, outQueue, blockId, listofvars, fakeLogToc):
        Thread.__init__(self)
        self.starttime = datetime.now()
        self.outQueue = outQueue
        self.setDaemon(True)
        self.mod = 0
        self.blockId = blockId
        self.period = 0
        self.listofvars = listofvars
        self.shouldLog = False
        self.fakeLogToc = fakeLogToc
        self.fakeLoggingData = []
        self.setName('Fakelog block=%d' % blockId)
        self.shouldQuit = False

        logging.info('FakeDataLoggingThread created for blockid=%d', blockId)
        i = 0
        while (i < len(listofvars)):
            varType = listofvars[i]
            var_stored_as = (varType >> 8)
            var_fetch_as = (varType & 0xFF)
            if (var_stored_as > 0):
                addr = struct.unpack('<I', listofvars[i + 1:i + 5])
                logger.debug('FakeLoggingThread: We should log a memory addr'
                             ' 0x%04X', addr)
                self.fakeLoggingData.append([memlogging[var_fetch_as],
                                             memlogging[var_fetch_as]['min'],
                                             1])
                i = i + 5
            else:
                varId = listofvars[i]
                logger.debug('FakeLoggingThread: We should log variable from'
                             ' TOC: id=%d, type=0x%02X', varId, varType)
                for t in self.fakeLogToc:
                    if (varId == t['varid']):
                        # Each touple will have var data and current fake value
                        self.fakeLoggingData.append([t, t['min'], 1])
                i = i + 2

    def _enable_logging(self):
        self.shouldLog = True
        logging.info('_FakeLoggingDataThread: Enable thread [%s] at period %d',
                     self.getName(), self.period)

    def _disable_logging(self):
        self.shouldLog = False
        logging.info('_FakeLoggingDataThread: Disable thread [%s]',
                     self.getName())

    def stop(self):
        self.shouldQuit = True

    def run(self):
        while (self.shouldQuit is False):
            if (self.shouldLog is True):

                p = CRTPPacket()
                p.set_header(5, 2)
                p.data = struct.pack('<B', self.blockId)
                timestamp = int(
                    (datetime.now() - self.starttime).total_seconds() * 1000)
                p.data += struct.pack('BBB', timestamp & 0xff,
                                      (timestamp >> 8) & 0x0ff,
                                      (timestamp >> 16) & 0x0ff)  # Timestamp

                for d in self.fakeLoggingData:
                    # Set new value
                    d[1] = d[1] + d[0]['mod'] * d[2]
                    # Obej the limitations
                    if (d[1] > d[0]['max']):
                        d[1] = d[0]['max']  # Limit value
                        d[2] = -1  # Switch direction
                    if (d[1] < d[0]['min']):
                        d[1] = d[0]['min']  # Limit value
                        d[2] = 1  # Switch direction
                    # Pack value
                    formatStr = LogTocElement.types[d[0]['vartype']][1]
                    p.data += struct.pack(formatStr, d[1])
                self.outQueue.put(p)
            time.sleep(self.period / 1000.0)  # Period in ms here


class FakeConsoleThread(Thread):
    """Thread that will send back fake console data via CRTP"""

    def __init__(self, outQueue):
        Thread.__init__(self)
        self.outQueue = outQueue
        self.setDaemon(True)
        self._should_run = True

    def stop(self):
        self._shoud_run = False

    def run(self):
        # Temporary hack to test GPS from firmware by sending NMEA string
        # on console
        long_val = 0
        lat_val = 0
        alt_val = 0

        while (self._should_run):
            long_val += 1
            lat_val += 1
            alt_val += 1.0

            long_string = '5536.677%d' % (long_val % 99)
            lat_string = '01259.645%d' % (lat_val % 99)
            alt_string = '%.1f' % (alt_val % 100.0)

            # Copy of what is sent from the module, but note that only
            # the GPGGA message is being simulated, the others are fixed...
            self._send_text('Time is now %s\n' % datetime.now())
            self._send_text('$GPVTG,,T,,M,0.386,N,0.716,K,A*2E\n')
            self._send_text('$GPGGA,135544.0')
            self._send_text('0,%s,N,%s,E,1,04,2.62,3.6,M,%s,M,,*58\n' % (
                long_string, lat_string, alt_string))
            self._send_text(
                '$GPGSA,A,3,31,20,23,07,,,,,,,,,3.02,2.62,1.52*05\n')
            self._send_text('$GPGSV,2,1,07,07,09,181,15,13,63,219,26,16,02,'
                            '097,,17,05,233,20*7E\n')
            self._send_text(
                '$GPGSV,2,2,07,20,42,119,35,23,77,097,27,31,12,032,19*47\n')
            self._send_text(
                '$GPGLL,5536.67734,N,01259.64578,E,135544.00,A,A*68\n')

            time.sleep(2)

    def _send_text(self, message):
        p = CRTPPacket()
        p.set_header(0, 0)

        # This might be done prettier ;-)
        p.data = message

        self.outQueue.put(p)
