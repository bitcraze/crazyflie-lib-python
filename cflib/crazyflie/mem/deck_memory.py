# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2021 Bitcraze AB
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import logging
import struct

from .memory_element import MemoryElement
from cflib.utils.callbacks import Syncer

logger = logging.getLogger(__name__)


class DeckMemory:
    """
    This class represents the memory in one deck. It is used
    to read and write to the deck memory.
    """

    MASK_IS_VALID = 1
    MASK_IS_STARTED = 2
    MASK_SUPPORTS_READ = 4
    MASK_SUPPORTS_WRITE = 8
    MASK_SUPPORTS_UPGRADE = 16
    MASK_UPGRADE_REQUIRED = 32
    MASK_BOOTLOADER_ACTIVE = 64

    MASK_SUPPORTS_RESET_TO_FW = 1
    MASK_SUPPORTS_RESET_TO_BOOTLOADER = 2

    FLAG_COMMAND_RESET_TO_FW = 1
    FLAG_COMMAND_RESET_TO_BOOTLOADER = 2

    MEMORY_MAX_SIZE = 0x10000000

    ADR_FW_NEW_FLASH = 0
    ADR_COMMAND_BIT_FIELD = 4

    def __init__(self, deck_memory_manager: 'DeckMemoryManager', _command_base_address):
        self._deck_memory_manager = deck_memory_manager
        self.required_hash = None
        self.required_length = None
        self.name = None

        self._base_address = None
        self._command_base_address = _command_base_address
        self._bit_field1 = 0
        self._bit_field2 = 0

    def contains(self, address):
        max = self._base_address + self.MEMORY_MAX_SIZE
        return address >= self._base_address and address < max

    def write(self, address, data, write_complete_cb, write_failed_cb=None, progress_cb=None):
        """Write a block of binary data to the deck"""
        if not self.supports_write:
            raise Exception('Deck does not support write operations')
        if not self.is_started:
            raise Exception('Deck not ready')

        self._deck_memory_manager._write(self._base_address, address, data,
                                         write_complete_cb, write_failed_cb, progress_cb)

    def write_sync(self, address, data, progress_cb=None):
        """Write a block of binary data to the deck, block until done"""
        syncer = Syncer()
        self.write(address, data, syncer.success_cb, write_failed_cb=syncer.failure_cb, progress_cb=progress_cb)
        syncer.wait()
        return syncer.is_success

    def read(self, address, length, read_complete_cb, read_failed_cb=None):
        """Read a block of data from a deck"""
        if not self.supports_read:
            raise Exception('Deck does not support read operations')
        if not self.is_started:
            raise Exception('Deck not ready')

        self._deck_memory_manager._read(self._base_address, address, length, read_complete_cb, read_failed_cb)

    def read_sync(self, address, length):
        """Read a block of data from a deck, block until done"""
        syncer = Syncer()
        self.read(address, length, syncer.success_cb, read_failed_cb=syncer.failure_cb)
        syncer.wait()
        if syncer.is_success:
            return syncer.success_args[1]
        else:
            return None

    @property
    def is_valid(self):
        return (self._bit_field1 & self.MASK_IS_VALID) != 0

    @property
    def is_started(self):
        return (self._bit_field1 & self.MASK_IS_STARTED) != 0

    @property
    def supports_read(self):
        return (self._bit_field1 & self.MASK_SUPPORTS_READ) != 0

    @property
    def supports_write(self):
        return (self._bit_field1 & self.MASK_SUPPORTS_WRITE) != 0

    @property
    def supports_fw_upgrade(self):
        return (self._bit_field1 & self.MASK_SUPPORTS_UPGRADE) != 0

    @property
    def is_fw_upgrade_required(self):
        return (self._bit_field1 & self.MASK_UPGRADE_REQUIRED) != 0

    @property
    def is_bootloader_active(self):
        return (self._bit_field1 & self.MASK_BOOTLOADER_ACTIVE) != 0

    @property
    def supports_reset_to_fw(self):
        return (self._bit_field2 & self.MASK_SUPPORTS_RESET_TO_FW) != 0

    @property
    def supports_reset_to_bootloader(self):
        return (self._bit_field2 & self.MASK_SUPPORTS_RESET_TO_BOOTLOADER) != 0

    def reset_to_fw(self):
        data = struct.pack('<B', self.FLAG_COMMAND_RESET_TO_FW)
        self._write_command_data(self.ADR_COMMAND_BIT_FIELD, data)

    def reset_to_bootloader(self):
        data = struct.pack('<B', self.FLAG_COMMAND_RESET_TO_BOOTLOADER)
        self._write_command_data(self.ADR_COMMAND_BIT_FIELD, data)

    def set_fw_new_flash_size(self, size):
        data = struct.pack('<L', size)
        self._write_command_data(self.ADR_FW_NEW_FLASH, data)

    def _parse(self, data):
        self._bit_field1, self._bit_field2 = struct.unpack('<BB', data[0:2])
        if self.is_valid:
            try:
                self.required_hash, self.required_length, self._base_address, _name = struct.unpack('<LLL18s', data[2:])
                self.name = _name.split(b'\x00')[0].decode()
            except Exception as e:
                logger.warning(f'Error while decoding deck mem ({e}), skipping!')
                self._bit_field1 = 0
                self._bit_field2 = 0

    def _write_command_data(self, address, data):
        if not self.is_started:
            raise Exception('Deck not ready')

        syncer = Syncer()
        self._deck_memory_manager._write(self._command_base_address, address, data, syncer.success_cb,
                                         syncer.failure_cb, None)
        syncer.wait()
        return syncer.is_success


