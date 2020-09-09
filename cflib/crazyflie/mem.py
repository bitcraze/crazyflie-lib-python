#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2014 Bitcraze AB
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
Enables flash access to the Crazyflie.

"""
import errno
import logging
import struct
from array import array
from binascii import crc32
from functools import reduce
from threading import Lock

from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.callbacks import Caller

__author__ = 'Bitcraze AB'
__all__ = ['Memory', 'MemoryElement']

# Channels used for the logging port
CHAN_INFO = 0
CHAN_READ = 1
CHAN_WRITE = 2

# Commands used when accessing the Settings port
CMD_INFO_VER = 0
CMD_INFO_NBR = 1
CMD_INFO_DETAILS = 2

EEPROM_TOKEN = b'0xBC'

logger = logging.getLogger(__name__)


class MemoryElement(object):
    """A memory """

    TYPE_I2C = 0
    TYPE_1W = 1
    TYPE_DRIVER_LED = 0x10
    TYPE_LOCO = 0x11
    TYPE_TRAJ = 0x12
    TYPE_LOCO2 = 0x13
    TYPE_LH = 0x14
    TYPE_MEMORY_TESTER = 0x15
    TYPE_DRIVER_LEDTIMING = 0x17

    def __init__(self, id, type, size, mem_handler):
        """Initialize the element with default values"""
        self.id = id
        self.type = type
        self.size = size
        self.mem_handler = mem_handler

    @staticmethod
    def type_to_string(t):
        """Get string representation of memory type"""
        if t == MemoryElement.TYPE_I2C:
            return 'I2C'
        if t == MemoryElement.TYPE_1W:
            return '1-wire'
        if t == MemoryElement.TYPE_DRIVER_LEDTIMING:
            return 'LED memory driver'
        if t == MemoryElement.TYPE_DRIVER_LED:
            return 'LED driver'
        if t == MemoryElement.TYPE_LOCO:
            return 'Loco Positioning'
        if t == MemoryElement.TYPE_TRAJ:
            return 'Trajectory'
        if t == MemoryElement.TYPE_LOCO2:
            return 'Loco Positioning 2'
        if t == MemoryElement.TYPE_LH:
            return 'Lighthouse positioning'
        if t == MemoryElement.TYPE_MEMORY_TESTER:
            return 'Memory tester'
        return 'Unknown'

    def new_data(self, mem, addr, data):
        logger.debug('New data, but not OW mem')

    def __str__(self):
        """Generate debug string for memory"""
        return ('Memory: id={}, type={}, size={}'.format(
            self.id, MemoryElement.type_to_string(self.type), self.size))


class LED:
    """Used to set color/intensity of one LED in the LED-ring"""

    def __init__(self):
        """Initialize to off"""
        self.r = 0
        self.g = 0
        self.b = 0
        self.intensity = 100

    def set(self, r, g, b, intensity=None):
        """Set the R/G/B and optionally intensity in one call"""
        self.r = r
        self.g = g
        self.b = b
        if intensity:
            self.intensity = intensity


class LEDDriverMemory(MemoryElement):
    """Memory interface for using the LED-ring mapped memory for setting RGB
       values for all the LEDs in the ring"""

    def __init__(self, id, type, size, mem_handler):
        """Initialize with 12 LEDs"""
        super(LEDDriverMemory, self).__init__(id=id, type=type, size=size,
                                              mem_handler=mem_handler)
        self._update_finished_cb = None
        self._write_finished_cb = None

        self.leds = []
        for i in range(12):
            self.leds.append(LED())

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            logger.debug(
                "Got new data from the LED driver, but we don't care.")

    def write_data(self, write_finished_cb):
        """Write the saved LED-ring data to the Crazyflie"""
        self._write_finished_cb = write_finished_cb
        data = bytearray()
        for led in self.leds:
            # In order to fit all the LEDs in one radio packet RGB565 is used
            # to compress the colors. The calculations below converts 3 bytes
            # RGB into 2 bytes RGB565. Then shifts the value of each color to
            # LSB, applies the intensity and shifts them back for correct
            # alignment on 2 bytes.
            R5 = ((int)((((int(led.r) & 0xFF) * 249 + 1014) >> 11) & 0x1F) *
                  led.intensity / 100)
            G6 = ((int)((((int(led.g) & 0xFF) * 253 + 505) >> 10) & 0x3F) *
                  led.intensity / 100)
            B5 = ((int)((((int(led.b) & 0xFF) * 249 + 1014) >> 11) & 0x1F) *
                  led.intensity / 100)
            tmp = (int(R5) << 11) | (int(G6) << 5) | (int(B5) << 0)
            data += bytearray((tmp >> 8, tmp & 0xFF))
        self.mem_handler.write(self, 0x00, data, flush_queue=True)

    def update(self, update_finished_cb):
        """Request an update of the memory content"""
        if not self._update_finished_cb:
            self._update_finished_cb = update_finished_cb
            self.valid = False
            logger.debug('Updating content of memory {}'.format(self.id))
            # Start reading the header
            self.mem_handler.read(self, 0, 16)

    def write_done(self, mem, addr):
        if self._write_finished_cb and mem.id == self.id:
            logger.debug('Write to LED driver done')
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None

    def disconnect(self):
        self._update_finished_cb = None
        self._write_finished_cb = None


class LEDTimingsDriverMemory(MemoryElement):
    """Memory interface for using the LED-ring mapped memory for setting RGB
       values over time. To upload and run a show sequence of
       the LEDs in the ring"""

    def __init__(self, id, type, size, mem_handler):
        super(LEDTimingsDriverMemory, self).__init__(id=id,
                                                     type=type,
                                                     size=size,
                                                     mem_handler=mem_handler)
        self._update_finished_cb = None
        self._write_finished_cb = None

        self.timings = []

    def add(self, time, rgb, leds=0, fade=False, rotate=0):
        self.timings.append({
            'time': time,
            'rgb': rgb,
            'leds': leds,
            'fade': fade,
            'rotate': rotate
        })

    def write_data(self, write_finished_cb):
        if write_finished_cb is not None:
            self._write_finished_cb = write_finished_cb

        data = []
        for timing in self.timings:
            # In order to fit all the LEDs in one radio packet RGB565 is used
            # to compress the colors. The calculations below converts 3 bytes
            # RGB into 2 bytes RGB565. Then shifts the value of each color to
            # LSB, applies the intensity and shifts them back for correct
            # alignment on 2 bytes.
            R5 = ((int)((((int(timing['rgb']['r']) & 0xFF) * 249 + 1014) >> 11)
                        & 0x1F))
            G6 = ((int)((((int(timing['rgb']['g']) & 0xFF) * 253 + 505) >> 10)
                        & 0x3F))
            B5 = ((int)((((int(timing['rgb']['b']) & 0xFF) * 249 + 1014) >> 11)
                        & 0x1F))
            led = (int(R5) << 11) | (int(G6) << 5) | (int(B5) << 0)
            extra = ((timing['leds']) & 0x0F) | (
                (timing['fade'] << 4) & 0x10) | (
                (timing['rotate'] << 5) & 0xE0)

            if (timing['time'] & 0xFF) != 0 or led != 0 or extra != 0:
                data += [timing['time'] & 0xFF, led >> 8, led & 0xFF, extra]

        data += [0, 0, 0, 0]
        self.mem_handler.write(self, 0x00, bytearray(data), flush_queue=True)

    def write_done(self, mem, addr):
        if mem.id == self.id and self._write_finished_cb:
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None

    def disconnect(self):
        self._update_finished_cb = None
        self._write_finished_cb = None


class I2CElement(MemoryElement):

    def __init__(self, id, type, size, mem_handler):
        super(I2CElement, self).__init__(id=id, type=type, size=size,
                                         mem_handler=mem_handler)
        self._update_finished_cb = None
        self._write_finished_cb = None
        self.elements = {}
        self.valid = False

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            if addr == 0:
                done = False
                # Check for header
                if data[0:4] == EEPROM_TOKEN:
                    logger.debug('Got new data: {}'.format(data))
                    [self.elements['version'],
                     self.elements['radio_channel'],
                     self.elements['radio_speed'],
                     self.elements['pitch_trim'],
                     self.elements['roll_trim']] = struct.unpack('<BBBff',
                                                                 data[4:15])
                    if self.elements['version'] == 0:
                        done = True
                    elif self.elements['version'] == 1:
                        self.datav0 = data
                        self.mem_handler.read(self, 16, 5)
                else:
                    self.valid = False
                    if self._update_finished_cb:
                        self._update_finished_cb(self)
                        self._update_finished_cb = None

            if addr == 16:
                [radio_address_upper, radio_address_lower] = struct.unpack(
                    '<BI', self.datav0[15:16] + data[0:4])
                self.elements['radio_address'] = int(
                    radio_address_upper) << 32 | radio_address_lower

                logger.debug(self.elements)
                data = self.datav0 + data
                done = True

            if done:
                if self._checksum256(data[:len(data) - 1]) == \
                        data[len(data) - 1]:
                    self.valid = True
                if self._update_finished_cb:
                    self._update_finished_cb(self)
                    self._update_finished_cb = None

    def _checksum256(self, st):
        return reduce(lambda x, y: x + y, list(st)) % 256

    def write_data(self, write_finished_cb):
        image = bytearray()
        if self.elements['version'] == 0:
            data = (
                0x00, self.elements['radio_channel'],
                self.elements['radio_speed'],
                self.elements['pitch_trim'], self.elements['roll_trim'])
            image += struct.pack('<BBBff', *data)
        elif self.elements['version'] == 1:
            data = (
                0x01, self.elements['radio_channel'],
                self.elements['radio_speed'],
                self.elements['pitch_trim'], self.elements['roll_trim'],
                self.elements['radio_address'] >> 32,
                self.elements['radio_address'] & 0xFFFFFFFF)
            image += struct.pack('<BBBffBI', *data)
        # Adding some magic:
        image = EEPROM_TOKEN + image
        image += struct.pack('B', self._checksum256(image))

        self._write_finished_cb = write_finished_cb

        self.mem_handler.write(self, 0x00,
                               struct.unpack('B' * len(image), image))

    def update(self, update_finished_cb):
        """Request an update of the memory content"""
        if not self._update_finished_cb:
            self._update_finished_cb = update_finished_cb
            self.valid = False
            logger.debug('Updating content of memory {}'.format(self.id))
            # Start reading the header
            self.mem_handler.read(self, 0, 16)

    def write_done(self, mem, addr):
        if self._write_finished_cb and mem.id == self.id:
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None

    def disconnect(self):
        self._update_finished_cb = None
        self._write_finished_cb = None


class OWElement(MemoryElement):
    """Memory class with extra functionality for 1-wire memories"""

    element_mapping = {
        1: 'Board name',
        2: 'Board revision',
        3: 'Custom'
    }

    def __init__(self, id, type, size, addr, mem_handler):
        """Initialize the memory with good defaults"""
        super(OWElement, self).__init__(id=id, type=type, size=size,
                                        mem_handler=mem_handler)
        self.addr = addr

        self.valid = False

        self.vid = None
        self.pid = None
        self.name = None
        self.pins = None
        self.elements = {}

        self._update_finished_cb = None
        self._write_finished_cb = None

        self._rev_element_mapping = {}
        for key in list(OWElement.element_mapping.keys()):
            self._rev_element_mapping[OWElement.element_mapping[key]] = key

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            if addr == 0:
                if self._parse_and_check_header(data[0:8]):
                    if self._parse_and_check_elements(data[9:11]):
                        self.valid = True
                        self._update_finished_cb(self)
                        self._update_finished_cb = None
                    else:
                        # We need to fetch the elements, find out the length
                        (elem_ver, elem_len) = struct.unpack('BB', data[8:10])
                        self.mem_handler.read(self, 8, elem_len + 3)
                else:
                    # Call the update if the CRC check of the header fails,
                    # we're done here
                    if self._update_finished_cb:
                        self._update_finished_cb(self)
                        self._update_finished_cb = None
            elif addr == 0x08:
                if self._parse_and_check_elements(data):
                    self.valid = True
                if self._update_finished_cb:
                    self._update_finished_cb(self)
                    self._update_finished_cb = None

    def _parse_and_check_elements(self, data):
        """
        Parse and check the CRC and length of the elements part of the memory
        """
        crc = data[-1]
        test_crc = crc32(data[:-1]) & 0x0ff
        elem_data = data[2:-1]
        if test_crc == crc:
            while len(elem_data) > 0:
                (eid, elen) = struct.unpack('BB', elem_data[:2])
                self.elements[self.element_mapping[eid]] = \
                    elem_data[2:2 + elen].decode('ISO-8859-1')
                elem_data = elem_data[2 + elen:]
            return True
        return False

    def write_done(self, mem, addr):
        if self._write_finished_cb:
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None

    def write_data(self, write_finished_cb):
        # First generate the header part
        header_data = struct.pack('<BIBB', 0xEB, self.pins, self.vid, self.pid)
        header_crc = crc32(header_data) & 0x0ff
        header_data += struct.pack('B', header_crc)

        # Now generate the elements part
        elem = bytearray()
        logger.debug(list(self.elements.keys()))
        for element in reversed(list(self.elements.keys())):
            elem_string = self.elements[element]
            key_encoding = self._rev_element_mapping[element]
            elem += struct.pack('BB', key_encoding, len(elem_string))
            elem += bytearray(elem_string.encode('ISO-8859-1'))

        elem_data = struct.pack('BB', 0x00, len(elem))
        elem_data += elem
        elem_crc = crc32(elem_data) & 0x0ff
        elem_data += struct.pack('B', elem_crc)

        data = header_data + elem_data

        self.mem_handler.write(self, 0x00,
                               struct.unpack('B' * len(data), data))

        self._write_finished_cb = write_finished_cb

    def erase(self, write_finished_cb):
        erase_data = array('B', [0xFF] * 112)
        self.mem_handler.write(self, 0x00,
                               struct.unpack('B' * len(erase_data),
                                             erase_data))

        self._write_finished_cb = write_finished_cb

    def update(self, update_finished_cb):
        """Request an update of the memory content"""
        if not self._update_finished_cb:
            self._update_finished_cb = update_finished_cb
            self.valid = False
            logger.debug('Updating content of memory {}'.format(self.id))
            # Start reading the header
            self.mem_handler.read(self, 0, 11)

    def _parse_and_check_header(self, data):
        """Parse and check the CRC of the header part of the memory"""
        (start, self.pins, self.vid, self.pid, crc) = struct.unpack('<BIBBB',
                                                                    data)
        test_crc = crc32(data[:-1]) & 0x0ff
        if start == 0xEB and crc == test_crc:
            return True
        return False

    def __str__(self):
        """Generate debug string for memory"""
        return ('OW {} ({:02X}:{:02X}): {}'.format(
            self.addr, self.vid, self.pid, self.elements))

    def disconnect(self):
        self._update_finished_cb = None
        self._write_finished_cb = None


class AnchorData:
    """Holds data for one anchor"""

    def __init__(self, position=(0.0, 0.0, 0.0), is_valid=False):
        self.position = position
        self.is_valid = is_valid

    def set_from_mem_data(self, data):
        x, y, z, self.is_valid = struct.unpack('<fff?', data)
        self.position = (x, y, z)


class LocoMemory(MemoryElement):
    """Memory interface for accessing data from the Loco Positioning system"""

    SIZE_OF_FLOAT = 4
    MEM_LOCO_INFO = 0x0000
    MEM_LOCO_INFO_LEN = 1
    MEM_LOCO_ANCHOR_BASE = 0x1000
    MEM_LOCO_ANCHOR_PAGE_SIZE = 0x0100
    MEM_LOCO_PAGE_LEN = (3 * SIZE_OF_FLOAT) + 1

    def __init__(self, id, type, size, mem_handler):
        super(LocoMemory, self).__init__(id=id, type=type, size=size,
                                         mem_handler=mem_handler)
        self._update_finished_cb = None

        self.anchor_data = []
        self.nr_of_anchors = 0
        self.valid = False

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        done = False
        if mem.id == self.id:
            if addr == LocoMemory.MEM_LOCO_INFO:
                self.nr_of_anchors = data[0]
                if self.nr_of_anchors == 0:
                    done = True
                else:
                    self.anchor_data = \
                        [AnchorData() for _ in range(self.nr_of_anchors)]
                    self._request_page(0)
            else:
                page = int((addr - LocoMemory.MEM_LOCO_ANCHOR_BASE) /
                           LocoMemory.MEM_LOCO_ANCHOR_PAGE_SIZE)

                self.anchor_data[page].set_from_mem_data(data)

                next_page = page + 1
                if next_page < self.nr_of_anchors:
                    self._request_page(next_page)
                else:
                    done = True

        if done:
            self.valid = True
            if self._update_finished_cb:
                self._update_finished_cb(self)
                self._update_finished_cb = None

    def update(self, update_finished_cb):
        """Request an update of the memory content"""
        if not self._update_finished_cb:
            self._update_finished_cb = update_finished_cb
            self.anchor_data = []
            self.nr_of_anchors = 0
            self.valid = False
            logger.debug('Updating content of memory {}'.format(self.id))

            # Start reading the header
            self.mem_handler.read(self, LocoMemory.MEM_LOCO_INFO,
                                  LocoMemory.MEM_LOCO_INFO_LEN)

    def disconnect(self):
        self._update_finished_cb = None

    def _request_page(self, page):
        addr = LocoMemory.MEM_LOCO_ANCHOR_BASE + \
            LocoMemory.MEM_LOCO_ANCHOR_PAGE_SIZE * page
        self.mem_handler.read(self, addr, LocoMemory.MEM_LOCO_PAGE_LEN)


class AnchorData2:
    """Holds data for one anchor"""

    def __init__(self, position=(0.0, 0.0, 0.0), is_valid=False):
        self.position = position
        self.is_valid = is_valid

    def set_from_mem_data(self, data):
        x, y, z, self.is_valid = struct.unpack('<fff?', data)
        self.position = (x, y, z)


class LocoMemory2(MemoryElement):
    """Memory interface for accessing data from the Loco Positioning system
       version 2"""

    SIZE_OF_FLOAT = 4

    # MAX_NR_OF_ANCHORS should be set to the number of anchors
    # supported by the firmware. Preferably short enough to fit into one packet
    MAX_NR_OF_ANCHORS = 16
    ID_LIST_LEN = 1 + MAX_NR_OF_ANCHORS

    ADR_ID_LIST = 0x0000
    ADR_ACTIVE_ID_LIST = 0x1000
    ADR_ANCHOR_BASE = 0x2000

    ANCHOR_PAGE_SIZE = 0x0100
    PAGE_LEN = (3 * SIZE_OF_FLOAT) + 1

    def __init__(self, id, type, size, mem_handler):
        super(LocoMemory2, self).__init__(id=id, type=type, size=size,
                                          mem_handler=mem_handler)
        self._update_ids_finished_cb = None
        self._update_active_ids_finished_cb = None
        self._update_data_finished_cb = None
        self._currently_fetching_index = -1

        self.anchor_ids = []
        self.active_anchor_ids = []
        self.anchor_data = {}
        self.nr_of_anchors = 0
        self.ids_valid = False
        self.active_ids_valid = False
        self.data_valid = False

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            if addr == LocoMemory2.ADR_ID_LIST:
                self._handle_id_list_data(data)
            elif addr == LocoMemory2.ADR_ACTIVE_ID_LIST:
                self._handle_active_id_list_data(data)
            else:
                id = int((addr - LocoMemory2.ADR_ANCHOR_BASE) /
                         LocoMemory2.ANCHOR_PAGE_SIZE)
                self._handle_anchor_data(id, data)

    def update_id_list(self, update_ids_finished_cb):
        """Request an update of the id list"""
        if not self._update_ids_finished_cb:
            self._update_ids_finished_cb = update_ids_finished_cb
            self.anchor_ids = []
            self.active_anchor_ids = []
            self.anchor_data = {}

            self.nr_of_anchors = 0
            self.ids_valid = False
            self.data_valid = False

            logger.debug('Updating ids of memory {}'.format(self.id))

            # Start reading the header
            self.mem_handler.read(self, LocoMemory2.ADR_ID_LIST,
                                  LocoMemory2.ID_LIST_LEN)

    def update_active_id_list(self, update_active_ids_finished_cb):
        """Request an update of the active id list"""
        if not self._update_active_ids_finished_cb:
            self._update_active_ids_finished_cb = update_active_ids_finished_cb
            self.active_anchor_ids = []

            self.active_ids_valid = False

            logger.debug('Updating active ids of memory {}'.format(self.id))

            # Start reading the header
            self.mem_handler.read(self, LocoMemory2.ADR_ACTIVE_ID_LIST,
                                  LocoMemory2.ID_LIST_LEN)

    def update_data(self, update_data_finished_cb):
        """Request an update of the anchor data"""
        if not self._update_data_finished_cb and self.nr_of_anchors > 0:
            self._update_data_finished_cb = update_data_finished_cb
            self.anchor_data = {}

            self.data_valid = False
            self._nr_of_anchors_to_fetch = self.nr_of_anchors

            logger.debug('Updating anchor data of memory {}'.format(self.id))

            # Start reading the first anchor
            self._currently_fetching_index = 0
            self._request_page(self.anchor_ids[self._currently_fetching_index])

    def disconnect(self):
        self._update_ids_finished_cb = None
        self._update_data_finished_cb = None

    def _handle_id_list_data(self, data):
        self.nr_of_anchors = data[0]
        for i in range(self.nr_of_anchors):
            self.anchor_ids.append(data[1 + i])
        self.ids_valid = True

        if self._update_ids_finished_cb:
            self._update_ids_finished_cb(self)
            self._update_ids_finished_cb = None

    def _handle_active_id_list_data(self, data):
        count = data[0]
        for i in range(count):
            self.active_anchor_ids.append(data[1 + i])
        self.active_ids_valid = True

        if self._update_active_ids_finished_cb:
            self._update_active_ids_finished_cb(self)
            self._update_active_ids_finished_cb = None

    def _handle_anchor_data(self, id, data):
        anchor = AnchorData2()
        anchor.set_from_mem_data(data)
        self.anchor_data[id] = anchor

        self._currently_fetching_index += 1
        if self._currently_fetching_index < self.nr_of_anchors:
            self._request_page(self.anchor_ids[self._currently_fetching_index])
        else:
            self.data_valid = True
            if self._update_data_finished_cb:
                self._update_data_finished_cb(self)
                self._update_data_finished_cb = None

    def _request_page(self, page):
        addr = LocoMemory2.ADR_ANCHOR_BASE + \
            LocoMemory2.ANCHOR_PAGE_SIZE * page
        self.mem_handler.read(self, addr, LocoMemory2.PAGE_LEN)


class Poly4D:
    class Poly:
        def __init__(self, values=[0.0] * 8):
            self.values = values

    def __init__(self, duration, x=None, y=None, z=None, yaw=None):
        self.duration = duration
        self.x = x if x else self.Poly()
        self.y = y if y else self.Poly()
        self.z = z if z else self.Poly()
        self.yaw = yaw if yaw else self.Poly()


class TrajectoryMemory(MemoryElement):
    """
    Memory interface for trajectories used by the high level commander
    """

    def __init__(self, id, type, size, mem_handler):
        """Initialize trajectory memory"""
        super(TrajectoryMemory, self).__init__(id=id, type=type, size=size,
                                               mem_handler=mem_handler)
        self._write_finished_cb = None

        # A list of Poly4D objects to write to the Crazyflie
        self.poly4Ds = []

    def write_data(self, write_finished_cb):
        """Write trajectory data to the Crazyflie"""
        self._write_finished_cb = write_finished_cb
        data = bytearray()

        for poly4D in self.poly4Ds:
            data += struct.pack('<ffffffff', *poly4D.x.values)
            data += struct.pack('<ffffffff', *poly4D.y.values)
            data += struct.pack('<ffffffff', *poly4D.z.values)
            data += struct.pack('<ffffffff', *poly4D.yaw.values)
            data += struct.pack('<f', poly4D.duration)

        self.mem_handler.write(self, 0x00, data, flush_queue=True)

    def write_done(self, mem, addr):
        if self._write_finished_cb and mem.id == self.id:
            logger.debug('Write trajectory data done')
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None

    def disconnect(self):
        self._write_finished_cb = None


class LighthouseBsGeometry:
    """Container for geometry data of one Lighthouse base station"""

    SIZE_FLOAT = 4
    SIZE_VECTOR = 3 * SIZE_FLOAT
    SIZE_GEOMETRY = (1 + 3) * SIZE_VECTOR
    SIZE_DATA = 2 * SIZE_GEOMETRY

    def __init__(self):
        self.origin = [0.0, 0.0, 0.0]
        self.rotation_matrix = [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        ]

    def set_from_mem_data(self, data):
        self.origin = self._read_vector(
            data[0 * self.SIZE_VECTOR:1 * self.SIZE_VECTOR])
        self.rotation_matrix = [
            self._read_vector(data[1 * self.SIZE_VECTOR:2 * self.SIZE_VECTOR]),
            self._read_vector(data[2 * self.SIZE_VECTOR:3 * self.SIZE_VECTOR]),
            self._read_vector(data[3 * self.SIZE_VECTOR:4 * self.SIZE_VECTOR]),
        ]

    def add_mem_data(self, data):
        self._add_vector(data, self.origin)
        self._add_vector(data, self.rotation_matrix[0])
        self._add_vector(data, self.rotation_matrix[1])
        self._add_vector(data, self.rotation_matrix[2])

    def _add_vector(self, data, vector):
        data += struct.pack('<fff', vector[0], vector[1], vector[2])

    def _read_vector(self, data):
        x, y, z = struct.unpack('<fff', data)
        return [x, y, z]

    def dump(self):
        print('origin:', self.origin)
        print('rotation matrix: ', self.rotation_matrix)


class LighthouseMemory(MemoryElement):
    """
    Memory interface for lighthouse configuration data
    """

    def __init__(self, id, type, size, mem_handler):
        """Initialize Lighthouse memory"""
        super(LighthouseMemory, self).__init__(id=id, type=type, size=size,
                                               mem_handler=mem_handler)

        self._update_finished_cb = None
        self._write_finished_cb = None

        # Geometry data for two base stations
        self.geometry_data = [
            LighthouseBsGeometry(),
            LighthouseBsGeometry(),
        ]

    def new_data(self, mem, addr, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            if addr == 0:
                self.geometry_data[0].set_from_mem_data(
                    data[0:LighthouseBsGeometry.SIZE_GEOMETRY])
                self.geometry_data[1].set_from_mem_data(
                    data[LighthouseBsGeometry.SIZE_GEOMETRY:])

                if self._update_finished_cb:
                    self._update_finished_cb(self)
                    self._update_finished_cb = None

    def update(self, update_finished_cb):
        """Request an update of the memory content"""
        if not self._update_finished_cb:
            self._update_finished_cb = update_finished_cb
            logger.debug('Updating content of memory {}'.format(self.id))
            self.mem_handler.read(self, 0, LighthouseBsGeometry.SIZE_DATA)

    def write_data(self, write_finished_cb):
        """Write geometry data to the Crazyflie"""
        self._write_finished_cb = write_finished_cb
        data = bytearray()

        for bs in self.geometry_data:
            bs.add_mem_data(data)

        self.mem_handler.write(self, 0x00, data, flush_queue=True)

    def write_done(self, mem, addr):
        if self._write_finished_cb and mem.id == self.id:
            logger.debug('Write of geometry data done')
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None

    def disconnect(self):
        self._update_finished_cb = None
        self._write_finished_cb = None

    def dump(self):
        for data in self.geometry_data:
            data.dump()


class MemoryTester(MemoryElement):
    """
    Memory interface for testing the memory sub system, end to end.

    Usage
    1. To verify reading:
      * Call read_data()
      * Wait for the callback to be called
      * Verify that readValidationSucess is True

    2. To verify writing:
      * Set the parameter 'memTst.resetW' in the CF
      * call write_data()
      * Wait for the callback
      * Read the log var 'memTst.errCntW' from the CF and validate that it
        is 0
    """

    def __init__(self, id, type, size, mem_handler):
        """Initialize Memory tester"""
        super(MemoryTester, self).__init__(id=id, type=type, size=size,
                                           mem_handler=mem_handler)

        self._update_finished_cb = None
        self._write_finished_cb = None

        self.readValidationSucess = True

    def new_data(self, mem, start_address, data):
        """Callback for when new memory data has been fetched"""
        if mem.id == self.id:
            for i in range(len(data)):
                actualValue = struct.unpack('<B', data[i:i + 1])[0]
                expectedValue = (start_address + i) & 0xff

                if (actualValue != expectedValue):
                    address = start_address + i
                    self.readValidationSucess = False
                    logger.error(
                        'Error in data - expected: {}, actual: {}, address:{}',
                        expectedValue, actualValue, address)

                if self._update_finished_cb:
                    self._update_finished_cb(self)
                    self._update_finished_cb = None

    def read_data(self, start_address, size, update_finished_cb):
        """Request an update of the memory content"""
        if not self._update_finished_cb:
            self._update_finished_cb = update_finished_cb
            logger.debug('Reading memory {}'.format(self.id))
            self.mem_handler.read(self, start_address, size)

    def write_data(self, start_address, size, write_finished_cb):
        """Write data to the Crazyflie"""
        self._write_finished_cb = write_finished_cb
        data = bytearray()

        for i in range(size):
            value = (start_address + i) & 0xff
            data += struct.pack('<B', value)

        self.mem_handler.write(self, start_address, data, flush_queue=True)

    def write_done(self, mem, addr):
        if self._write_finished_cb and mem.id == self.id:
            logger.debug('Write of data finished')
            self._write_finished_cb(self, addr)
            self._write_finished_cb = None

    def disconnect(self):
        self._update_finished_cb = None
        self._write_finished_cb = None


class _ReadRequest:
    """
    Class used to handle memory reads that will split up the read in multiple
    packets if necessary
    """
    MAX_DATA_LENGTH = 20

    def __init__(self, mem, addr, length, cf):
        """Initialize the object with good defaults"""
        self.mem = mem
        self.addr = addr
        self._bytes_left = length
        self.data = bytearray()
        self.cf = cf

        self._current_addr = addr

    def start(self):
        """Start the fetching of the data"""
        self._request_new_chunk()

    def resend(self):
        logger.debug('Sending write again...')
        self._request_new_chunk()

    def _request_new_chunk(self):
        """
        Called to request a new chunk of data to be read from the Crazyflie
        """
        # Figure out the length of the next request
        new_len = self._bytes_left
        if new_len > _ReadRequest.MAX_DATA_LENGTH:
            new_len = _ReadRequest.MAX_DATA_LENGTH

        logger.debug('Requesting new chunk of {}bytes at 0x{:X}'.format(
            new_len, self._current_addr))

        # Request the data for the next address
        pk = CRTPPacket()
        pk.set_header(CRTPPort.MEM, CHAN_READ)
        pk.data = struct.pack('<BIB', self.mem.id, self._current_addr, new_len)
        reply = struct.unpack('<BBBBB', pk.data[:-1])
        self.cf.send_packet(pk, expected_reply=reply, timeout=1)

    def add_data(self, addr, data):
        """Callback when data is received from the Crazyflie"""
        data_len = len(data)
        if not addr == self._current_addr:
            logger.warning(
                'Address did not match when adding data to read request!')
            return

        # Add the data and calculate the next address to fetch
        self.data += data
        self._bytes_left -= data_len
        self._current_addr += data_len

        if self._bytes_left > 0:
            self._request_new_chunk()
            return False
        else:
            return True


class _WriteRequest:
    """
    Class used to handle memory reads that will split up the read in multiple
    packets in necessary
    """
    MAX_DATA_LENGTH = 25

    def __init__(self, mem, addr, data, cf):
        """Initialize the object with good defaults"""
        self.mem = mem
        self.addr = addr
        self._bytes_left = len(data)
        self._data = data
        self.data = bytearray()
        self.cf = cf

        self._current_addr = addr

        self._sent_packet = None
        self._sent_reply = None

        self._addr_add = 0

    def start(self):
        """Start the fetching of the data"""
        self._write_new_chunk()

    def resend(self):
        logger.debug('Sending write again...')
        self.cf.send_packet(
            self._sent_packet, expected_reply=self._sent_reply, timeout=1)

    def _write_new_chunk(self):
        """
        Called to request a new chunk of data to be read from the Crazyflie
        """
        # Figure out the length of the next request
        new_len = len(self._data)
        if new_len > _WriteRequest.MAX_DATA_LENGTH:
            new_len = _WriteRequest.MAX_DATA_LENGTH

        logger.debug('Writing new chunk of {}bytes at 0x{:X}'.format(
            new_len, self._current_addr))

        data = self._data[:new_len]
        self._data = self._data[new_len:]

        pk = CRTPPacket()
        pk.set_header(CRTPPort.MEM, CHAN_WRITE)
        pk.data = struct.pack('<BI', self.mem.id, self._current_addr)
        # Create a tuple used for matching the reply using id and address
        reply = struct.unpack('<BBBBB', pk.data)
        self._sent_reply = reply
        # Add the data
        pk.data += struct.pack('B' * len(data), *data)
        self._sent_packet = pk
        self.cf.send_packet(pk, expected_reply=reply, timeout=1)

        self._addr_add = len(data)

    def write_done(self, addr):
        """Callback when data is received from the Crazyflie"""
        if not addr == self._current_addr:
            logger.warning(
                'Address did not match when adding data to read request!')
            return

        if len(self._data) > 0:
            self._current_addr += self._addr_add
            self._write_new_chunk()
            return False
        else:
            logger.debug('This write request is done')
            return True


class Memory():
    """Access memories on the Crazyflie"""

    # These codes can be decoded using os.stderror, but
    # some of the text messages will look very strange
    # in the UI, so they are redefined here
    _err_codes = {
        errno.ENOMEM: 'No more memory available',
        errno.ENOEXEC: 'Command not found',
        errno.ENOENT: 'No such block id',
        errno.E2BIG: 'Block too large',
        errno.EEXIST: 'Block already exists'
    }

    def __init__(self, crazyflie=None):
        """Instantiate class and connect callbacks"""
        # Called when new memories have been added
        self.mem_added_cb = Caller()
        # Called when new data has been read
        self.mem_read_cb = Caller()

        self.mem_write_cb = Caller()

        self.cf = crazyflie
        self.cf.add_port_callback(CRTPPort.MEM, self._new_packet_cb)
        self.cf.disconnected.add_callback(self._disconnected)
        self._write_requests_lock = Lock()

        self._clear_state()

    def _clear_state(self):
        self.mems = []
        self._refresh_callback = None
        self._fetch_id = 0
        self.nbr_of_mems = 0
        self._ow_mem_fetch_index = 0
        self._elem_data = ()
        self._read_requests = {}
        self._write_requests = {}
        self._ow_mems_left_to_update = []
        self._getting_count = False

    def _mem_update_done(self, mem):
        """
        Callback from each individual memory (only 1-wire) when reading of
        header/elements are done
        """
        if mem.id in self._ow_mems_left_to_update:
            self._ow_mems_left_to_update.remove(mem.id)

        logger.debug(mem)

        if len(self._ow_mems_left_to_update) == 0:
            if self._refresh_callback:
                self._refresh_callback()
                self._refresh_callback = None

    def get_mem(self, id):
        """Fetch the memory with the supplied id"""
        for m in self.mems:
            if m.id == id:
                return m

        return None

    def get_mems(self, type):
        """Fetch all the memories of the supplied type"""
        ret = ()
        for m in self.mems:
            if m.type == type:
                ret += (m,)

        return ret

    def ow_search(self, vid=0xBC, pid=None, name=None):
        """Search for specific memory id/name and return it"""
        for m in self.get_mems(MemoryElement.TYPE_1W):
            if pid and m.pid == pid or name and m.name == name:
                return m

        return None

    def write(self, memory, addr, data, flush_queue=False):
        """Write the specified data to the given memory at the given address"""
        wreq = _WriteRequest(memory, addr, data, self.cf)
        if memory.id not in self._write_requests:
            self._write_requests[memory.id] = []

        # Workaround until we secure the uplink and change messages for
        # mems to non-blocking
        self._write_requests_lock.acquire()
        if flush_queue:
            self._write_requests[memory.id] = self._write_requests[
                memory.id][:1]
        self._write_requests[memory.id].insert(len(self._write_requests), wreq)
        if len(self._write_requests[memory.id]) == 1:
            wreq.start()
        self._write_requests_lock.release()

        return True

    def read(self, memory, addr, length):
        """
        Read the specified amount of bytes from the given memory at the given
        address
        """
        if memory.id in self._read_requests:
            logger.warning('There is already a read operation ongoing for '
                           'memory id {}'.format(memory.id))
            return False

        rreq = _ReadRequest(memory, addr, length, self.cf)
        self._read_requests[memory.id] = rreq

        rreq.start()

        return True

    def refresh(self, refresh_done_callback):
        """Start fetching all the detected memories"""
        self._refresh_callback = refresh_done_callback
        self._fetch_id = 0
        for m in self.mems:
            try:
                self.mem_read_cb.remove_callback(m.new_data)
                m.disconnect()
            except Exception as e:
                logger.info(
                    'Error when removing memory after update: {}'.format(e))
        self.mems = []

        self.nbr_of_mems = 0
        self._getting_count = False

        logger.debug('Requesting number of memories')
        pk = CRTPPacket()
        pk.set_header(CRTPPort.MEM, CHAN_INFO)
        pk.data = (CMD_INFO_NBR,)
        self.cf.send_packet(pk, expected_reply=(CMD_INFO_NBR,))

    def _disconnected(self, uri):
        """The link to the Crazyflie has been broken. Reset state"""
        self._clear_state()

    def _new_packet_cb(self, packet):
        """Callback for newly arrived packets for the memory port"""
        chan = packet.channel
        cmd = packet.data[0]
        payload = packet.data[1:]

        if chan == CHAN_INFO:
            if cmd == CMD_INFO_NBR:
                self.nbr_of_mems = payload[0]
                logger.info('{} memories found'.format(self.nbr_of_mems))

                # Start requesting information about the memories,
                # if there are any...
                if self.nbr_of_mems > 0:
                    if not self._getting_count:
                        self._getting_count = True
                        logger.debug('Requesting first id')
                        pk = CRTPPacket()
                        pk.set_header(CRTPPort.MEM, CHAN_INFO)
                        pk.data = (CMD_INFO_DETAILS, 0)
                        self.cf.send_packet(pk, expected_reply=(
                            CMD_INFO_DETAILS, 0))
                else:
                    self._refresh_callback()

            if cmd == CMD_INFO_DETAILS:

                # Did we get a good reply, otherwise try again:
                if len(payload) < 5:
                    # Workaround for 1-wire bug when memory is detected
                    # but updating the info crashes the communication with
                    # the 1-wire. Fail by saying we only found 1 memory
                    # (the I2C).
                    logger.error(
                        '-------->Got good count, but no info on mem!')
                    self.nbr_of_mems = 1
                    if self._refresh_callback:
                        self._refresh_callback()
                        self._refresh_callback = None
                    return

                # Create information about a new memory
                # Id - 1 byte
                mem_id = payload[0]
                # Type - 1 byte
                mem_type = payload[1]
                # Size 4 bytes (as addr)
                mem_size = struct.unpack('I', payload[2:6])[0]
                # Addr (only valid for 1-wire?)
                mem_addr_raw = struct.unpack('B' * 8, payload[6:14])
                mem_addr = ''
                for m in mem_addr_raw:
                    mem_addr += '{:02X}'.format(m)

                if (not self.get_mem(mem_id)):
                    if mem_type == MemoryElement.TYPE_1W:
                        mem = OWElement(id=mem_id, type=mem_type,
                                        size=mem_size,
                                        addr=mem_addr, mem_handler=self)
                        self.mem_read_cb.add_callback(mem.new_data)
                        self.mem_write_cb.add_callback(mem.write_done)
                        self._ow_mems_left_to_update.append(mem.id)
                    elif mem_type == MemoryElement.TYPE_I2C:
                        mem = I2CElement(id=mem_id, type=mem_type,
                                         size=mem_size,
                                         mem_handler=self)
                        self.mem_read_cb.add_callback(mem.new_data)
                        self.mem_write_cb.add_callback(mem.write_done)
                    elif mem_type == MemoryElement.TYPE_DRIVER_LED:
                        mem = LEDDriverMemory(id=mem_id, type=mem_type,
                                              size=mem_size, mem_handler=self)
                        logger.debug(mem)
                        self.mem_read_cb.add_callback(mem.new_data)
                        self.mem_write_cb.add_callback(mem.write_done)
                    elif mem_type == MemoryElement.TYPE_LOCO:
                        mem = LocoMemory(id=mem_id, type=mem_type,
                                         size=mem_size, mem_handler=self)
                        logger.debug(mem)
                        self.mem_read_cb.add_callback(mem.new_data)
                    elif mem_type == MemoryElement.TYPE_TRAJ:
                        mem = TrajectoryMemory(id=mem_id, type=mem_type,
                                               size=mem_size, mem_handler=self)
                        logger.debug(mem)
                        self.mem_write_cb.add_callback(mem.write_done)
                    elif mem_type == MemoryElement.TYPE_LOCO2:
                        mem = LocoMemory2(id=mem_id, type=mem_type,
                                          size=mem_size, mem_handler=self)
                        logger.debug(mem)
                        self.mem_read_cb.add_callback(mem.new_data)
                    elif mem_type == MemoryElement.TYPE_LH:
                        mem = LighthouseMemory(id=mem_id, type=mem_type,
                                               size=mem_size, mem_handler=self)
                        logger.debug(mem)
                        self.mem_read_cb.add_callback(mem.new_data)
                        self.mem_write_cb.add_callback(mem.write_done)
                    elif mem_type == MemoryElement.TYPE_MEMORY_TESTER:
                        mem = MemoryTester(id=mem_id, type=mem_type,
                                           size=mem_size, mem_handler=self)
                        logger.debug(mem)
                        self.mem_read_cb.add_callback(mem.new_data)
                        self.mem_write_cb.add_callback(mem.write_done)
                    elif mem_type == MemoryElement.TYPE_DRIVER_LEDTIMING:
                        mem = LEDTimingsDriverMemory(id=mem_id, type=mem_type,
                                                     size=mem_size,
                                                     mem_handler=self)
                        logger.debug(mem)
                        self.mem_read_cb.add_callback(mem.new_data)
                        self.mem_write_cb.add_callback(mem.write_done)
                    else:
                        mem = MemoryElement(id=mem_id, type=mem_type,
                                            size=mem_size, mem_handler=self)
                        logger.debug(mem)
                    self.mems.append(mem)
                    self.mem_added_cb.call(mem)

                    self._fetch_id = mem_id + 1

                if self.nbr_of_mems - 1 >= self._fetch_id:
                    logger.debug(
                        'Requesting information about memory {}'.format(
                            self._fetch_id))
                    pk = CRTPPacket()
                    pk.set_header(CRTPPort.MEM, CHAN_INFO)
                    pk.data = (CMD_INFO_DETAILS, self._fetch_id)
                    self.cf.send_packet(pk, expected_reply=(
                        CMD_INFO_DETAILS, self._fetch_id))
                else:
                    logger.debug(
                        'Done getting all the memories, start reading the OWs')
                    ows = self.get_mems(MemoryElement.TYPE_1W)
                    # If there are any OW mems start reading them, otherwise
                    # we are done
                    for ow_mem in ows:
                        ow_mem.update(self._mem_update_done)
                    if len(ows) == 0:
                        if self._refresh_callback:
                            self._refresh_callback()
                            self._refresh_callback = None

        if chan == CHAN_WRITE:
            id = cmd
            (addr, status) = struct.unpack('<IB', payload[0:5])
            logger.debug(
                'WRITE: Mem={}, addr=0x{:X}, status=0x{}'.format(
                    id, addr, status))
            # Find the read request
            if id in self._write_requests:
                self._write_requests_lock.acquire()
                wreq = self._write_requests[id][0]
                if status == 0:
                    if wreq.write_done(addr):
                        # self._write_requests.pop(id, None)
                        # Remove the first item
                        self._write_requests[id].pop(0)
                        self.mem_write_cb.call(wreq.mem, wreq.addr)

                        # Get a new one to start (if there are any)
                        if len(self._write_requests[id]) > 0:
                            self._write_requests[id][0].start()
                else:
                    logger.debug(
                        'Status {}: write resending...'.format(status))
                    wreq.resend()
                self._write_requests_lock.release()

        if chan == CHAN_READ:
            id = cmd
            (addr, status) = struct.unpack('<IB', payload[0:5])
            data = struct.unpack('B' * len(payload[5:]), payload[5:])
            logger.debug('READ: Mem={}, addr=0x{:X}, status=0x{}, '
                         'data={}'.format(id, addr, status, data))
            # Find the read request
            if id in self._read_requests:
                logger.debug(
                    'READING: We are still interested in request for '
                    'mem {}'.format(id))
                rreq = self._read_requests[id]
                if status == 0:
                    if rreq.add_data(addr, payload[5:]):
                        self._read_requests.pop(id, None)
                        self.mem_read_cb.call(rreq.mem, rreq.addr, rreq.data)
                else:
                    logger.debug('Status {}: resending...'.format(status))
                    rreq.resend()
