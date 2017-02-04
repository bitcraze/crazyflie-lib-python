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
Enables logging of variables from the Crazyflie.

When a Crazyflie is connected it's possible to download a TableOfContent of all
the variables that can be logged. Using this it's possible to add logging
configurations where selected variables are sent to the client at a
specified period.

Terminology:
  Log configuration - A configuration with a period and a number of variables
                      that are present in the TOC.
  Stored as         - The size and type of the variable as declared in the
                      Crazyflie firmware
  Fetch as          - The size and type that a variable should be fetched as.
                      This does not have to be the same as the size and type
                      it's stored as.

States of a configuration:
  Created on host - When a configuration is created the contents is checked
                    so that all the variables are present in the TOC. If not
                    then the configuration cannot be created.
  Created on CF   - When the configuration is deemed valid it is added to the
                    Crazyflie. At this time the memory constraint is checked
                    and the status returned.
  Started on CF   - Any added block that is not started can be started. Once
                    started the Crazyflie will send back logdata periodically
                    according to the specified period when it's created.
  Stopped on CF   - Any started configuration can be stopped. The memory taken
                    by the configuration on the Crazyflie is NOT freed, the
                    only effect is that the Crazyflie will stop sending
                    logdata back to the host.
  Deleted on CF   - Any block that is added can be deleted. When this is done
                    the memory taken by the configuration is freed on the
                    Crazyflie. The configuration will have to be re-added to
                    be used again.
