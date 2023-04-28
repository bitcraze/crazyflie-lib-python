#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2020 Bitcraze AB
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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
Enables access to the Crazyflie memory subsystem.

"""
import errno
import logging
import struct
from threading import Lock

from .deck_memory import DeckMemoryManager
from .i2c_element import I2CElement
from .led_driver_memory import LEDDriverMemory
from .led_timings_driver_memory import LEDTimingsDriverMemory
from .lighthouse_memory import LighthouseBsCalibration
from .lighthouse_memory import LighthouseBsGeometry
from .lighthouse_memory import LighthouseMemHelper
from .lighthouse_memory import LighthouseMemory
from .loco_memory import LocoMemory
from .loco_memory_2 import LocoMemory2
from .memory_element import MemoryElement
from .memory_tester import MemoryTester
from .multiranger_memory import MultirangerMemory
from .ow_element import OWElement
from .paa3905_memory import PAA3905Memory
from .trajectory_memory import CompressedSegment
from .trajectory_memory import CompressedStart
from .trajectory_memory import Poly4D
from .trajectory_memory import TrajectoryMemory
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.callbacks import Caller

__author__ = 'Bitcraze AB'
__all__ = ['Memory', 'Poly4D', 'CompressedStart', 'CompressedSegment', 'MemoryElement',
           'LighthouseBsGeometry', 'LighthouseBsCalibration', 'LighthouseMemHelper',
           'DeckMemoryManager']

# Channels used for the logging port
CHAN_INFO = 0
CHAN_READ = 1
CHAN_WRITE = 2

# Commands used when accessing the Settings port
CMD_INFO_VER = 0
CMD_INFO_NBR = 1
CMD_INFO_DETAILS = 2

logger = logging.getLogger(__name__)


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

    def __init__(self, mem, addr, data, cf, progress_cb=None):
        """Initialize the object with good defaults"""
        self.mem = mem
        self.addr = addr
        self._bytes_left = len(data)
        self._write_len = self._bytes_left
        self._data = data
        self.data = bytearray()
        self.cf = cf
        self._progress_cb = progress_cb
        self._progress = -1

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
        self._bytes_left -= self._addr_add

    def _get_progress_message(self):
        if isinstance(self.mem, DeckMemoryManager):
            for deck_memory in self.mem.deck_memories.values():
                if deck_memory.contains(self._current_addr):
                    return f'Writing to {deck_memory.name} deck memory'

        return 'Writing to memory'

    def write_done(self, addr):
        """Callback when data is received from the Crazyflie"""
        if not addr == self._current_addr:
            logger.warning(
                'Address did not match when adding data to read request!')
            return

        if self._progress_cb is not None:
            new_progress = int(100 * (self._write_len - self._bytes_left) / self._write_len)
            if new_progress > self._progress:
                self._progress = new_progress
                self._progress_cb(self._get_progress_message(), self._progress)

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
        self.cf = crazyflie
        self.cf.add_port_callback(CRTPPort.MEM, self._new_packet_cb)
        self.cf.disconnected.add_callback(self._disconnected)
        self._write_requests_lock = Lock()

        self._clear_state()

    def _clear_state(self):
        self.mems = []
        # Called when new memories have been added
        self.mem_added_cb = Caller()

        self._clear_refresh_callbacks()

        # Called to signal completion of read or write
        self.mem_read_cb = Caller()
        self.mem_read_failed_cb = Caller()
        self.mem_write_cb = Caller()
        self.mem_write_failed_cb = Caller()

        self._refresh_callback = None
        self._refresh_failed_callback = None
        self._fetch_id = 0
        self.nbr_of_mems = 0
        self._ow_mem_fetch_index = 0
        self._elem_data = ()
        self._read_requests = {}
        self._write_requests = {}
        self._ow_mems_left_to_update = []
        self._getting_count = False

    def _clear_refresh_callbacks(self):
        self._refresh_callback = None
        self._refresh_failed_callback = None

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
                self._clear_refresh_callbacks()

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

    def write(self, memory, addr, data, flush_queue=False, progress_cb=None):
        """Write the specified data to the given memory at the given address"""
        wreq = _WriteRequest(memory, addr, data, self.cf, progress_cb)
        if memory.id not in self._write_requests:
            self._write_requests[memory.id] = []

        # Workaround until we secure the uplink and change messages for
        # mems to non-blocking
        self._write_requests_lock.acquire()
        if flush_queue:
            self._write_requests[memory.id] = self._write_requests[
                memory.id][:1]
        self._write_requests[memory.id].append(wreq)
        if len(self._write_requests[memory.id]) == 1:
            wreq.start()
        self._write_requests_lock.release()

        return True

    def read(self, memory, addr, length):
        """
        Read the specified amount of bytes from the given memory at the given address
        """
        if memory.id in self._read_requests:
            logger.warning('There is already a read operation ongoing for memory id {}'.format(memory.id))
            return False

        rreq = _ReadRequest(memory, addr, length, self.cf)
        self._read_requests[memory.id] = rreq

        rreq.start()

        return True

    def refresh(self, refresh_done_callback, refresh_failed_cb=None):
        """Start fetching all the detected memories"""
        self._refresh_callback = refresh_done_callback
        self._refresh_failed_callback = refresh_failed_cb
        self._fetch_id = 0
        for m in self.mems:
            try:
                self.mem_read_cb.remove_callback(m.new_data)
                m.disconnect()
            except Exception as e:
                logger.info('Error when removing memory after update: {}'.format(e))
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
        self._call_all_failed_callbacks()
        self._clear_state()

    def _call_all_failed_callbacks(self):
        # Read requests
        read_requests = list(self._read_requests.values())
        self._read_requests.clear()
        for rreq in read_requests:
            self.mem_read_failed_cb.call(rreq.mem, rreq.addr, rreq.data)

        # Write requests
        write_requests = []
        self._write_requests_lock.acquire()
        for requests in self._write_requests.values():
            write_requests += requests
        self._write_requests.clear()
        self._write_requests_lock.release()

        for wreq in write_requests:
            self.mem_write_failed_cb.call(wreq.mem, wreq.addr)

        # Info
        if self._refresh_failed_callback:
            self._refresh_failed_callback()
            self._clear_refresh_callbacks()

    def _new_packet_cb(self, packet):
        """Callback for newly arrived packets for the memory port"""
        chan = packet.channel
        cmd = packet.data[0]
        payload = packet.data[1:]

        if chan == CHAN_INFO:
            self._handle_chan_info(cmd, payload)
        if chan == CHAN_WRITE:
            self._handle_chan_write(cmd, payload)
        if chan == CHAN_READ:
            self._handle_chan_read(cmd, payload)

    def _handle_chan_info(self, cmd, payload):
        if cmd == CMD_INFO_NBR:
            self._handle_cmd_info_nbr(payload)
        if cmd == CMD_INFO_DETAILS:
            self._handle_cmd_info_details(payload)

    def _handle_cmd_info_nbr(self, payload):
        self.nbr_of_mems = payload[0]
        logger.info('{} memories found'.format(self.nbr_of_mems))

        # Start requesting information about the memories,
        if self.nbr_of_mems > 0:
            if not self._getting_count:
                self._getting_count = True
                logger.debug('Requesting first id')
                pk = CRTPPacket()
                pk.set_header(CRTPPort.MEM, CHAN_INFO)
                pk.data = (CMD_INFO_DETAILS, 0)
                self.cf.send_packet(pk, expected_reply=(CMD_INFO_DETAILS, 0))
        else:
            if self._refresh_callback:
                self._refresh_callback()
                self._clear_refresh_callbacks()

    def _handle_cmd_info_details(self, payload):
        # Did we get a good reply, otherwise try again:
        if len(payload) < 5:
            # Workaround for 1-wire bug when memory is detected
            # but updating the info crashes the communication with
            # the 1-wire. Fail by saying we only found 1 memory
            # (the I2C).
            logger.error('-------->Got good count, but no info on mem!')
            self.nbr_of_mems = 1
            if self._refresh_callback:
                self._refresh_callback()
                self._clear_refresh_callbacks()
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
                mem = I2CElement(id=mem_id, type=mem_type, size=mem_size, mem_handler=self)
                self.mem_read_cb.add_callback(mem.new_data)
                self.mem_write_cb.add_callback(mem.write_done)
            elif mem_type == MemoryElement.TYPE_DRIVER_LED:
                mem = LEDDriverMemory(id=mem_id, type=mem_type, size=mem_size, mem_handler=self)
                logger.debug(mem)
                self.mem_read_cb.add_callback(mem.new_data)
                self.mem_write_cb.add_callback(mem.write_done)
            elif mem_type == MemoryElement.TYPE_LOCO:
                mem = LocoMemory(id=mem_id, type=mem_type, size=mem_size, mem_handler=self)
                logger.debug(mem)
                self.mem_read_cb.add_callback(mem.new_data)
            elif mem_type == MemoryElement.TYPE_TRAJ:
                mem = TrajectoryMemory(id=mem_id, type=mem_type, size=mem_size, mem_handler=self)
                logger.debug(mem)
                self.mem_write_cb.add_callback(mem.write_done)
                self.mem_write_failed_cb.add_callback(mem.write_failed)
            elif mem_type == MemoryElement.TYPE_LOCO2:
                mem = LocoMemory2(id=mem_id, type=mem_type, size=mem_size, mem_handler=self)
                logger.debug(mem)
                self.mem_read_cb.add_callback(mem.new_data)
            elif mem_type == MemoryElement.TYPE_LH:
                mem = LighthouseMemory(id=mem_id, type=mem_type, size=mem_size, mem_handler=self)
                logger.debug(mem)
                self.mem_read_cb.add_callback(mem.new_data)
                self.mem_read_failed_cb.add_callback(mem.new_data_failed)
                self.mem_write_cb.add_callback(mem.write_done)
                self.mem_write_failed_cb.add_callback(mem.write_failed)
            elif mem_type == MemoryElement.TYPE_MEMORY_TESTER:
                mem = MemoryTester(id=mem_id, type=mem_type, size=mem_size, mem_handler=self)
                logger.debug(mem)
                self.mem_read_cb.add_callback(mem.new_data)
                self.mem_write_cb.add_callback(mem.write_done)
            elif mem_type == MemoryElement.TYPE_DRIVER_LEDTIMING:
                mem = LEDTimingsDriverMemory(id=mem_id, type=mem_type, size=mem_size, mem_handler=self)
                logger.debug(mem)
                self.mem_read_cb.add_callback(mem.new_data)
                self.mem_write_cb.add_callback(mem.write_done)
            elif mem_type == MemoryElement.TYPE_DECK_MEMORY:
                mem = DeckMemoryManager(id=mem_id, type=mem_type, size=mem_size, mem_handler=self)
                logger.debug(mem)
                self.mem_read_cb.add_callback(mem._new_data)
                self.mem_read_failed_cb.add_callback(mem._new_data_failed)
                self.mem_write_cb.add_callback(mem._write_done)
                self.mem_write_failed_cb.add_callback(mem._write_failed)
            elif mem_type == MemoryElement.TYPE_DECK_MULTIRANGER:
                mem = MultirangerMemory(id=mem_id, type=mem_type, size=mem_size, mem_handler=self)
                logger.debug(mem)
                self.mem_read_cb.add_callback(mem.new_data)
                self.mem_read_failed_cb.add_callback(mem.read_failed)
            elif mem_type == MemoryElement.TYPE_DECK_PAA3905:
                mem = PAA3905Memory(id=mem_id, type=mem_type, size=mem_size, mem_handler=self)
                logger.debug(mem)
                self.mem_read_cb.add_callback(mem.new_data)
                self.mem_read_failed_cb.add_callback(mem.read_failed)
            else:
                mem = MemoryElement(id=mem_id, type=mem_type, size=mem_size, mem_handler=self)
                logger.debug(mem)
            self.mems.append(mem)
            self.mem_added_cb.call(mem)

            self._fetch_id = mem_id + 1

        if self.nbr_of_mems - 1 >= self._fetch_id:
            logger.debug('Requesting information about memory {}'.format(self._fetch_id))
            pk = CRTPPacket()
            pk.set_header(CRTPPort.MEM, CHAN_INFO)
            pk.data = (CMD_INFO_DETAILS, self._fetch_id)
            self.cf.send_packet(pk, expected_reply=(CMD_INFO_DETAILS, self._fetch_id))
        else:
            logger.debug('Done getting all the memories, start reading the OWs')
            ows = self.get_mems(MemoryElement.TYPE_1W)
            # If there are any OW mems start reading them, otherwise
            # we are done
            for ow_mem in ows:
                ow_mem.update(self._mem_update_done)
            if len(ows) == 0:
                if self._refresh_callback:
                    self._refresh_callback()
                    self._clear_refresh_callbacks()

    def _handle_chan_write(self, cmd, payload):
        id = cmd
        (addr, status) = struct.unpack('<IB', payload[0:5])
        logger.debug('WRITE: Mem={}, addr=0x{:X}, status=0x{}'.format(id, addr, status))
        # Find the write request
        if id in self._write_requests:
            self._write_requests_lock.acquire()
            do_call_sucess_cb = False
            do_call_fail_cb = False
            wreq = self._write_requests[id][0]
            if status == 0:
                if wreq.write_done(addr):
                    # self._write_requests.pop(id, None)
                    # Remove the first item
                    self._write_requests[id].pop(0)
                    do_call_sucess_cb = True

                    # Get a new one to start (if there are any)
                    if len(self._write_requests[id]) > 0:
                        self._write_requests[id][0].start()
            else:
                logger.debug('Status {}: write failed.'.format(status))
                # Remove from queue
                self._write_requests[id].pop(0)
                do_call_fail_cb = True

                # Get a new one to start (if there are any)
                if len(self._write_requests[id]) > 0:
                    self._write_requests[id][0].start()

            self._write_requests_lock.release()

            # Call callbacks after the lock has been released to alow for new writes
            # to be initiated from the callback.
            if do_call_sucess_cb:
                self.mem_write_cb.call(wreq.mem, wreq.addr)
            if do_call_fail_cb:
                self.mem_write_failed_cb.call(wreq.mem, wreq.addr)

    def _handle_chan_read(self, cmd, payload):
        id = cmd
        (addr, status) = struct.unpack('<IB', payload[0:5])
        data = struct.unpack('B' * len(payload[5:]), payload[5:])
        logger.debug('READ: Mem={}, addr=0x{:X}, status=0x{}, data={}'.format(id, addr, status, data))
        # Find the read request
        if id in self._read_requests:
            logger.debug('READING: We are still interested in request for mem {}'.format(id))
            rreq = self._read_requests[id]
            if status == 0:
                if rreq.add_data(addr, payload[5:]):
                    self._read_requests.pop(id, None)
                    self.mem_read_cb.call(rreq.mem, rreq.addr, rreq.data)
            else:
                logger.debug('Status {}: read failed.'.format(status))
                self._read_requests.pop(id, None)
                self.mem_read_failed_cb.call(rreq.mem, rreq.addr, rreq.data)
