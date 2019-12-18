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
Crazyflie radio bootloader for flashing firmware.
"""
import binascii
import logging
import math
import struct
import time

import cflib.crtp
from .boottypes import Target
from .boottypes import TargetTypes
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort

__author__ = 'Bitcraze AB'
__all__ = ['Cloader']

logger = logging.getLogger(__name__)


class Cloader:
    """Bootloader utility for the Crazyflie"""

    def __init__(self, link, info_cb=None, in_boot_cb=None):
        """Init the communication class by starting to communicate with the
        link given. clink is the link address used after resetting to the
        bootloader.

        The device is actually considered in firmware mode.
        """
        self.link = None
        self.uri = link
        self.in_loader = False

        self.page_size = 0
        self.buffer_pages = 0
        self.flash_pages = 0
        self.start_page = 0
        self.cpuid = 'N/A'
        self.error_code = 0
        self.protocol_version = 0xFF

        self._info_cb = info_cb
        self._in_boot_cb = in_boot_cb

        self.targets = {}
        self.mapping = None
        self._available_boot_uri = ('radio://0/110/2M', 'radio://0/0/2M')

    def close(self):
        """ Close the link """
        if self.link:
            self.link.close()

    def scan_for_bootloader(self):
        link = cflib.crtp.get_link_driver('radio://0')
        ts = time.time()
        res = ()
        while len(res) == 0 and (time.time() - ts) < 10:
            res = link.scan_selected(self._available_boot_uri)

        link.close()

        if len(res) > 0:
            return res[0]
        return None

    def reset_to_bootloader(self, target_id):
        retry_counter = 5
        pk = CRTPPacket()
        pk.set_header(0xFF, 0xFF)
        pk.data = (target_id, 0xFF)
        self.link.send_packet(pk)

        got_answer = False
        while(not got_answer and retry_counter >= 0):
            pk = self.link.receive_packet(1)
            if pk and pk.header == 0xFF:
                try:
                    data = struct.unpack('<BB', pk.data[0:2])
                    got_answer = data == (target_id, 0xFF)
                except struct.error:
                    # Failed unpacking, retry
                    pass

        if got_answer:
            new_address = (0xb1,) + struct.unpack('<BBBB', pk.data[2:6][::-1])

            # The reset packet arrival cannot be checked.
            # Send it more than one time to increase the chances it makes it.
            for _ in range(10):
                pk = CRTPPacket()
                pk.set_header(0xFF, 0xFF)
                pk.data = (target_id, 0xF0, 0x00)
                self.link.send_packet(pk)

            addr = int(binascii.hexlify(
                struct.pack('B' * 5, *new_address)), 16)

            time.sleep(1)
            self.link.close()
            time.sleep(0.2)
            self.link = cflib.crtp.get_link_driver(
                'radio://0/0/2M/{:X}'.format(addr))

            return True
        else:
            return False

    def reset_to_bootloader1(self, cpu_id):
        """ Reset to the bootloader
        The parameter cpuid shall correspond to the device to reset.

        Return true if the reset has been done and the contact with the
        bootloader is established.
        """
        # Send an echo request and wait for the answer
        # Mainly aim to bypass a bug of the crazyflie firmware that prevents
        # reset before normal CRTP communication
        pk = CRTPPacket()
        pk.port = CRTPPort.LINKCTRL
        pk.data = (1, 2, 3) + cpu_id
        self.link.send_packet(pk)

        pk = None
        while True:
            pk = self.link.receive_packet(2)
            if not pk:
                return False

            if pk.port == CRTPPort.LINKCTRL:
                break

        # Send the reset to bootloader request
        pk = CRTPPacket()
        pk.set_header(0xFF, 0xFF)
        pk.data = (0xFF, 0xFE) + cpu_id
        self.link.send_packet(pk)

        # Wait to ack the reset ...
        pk = None
        while True:
            pk = self.link.receive_packet(2)
            if not pk:
                return False

            if pk.port == 0xFF and tuple(pk.data) == (0xFF, 0xFE) + cpu_id:
                pk.data = (0xFF, 0xF0) + cpu_id
                self.link.send_packet(pk)
                break

        time.sleep(0.1)
        self.link.close()
        self.link = cflib.crtp.get_link_driver(self.clink_address)
        # time.sleep(0.1)

        return self._update_info()

    def reset_to_firmware(self, target_id):
        """ Reset to firmware
        The parameter cpuid shall correspond to the device to reset.

        Return true if the reset has been done
        """
        # The fake CPU ID is legacy from the Crazyflie 1.0
        # In order to reset the CPU id had to be sent, but this
        # was removed before launching it. But the length check is
        # still in the bootloader. So to work around this bug so
        # some extra data needs to be sent.
        fake_cpu_id = (1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12)
        # Send the reset to bootloader request
        pk = CRTPPacket()
        pk.set_header(0xFF, 0xFF)
        pk.data = (target_id, 0xFF) + fake_cpu_id
        self.link.send_packet(pk)

        # Wait to ack the reset ...
        pk = None
        while True:
            pk = self.link.receive_packet(2)
            if not pk:
                return False

            if (pk.header == 0xFF and struct.unpack(
                    'B' * len(pk.data), pk.data)[:2] == (target_id, 0xFF)):
                # Difference in CF1 and CF2 (CPU ID)
                if target_id == 0xFE:
                    pk.data = (target_id, 0xF0, 0x01)
                else:
                    pk.data = (target_id, 0xF0) + fake_cpu_id
                self.link.send_packet(pk)
                break

        time.sleep(0.1)

    def open_bootloader_uri(self, uri=None):
        if self.link:
            self.link.close()
        if uri:
            self.link = cflib.crtp.get_link_driver(uri)
        else:
            self.link = cflib.crtp.get_link_driver(self.clink_address)

    def check_link_and_get_info(self, target_id=0xFF):
        """Try to get a connection with the bootloader by requesting info
        5 times. This let roughly 10 seconds to boot the copter ..."""
        for _ in range(0, 5):
            if self._update_info(target_id):
                if self._in_boot_cb:
                    self._in_boot_cb.call(True, self.targets[
                        target_id].protocol_version)
                if self._info_cb:
                    self._info_cb.call(self.targets[target_id])
                return True
        return False

    def request_info_update(self, target_id):
        if target_id not in self.targets:
            self._update_info(target_id)
        if self._info_cb:
            self._info_cb.call(self.targets[target_id])
        return self.targets[target_id]

    def _update_info(self, target_id):
        """ Call the command getInfo and fill up the information received in
        the fields of the object
        """

        # Call getInfo ...
        pk = CRTPPacket()
        pk.set_header(0xFF, 0xFF)
        pk.data = (target_id, 0x10)
        self.link.send_packet(pk)

        # Wait for the answer
        pk = self.link.receive_packet(2)

        if (pk and pk.header == 0xFF and struct.unpack('<BB', pk.data[0:2]) ==
                (target_id, 0x10)):
            tab = struct.unpack('BBHHHH', pk.data[0:10])
            cpuid = struct.unpack('B' * 12, pk.data[10:22])
            if target_id not in self.targets:
                self.targets[target_id] = Target(target_id)
            self.targets[target_id].addr = target_id
            if len(pk.data) > 22:
                self.targets[target_id].protocol_version = pk.datat[22]
                self.protocol_version = pk.datat[22]
            self.targets[target_id].page_size = tab[2]
            self.targets[target_id].buffer_pages = tab[3]
            self.targets[target_id].flash_pages = tab[4]
            self.targets[target_id].start_page = tab[5]
            self.targets[target_id].cpuid = '%02X' % cpuid[0]
            for i in cpuid[1:]:
                self.targets[target_id].cpuid += ':%02X' % i

            if (self.protocol_version == 0x10 and
                    target_id == TargetTypes.STM32):
                self._update_mapping(target_id)

            return True

        return False

    def _update_mapping(self, target_id):
        pk = CRTPPacket()
        pk.set_header(0xff, 0xff)
        pk.data = (target_id, 0x12)
        self.link.send_packet(pk)

        pk = self.link.receive_packet(2)

        if (pk and pk.header == 0xFF and struct.unpack('<BB', pk.data[0:2]) ==
                (target_id, 0x12)):
            m = pk.datat[2:]

            if (len(m) % 2) != 0:
                raise Exception('Malformed flash mapping packet')

            self.mapping = []
            page = 0
            for i in range(int(len(m) / 2)):
                for j in range(m[2 * i]):
                    self.mapping.append(page)
                    page += m[(2 * i) + 1]

    def upload_buffer(self, target_id, page, address, buff):
        """Upload data into a buffer on the Crazyflie"""
        # print len(buff)
        count = 0
        pk = CRTPPacket()
        pk.set_header(0xFF, 0xFF)
        pk.data = struct.pack('=BBHH', target_id, 0x14, page, address)

        for i in range(0, len(buff)):
            pk.data.append(buff[i])

            count += 1

            if count > 24:
                self.link.send_packet(pk)
                count = 0
                pk = CRTPPacket()
                pk.set_header(0xFF, 0xFF)
                pk.data = struct.pack('=BBHH', target_id, 0x14, page,
                                      i + address + 1)

        self.link.send_packet(pk)

    def read_flash(self, addr=0xFF, page=0x00):
        """Read back a flash page from the Crazyflie and return it"""
        buff = bytearray()

        page_size = self.targets[addr].page_size

        for i in range(0, int(math.ceil(page_size / 25.0))):
            pk = None
            retry_counter = 5
            while ((not pk or pk.header != 0xFF or
                    struct.unpack('<BB', pk.data[0:2]) != (addr, 0x1C)) and
                    retry_counter >= 0):
                pk = CRTPPacket()
                pk.set_header(0xFF, 0xFF)
                pk.data = struct.pack('<BBHH', addr, 0x1C, page, (i * 25))
                self.link.send_packet(pk)

                pk = self.link.receive_packet(1)
                retry_counter -= 1
            if (retry_counter < 0):
                return None
            else:
                buff += pk.data[6:]

        # For some reason we get one byte extra here...
        return buff[0:page_size]

    def write_flash(self, addr, page_buffer, target_page, page_count):
        """Initiate flashing of data in the buffer to flash."""
        # print "Write page", flashPage
        # print "Writing page [%d] and [%d] forward" % (flashPage, nPage)
        pk = None

        # Flushing downlink ...
        pk = self.link.receive_packet(0)
        while pk is not None:
            pk = self.link.receive_packet(0)

        retry_counter = 5
        # print "Flasing to 0x{:X}".format(addr)
        while ((not pk or pk.header != 0xFF or
                struct.unpack('<BB', pk.data[0:2]) != (addr, 0x18)) and
               retry_counter >= 0):
            pk = CRTPPacket()
            pk.set_header(0xFF, 0xFF)
            pk.data = struct.pack('<BBHHH', addr, 0x18, page_buffer,
                                  target_page, page_count)
            self.link.send_packet(pk)

            # Timeout for writing to flash is raised from 1s (used elsewhere
            # in this module) to 2.5s because it may take more than a second
            # to erase a page on the STM32F405.
            #
            # See https://github.com/bitcraze/crazyflie-lib-python/issues/98
            # for more details.
            pk = self.link.receive_packet(2.5)
            retry_counter -= 1

        if retry_counter < 0:
            self.error_code = -1
            return False

        self.error_code = pk.data[3]

        return pk.data[2] == 1

    def decode_cpu_id(self, cpuid):
        """Decode the CPU id into a string"""
        ret = ()
        for i in cpuid.split(':'):
            ret += (eval('0x' + i),)

        return ret