class DeckMemoryManager(MemoryElement):
    """
    Manager interface for deck memories. It is used to query
    for installed decks and get access to Deck Memory objects
    for the available decks.
    """

    MAX_NR_OF_DECKS = 4
    MAX_NR_OF_DECK_MEM_INFOS = MAX_NR_OF_DECKS * 2
    SIZE_OF_DECK_MEM_INFO = 0x20
    SIZE_OF_VERSION = 1
    SIZE_OF_INFO_SECTION = SIZE_OF_VERSION + MAX_NR_OF_DECK_MEM_INFOS * SIZE_OF_DECK_MEM_INFO
    INFO_SECTION_ADDRESS = 0
    COMMAND_SECTION_ADDRESS = 0x1000
    SIZE_OF_COMMAND_SECTION = 0x20
    SUPPORTED_VERSION = 3

    def __init__(self, id, type, size, mem_handler):
        """Initialize deck memory manager"""
        super(DeckMemoryManager, self).__init__(id=id, type=type, size=size, mem_handler=mem_handler)

        self._query_complete_cb = None
        self._query_failed_cb = None
        self.deck_memories = {}

        self._read_complete_cb = None
        self._read_failed_cb = None
        self._read_base_address = 0

        self._write_complete_cb = None
        self._write_failed_cb = None
        self._error = None

    def query_decks(self, query_complete_cb, query_failed_cb=None):
        if self._query_complete_cb is not None:
            raise Exception('Query ongoing')

        self._error = None
        self.deck_memories = {}
        self._query_complete_cb = query_complete_cb
        self._query_failed_cb = query_failed_cb
        self.mem_handler.read(self, self.INFO_SECTION_ADDRESS, self.SIZE_OF_INFO_SECTION)

    def _read(self, base_address, address, length, read_complete_cb, read_failed_cb):
        """Called from deck memory to read data"""
        if self._read_complete_cb is not None:
            raise Exception('Read operation ongoing')

        self._read_base_address = base_address
        self._read_complete_cb = read_complete_cb
        self._read_failed_cb = read_failed_cb

        mapped_address = address + self._read_base_address
        self.mem_handler.read(self, mapped_address, length)

    def _new_data(self, mem, addr, data):
        """Callback when new memory data has been fetched"""
        if mem.id == self.id:
            if addr == self.INFO_SECTION_ADDRESS:
                try:
                    self.deck_memories = self._parse_info_section(data)
                    tmp_cb = self._query_complete_cb
                    self._clear_query_cb()
                    tmp_cb(self.deck_memories)
                except RuntimeError as e:
                    tmp_cb = self._query_failed_cb
                    self._clear_query_cb()
                    if tmp_cb:
                        tmp_cb(str(e))
            else:
                tmp_cb = self._read_complete_cb
                self._clear_read_cb()
                tmp_cb(addr - self._read_base_address, data)

    def _new_data_failed(self, mem, addr, data):
        """Callback when a read failed"""
        if mem.id == self.id:
            if addr == self.INFO_SECTION_ADDRESS:
                self._clear_query_cb()
                logger.error('Deck memory query failed')
            else:
                tmp_cb = self._read_failed_cb
                self._clear_read_cb()
                if tmp_cb is not None:
                    tmp_cb(addr - self._read_base_address)
                else:
                    logger.error('Deck memory read failed, addr: {}'.format(addr))

    def _clear_query_cb(self):
        self._query_complete_cb = None
        self._query_failed_cb = None

    def _clear_read_cb(self):
        self._read_complete_cb = None
        self._read_failed_cb = None

    def _parse_info_section(self, data):
        result = {}

        version = struct.unpack('<B', data[0:1])[0]
        if version != self.SUPPORTED_VERSION:
            raise RuntimeError(f'Deck memory version {version} not supported')
        else:
            for i in range(self.MAX_NR_OF_DECK_MEM_INFOS):
                deck_memory = DeckMemory(self, self.COMMAND_SECTION_ADDRESS + i * self.SIZE_OF_COMMAND_SECTION)
                start = self.SIZE_OF_VERSION + self.SIZE_OF_DECK_MEM_INFO * i
                end = start + self.SIZE_OF_DECK_MEM_INFO
                deck_memory._parse(data[start:end])
                if deck_memory.is_valid:
                    result[i] = deck_memory

        return result

    def _write(self, base_address, address, data, complete_cb, failed_cb, progress_cb):
        """Called from deck memory to write data"""
        if self._write_complete_cb is not None:
            raise Exception('Write operation ongoing')

        self._write_complete_cb = complete_cb
        self._write_failed_cb = failed_cb

        mapped_address = address + base_address
        self.mem_handler.write(self, mapped_address, data, flush_queue=True, progress_cb=progress_cb)

    def _write_done(self, mem, addr):
        if mem.id == self.id:
            logger.debug('Write data done')

            tmp_cb = self._write_complete_cb
            self._clear_write_cb()
            tmp_cb(addr - self._read_base_address)

    def _write_failed(self, mem, addr):
        if mem.id == self.id:
            logger.debug('Write failed')

            tmp_cb = self._write_failed_cb
            self._clear_write_cb()
            tmp_cb(addr - self._read_base_address)

    def _clear_write_cb(self):
        self._write_complete_cb = None
        self._write_failed_cb = None

    def disconnect(self):
        self._clear_query_cb()
        self._clear_read_cb()
        self._clear_write_cb()
        self.deck_memories = {}


class SyncDeckMemoryManager:
    """A wrapper for the DeckMemoryManager class to make calls synchronous and avoid callbacks"""

    def __init__(self, deck_memory_manager):
        self._deck_memory_manager = deck_memory_manager

    def query_decks(self):
        syncer = Syncer()
        self._deck_memory_manager.query_decks(syncer.success_cb, syncer.failure_cb)
        syncer.wait()
        if syncer.is_success:
            return syncer.success_args[0]

        raise RuntimeError(syncer.failure_args[0])