"""
import errno
import logging
import struct

from .toc import Toc
from .toc import TocFetcher
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.callbacks import Caller

__author__ = 'Bitcraze AB'
__all__ = ['Log', 'LogTocElement']

# Channels used for the logging port
CHAN_TOC = 0
CHAN_SETTINGS = 1
CHAN_LOGDATA = 2

# Commands used when accessing the Table of Contents
CMD_TOC_ELEMENT = 0
CMD_TOC_INFO = 1

# Commands used when accessing the Log configurations
CMD_CREATE_BLOCK = 0
CMD_APPEND_BLOCK = 1
CMD_DELETE_BLOCK = 2
CMD_START_LOGGING = 3
CMD_STOP_LOGGING = 4
CMD_RESET_LOGGING = 5

# Possible states when receiving TOC
IDLE = 'IDLE'
GET_TOC_INF = 'GET_TOC_INFO'
GET_TOC_ELEMENT = 'GET_TOC_ELEMENT'

# The max size of a CRTP packet payload
MAX_LOG_DATA_PACKET_SIZE = 30


logger = logging.getLogger(__name__)


class LogVariable():
    """A logging variable"""

    TOC_TYPE = 0
    MEM_TYPE = 1

    def __init__(self, name='', fetchAs='uint8_t', varType=TOC_TYPE,
                 storedAs='', address=0):
        self.name = name
        self.fetch_as = LogTocElement.get_id_from_cstring(fetchAs)
        if (len(storedAs) == 0):
            self.stored_as = self.fetch_as
        else:
            self.stored_as = LogTocElement.get_id_from_cstring(storedAs)
        self.address = address
        self.type = varType
        self.stored_as_string = storedAs
        self.fetch_as_string = fetchAs

    def is_toc_variable(self):
        """
        Return true if the variable should be in the TOC, false if raw memory
        variable
        """
        return self.type == LogVariable.TOC_TYPE

    def get_storage_and_fetch_byte(self):
        """Return what the variable is stored as and fetched as"""
        return (self.fetch_as | (self.stored_as << 4))

    def __str__(self):
        return ('LogVariable: name=%s, store=%s, fetch=%s' %
                (self.name, LogTocElement.get_cstring_from_id(self.stored_as),
                 LogTocElement.get_cstring_from_id(self.fetch_as)))


class LogConfig(object):
    """Representation of one log configuration that enables logging
    from the Crazyflie"""

    def __init__(self, name, period_in_ms):
        """Initialize the entry"""
        self.data_received_cb = Caller()
        self.error_cb = Caller()
        self.started_cb = Caller()
        self.added_cb = Caller()
        self.err_no = 0

        self.id = 0
        self.cf = None
        self.period = int(period_in_ms / 10)
        self.period_in_ms = period_in_ms
        self._added = False
        self._started = False
        self.valid = False
        self.variables = []
        self.default_fetch_as = []
        self.name = name

    def add_variable(self, name, fetch_as=None):
        """Add a new variable to the configuration.

        name - Complete name of the variable in the form group.name
        fetch_as - String representation of the type the variable should be
                   fetched as (i.e uint8_t, float, FP16, etc)

        If no fetch_as type is supplied, then the stored as type will be used
        (i.e the type of the fetched variable is the same as it's stored in the
        Crazyflie)."""
        if fetch_as:
            self.variables.append(LogVariable(name, fetch_as))
        else:
            # We cannot determine the default type until we have connected. So
            # save the name and we will add these once we are connected.
            self.default_fetch_as.append(name)

    def add_memory(self, name, fetch_as, stored_as, address):
        """Add a raw memory position to log.

        name - Arbitrary name of the variable
        fetch_as - String representation of the type of the data the memory
                   should be fetch as (i.e uint8_t, float, FP16)
        stored_as - String representation of the type the data is stored as
                    in the Crazyflie
        address - The address of the data
        """
        self.variables.append(LogVariable(name, fetch_as, LogVariable.MEM_TYPE,
                                          stored_as, address))

    def _set_added(self, added):
        if added != self._added:
            self.added_cb.call(self, added)
        self._added = added

    def _get_added(self):
        return self._added

    def _set_started(self, started):
        if started != self._started:
            self.started_cb.call(self, started)
        self._started = started

    def _get_started(self):
        return self._started

    added = property(_get_added, _set_added)
    started = property(_get_started, _set_started)

    def create(self):
        """Save the log configuration in the Crazyflie"""
        pk = CRTPPacket()
        pk.set_header(5, CHAN_SETTINGS)
        pk.data = (CMD_CREATE_BLOCK, self.id)
        for var in self.variables:
            if (var.is_toc_variable() is False):  # Memory location
                logger.debug('Logging to raw memory %d, 0x%04X',
                             var.get_storage_and_fetch_byte(), var.address)
                pk.data.append(struct.pack('<B',
                                           var.get_storage_and_fetch_byte()))
                pk.data.append(struct.pack('<I', var.address))
            else:  # Item in TOC
                logger.debug('Adding %s with id=%d and type=0x%02X',
                             var.name,
                             self.cf.log.toc.get_element_id(
                                 var.name), var.get_storage_and_fetch_byte())
                pk.data.append(var.get_storage_and_fetch_byte())
                pk.data.append(self.cf.log.toc.get_element_id(var.name))
        logger.debug('Adding log block id {}'.format(self.id))
        self.cf.send_packet(pk, expected_reply=(CMD_CREATE_BLOCK, self.id))

    def start(self):
        """Start the logging for this entry"""
        if (self.cf.link is not None):
            if (self._added is False):
                self.create()
                logger.debug('First time block is started, add block')
            else:
                logger.debug('Block already registered, starting logging'
                             ' for id=%d', self.id)
                pk = CRTPPacket()
                pk.set_header(5, CHAN_SETTINGS)
                pk.data = (CMD_START_LOGGING, self.id, self.period)
                self.cf.send_packet(pk, expected_reply=(
                    CMD_START_LOGGING, self.id))

    def stop(self):
        """Stop the logging for this entry"""
        if (self.cf.link is not None):
            if (self.id is None):
                logger.warning('Stopping block, but no block registered')
            else:
                logger.debug('Sending stop logging for block id=%d', self.id)
                pk = CRTPPacket()
                pk.set_header(5, CHAN_SETTINGS)
                pk.data = (CMD_STOP_LOGGING, self.id)
                self.cf.send_packet(
                    pk, expected_reply=(CMD_STOP_LOGGING, self.id))

    def delete(self):
        """Delete this entry in the Crazyflie"""
        if (self.cf.link is not None):
            if (self.id is None):
                logger.warning('Delete block, but no block registered')
            else:
                logger.debug('LogEntry: Sending delete logging for block id=%d'
                             % self.id)
                pk = CRTPPacket()
                pk.set_header(5, CHAN_SETTINGS)
                pk.data = (CMD_DELETE_BLOCK, self.id)
                self.cf.send_packet(
                    pk, expected_reply=(CMD_DELETE_BLOCK, self.id))

    def unpack_log_data(self, log_data, timestamp):
        """Unpack received logging data so it represent real values according
        to the configuration in the entry"""
        ret_data = {}
        data_index = 0
        for var in self.variables:
            size = LogTocElement.get_size_from_id(var.fetch_as)
            name = var.name
            unpackstring = LogTocElement.get_unpack_string_from_id(
                var.fetch_as)
            value = struct.unpack(
                unpackstring, log_data[data_index:data_index + size])[0]
            data_index += size
            ret_data[name] = value
        self.data_received_cb.call(timestamp, ret_data, self)


class LogTocElement:
    """An element in the Log TOC."""
    types = {0x01: ('uint8_t', '<B', 1),
             0x02: ('uint16_t', '<H', 2),
             0x03: ('uint32_t', '<L', 4),
             0x04: ('int8_t', '<b', 1),
             0x05: ('int16_t', '<h', 2),
             0x06: ('int32_t', '<i', 4),
             0x08: ('FP16', '<h', 2),
             0x07: ('float', '<f', 4)}

    @staticmethod
    def get_id_from_cstring(name):
        """Return variable type id given the C-storage name"""
        for key in list(LogTocElement.types.keys()):
            if (LogTocElement.types[key][0] == name):
                return key
        raise KeyError('Type [%s] not found in LogTocElement.types!' % name)

    @staticmethod
    def get_cstring_from_id(ident):
        """Return the C-storage name given the variable type id"""
        try:
            return LogTocElement.types[ident][0]
        except KeyError:
            raise KeyError('Type [%d] not found in LogTocElement.types'
                           '!' % ident)

    @staticmethod
    def get_size_from_id(ident):
        """Return the size in bytes given the variable type id"""
        try:
            return LogTocElement.types[ident][2]
        except KeyError:
            raise KeyError('Type [%d] not found in LogTocElement.types'
                           '!' % ident)

    @staticmethod
    def get_unpack_string_from_id(ident):
        """Return the Python unpack string given the variable type id"""
        try:
            return LogTocElement.types[ident][1]
        except KeyError:
            raise KeyError(
                'Type [%d] not found in LogTocElement.types!' % ident)

    def __init__(self, data=None):
        """TocElement creator. Data is the binary payload of the element."""

        if (data):
            naming = data[2:]
            zt = bytearray((0, ))
            self.group = naming[:naming.find(zt)].decode('ISO-8859-1')
            self.name = naming[naming.find(zt) + 1:-1].decode('ISO-8859-1')

            self.ident = data[0]

            self.ctype = LogTocElement.get_cstring_from_id(data[1])
            self.pytype = LogTocElement.get_unpack_string_from_id(data[1])

            self.access = data[1] & 0x10


class Log():
    """Create log configuration"""

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
        self.log_blocks = []
        # Called with newly created blocks
        self.block_added_cb = Caller()

        self.cf = crazyflie
        self.toc = None
        self.cf.add_port_callback(CRTPPort.LOGGING, self._new_packet_cb)

        self.toc_updated = Caller()
        self.state = IDLE
        self.fake_toc_crc = 0xDEADBEEF

        self._refresh_callback = None
        self._toc_cache = None

        self._config_id_counter = 1

    def add_config(self, logconf):
        """Add a log configuration to the logging framework.

        When doing this the contents of the log configuration will be validated
        and listeners for new log configurations will be notified. When
        validating the configuration the variables are checked against the TOC
        to see that they actually exist. If they don't then the configuration
        cannot be used. Since a valid TOC is required, a Crazyflie has to be
        connected when calling this method, otherwise it will fail."""

        if not self.cf.link:
            logger.error('Cannot add configs without being connected to a '
                         'Crazyflie!')
            return

        # If the log configuration contains variables that we added without
        # type (i.e we want the stored as type for fetching as well) then
        # resolve this now and add them to the block again.
        for name in logconf.default_fetch_as:
            var = self.toc.get_element_by_complete_name(name)
            if not var:
                logger.warning(
                    '%s not in TOC, this block cannot be used!', name)
                logconf.valid = False
                raise KeyError('Variable {} not in TOC'.format(name))
            # Now that we know what type this variable has, add it to the log
            # config again with the correct type
            logconf.add_variable(name, var.ctype)

        # Now check that all the added variables are in the TOC and that
        # the total size constraint of a data packet with logging data is
        # not
        size = 0
        for var in logconf.variables:
            size += LogTocElement.get_size_from_id(var.fetch_as)
            # Check that we are able to find the variable in the TOC so
            # we can return error already now and not when the config is sent
            if var.is_toc_variable():
                if (self.toc.get_element_by_complete_name(var.name) is None):
                    logger.warning(
                        'Log: %s not in TOC, this block cannot be used!',
                        var.name)
                    logconf.valid = False
                    raise KeyError('Variable {} not in TOC'.format(var.name))

        if (size <= MAX_LOG_DATA_PACKET_SIZE and
                (logconf.period > 0 and logconf.period < 0xFF)):
            logconf.valid = True
            logconf.cf = self.cf
            logconf.id = self._config_id_counter
            self._config_id_counter = (self._config_id_counter + 1) % 255
            self.log_blocks.append(logconf)
            self.block_added_cb.call(logconf)
        else:
            logconf.valid = False
            raise AttributeError(
                'The log configuration is too large or has an invalid '
                'parameter')

    def refresh_toc(self, refresh_done_callback, toc_cache):
        """Start refreshing the table of loggale variables"""

        self._toc_cache = toc_cache
        self._refresh_callback = refresh_done_callback
        self.toc = None

        pk = CRTPPacket()
        pk.set_header(CRTPPort.LOGGING, CHAN_SETTINGS)
        pk.data = (CMD_RESET_LOGGING,)
        self.cf.send_packet(pk, expected_reply=(CMD_RESET_LOGGING,))

    def _find_block(self, id):
        for block in self.log_blocks:
            if block.id == id:
                return block
        return None

    def _new_packet_cb(self, packet):
        """Callback for newly arrived packets with TOC information"""
        chan = packet.channel
        cmd = packet.data[0]
        payload = packet.data[1:]

        if (chan == CHAN_SETTINGS):
            id = payload[0]
            error_status = payload[1]
            block = self._find_block(id)
            if (cmd == CMD_CREATE_BLOCK):
                if (block is not None):
                    if error_status == 0 or error_status == errno.EEXIST:
                        if not block.added:
                            logger.debug('Have successfully added id=%d', id)

                            pk = CRTPPacket()
                            pk.set_header(5, CHAN_SETTINGS)
                            pk.data = (CMD_START_LOGGING, id, block.period)
                            self.cf.send_packet(pk, expected_reply=(
                                CMD_START_LOGGING, id))
                            block.added = True
                    else:
                        msg = self._err_codes[error_status]
                        logger.warning('Error %d when adding id=%d (%s)',
                                       error_status, id, msg)
                        block.err_no = error_status
                        block.added_cb.call(False)
                        block.error_cb.call(block, msg)

                else:
                    logger.warning('No LogEntry to assign block to !!!')
            if (cmd == CMD_START_LOGGING):
                if (error_status == 0x00):
                    logger.info('Have successfully started logging for id=%d',
                                id)
                    if block:
                        block.started = True

                else:
                    msg = self._err_codes[error_status]
                    logger.warning('Error %d when starting id=%d (%s)',
                                   error_status, id, msg)
                    if block:
                        block.err_no = error_status
                        block.started_cb.call(self, False)
                        # This is a temporary fix, we are adding a new issue
                        # for this. For some reason we get an error back after
                        # the block has been started and added. This will show
                        # an error in the UI, but everything is still working.
                        # block.error_cb.call(block, msg)

            if (cmd == CMD_STOP_LOGGING):
                if (error_status == 0x00):
                    logger.info('Have successfully stopped logging for id=%d',
                                id)
                    if block:
                        block.started = False

            if (cmd == CMD_DELETE_BLOCK):
                # Accept deletion of a block that isn't added. This could
                # happen due to timing (i.e add/start/delete in fast sequence)
                if error_status == 0x00 or error_status == errno.ENOENT:
                    logger.info('Have successfully deleted id=%d', id)
                    if block:
                        block.started = False
                        block.added = False

            if (cmd == CMD_RESET_LOGGING):
                # Guard against multiple responses due to re-sending
                if not self.toc:
                    logger.debug('Logging reset, continue with TOC download')
                    self.log_blocks = []

                    self.toc = Toc()
                    toc_fetcher = TocFetcher(self.cf, LogTocElement,
                                             CRTPPort.LOGGING,
                                             self.toc, self._refresh_callback,
                                             self._toc_cache)
                    toc_fetcher.start()

        if (chan == CHAN_LOGDATA):
            chan = packet.channel
            id = packet.data[0]
            block = self._find_block(id)
            timestamps = struct.unpack('<BBB', packet.data[1:4])
            timestamp = (
                timestamps[0] | timestamps[1] << 8 | timestamps[2] << 16)
            logdata = packet.data[4:]
            if (block is not None):
                block.unpack_log_data(logdata, timestamp)
            else:
                logger.warning('Error no LogEntry to handle id=%d', id)
