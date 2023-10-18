# !/usr/bin/env python
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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
Enables reading/writing of parameter values to/from the Crazyflie.

When a Crazyflie is connected it's possible to download a TableOfContent of all
the parameters that can be written/read.

"""
import errno
import logging
import struct
from collections import namedtuple
from queue import Empty
from queue import Queue
from threading import Event
from threading import Lock
from threading import Thread

from .toc import Toc
from .toc import TocFetcher
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.callbacks import Caller

__author__ = 'Bitcraze AB'
__all__ = ['Param', 'ParamTocElement']

logger = logging.getLogger(__name__)

# Possible states
IDLE = 0
WAIT_TOC = 1
WAIT_READ = 2
WAIT_WRITE = 3

TOC_CHANNEL = 0
READ_CHANNEL = 1
WRITE_CHANNEL = 2
MISC_CHANNEL = 3

MISC_SETBYNAME = 0
MISC_VALUE_UPDATED = 1
MISC_GET_EXTENDED_TYPE = 2
MISC_PERSISTENT_STORE = 3
MISC_PERSISTENT_GET_STATE = 4
MISC_PERSISTENT_CLEAR = 5
MISC_GET_DEFAULT_VALUE = 6

PersistentParamState = namedtuple('PersistentParamState', 'is_stored default_value stored_value')


# One element entry in the TOC


class ParamTocElement:
    """An element in the Log TOC."""

    RW_ACCESS = 0
    RO_ACCESS = 1

    EXTENDED_PERSISTENT = 1

    types = {0x08: ('uint8_t', '<B'),
             0x09: ('uint16_t', '<H'),
             0x0A: ('uint32_t', '<L'),
             0x0B: ('uint64_t', '<Q'),
             0x00: ('int8_t', '<b'),
             0x01: ('int16_t', '<h'),
             0x02: ('int32_t', '<i'),
             0x03: ('int64_t', '<q'),
             0x05: ('FP16', ''),
             0x06: ('float', '<f'),
             0x07: ('double', '<d')}

    def __init__(self, ident=0, data=None):
        """TocElement creator. Data is the binary payload of the element."""
        self.ident = ident
        self.persistent = False
        self.extended = False
        if (data):
            strs = struct.unpack('s' * len(data[1:]), data[1:])
            s = ''
            for ch in strs:
                s += ch.decode('ISO-8859-1')
            strs = s.split('\x00')
            self.group = strs[0]
            self.name = strs[1]

            metadata = data[0]
            if isinstance(metadata, str):
                metadata = ord(metadata)

            # If the fouth byte (1 << 4) (0x10) is set we have extended
            # type information for this element.
            self.extended = ((metadata & 0x10) != 0)

            self.ctype = self.types[metadata & 0x0F][0]
            self.pytype = self.types[metadata & 0x0F][1]
            if ((metadata & 0x40) != 0):
                self.access = ParamTocElement.RO_ACCESS
            else:
                self.access = ParamTocElement.RW_ACCESS

    def get_readable_access(self):
        if (self.access == ParamTocElement.RO_ACCESS):
            return 'RO'
        return 'RW'

    def is_extended(self):
        return self.extended

    def mark_persistent(self):
        self.persistent = True

    def is_persistent(self):
        return self.persistent


class Param():
    """
    Used to read and write parameter values in the Crazyflie.
    """

    def __init__(self, crazyflie):
        self.toc = Toc()

        self.cf = crazyflie
        self._useV2 = False
        self.param_update_callbacks = {}
        self.group_update_callbacks = {}
        self.all_update_callback = Caller()
        self.param_updater = None

        self.param_updater = _ParamUpdater(self.cf, self._useV2, self._param_updated)
        self.param_updater.start()

        self.cf.disconnected.add_callback(self._disconnected)
        self.cf.connection_requested.add_callback(self._connection_requested)

        self.all_updated = Caller()
        self.is_updated = False
        self._initialized = Event()

        self.values = {}

    def request_update_of_all_params(self):
        """Request an update of all the parameters in the TOC"""
        for group in self.toc.toc:
            for name in self.toc.toc[group]:
                complete_name = '%s.%s' % (group, name)
                self.request_param_update(complete_name)

    def _check_if_all_updated(self):
        """Check if all parameters from the TOC has at least been fetched
        once"""
        for g in self.toc.toc:
            if g not in self.values:
                return False
            for n in self.toc.toc[g]:
                if n not in self.values[g]:
                    return False

        return True

    def _param_updated(self, pk):
        """Callback with data for an updated parameter"""

        # This method handles both param value packets as well as misc param updated packets
        # The Misc packets have a command byte first and the variable id is shifted one byte
        # Misc packets are not supported for V1
        if pk.channel == MISC_CHANNEL:
            id_index = 1
        else:
            id_index = 0

        if self._useV2:
            var_id = struct.unpack('<H', pk.data[id_index:id_index + 2])[0]
        else:
            var_id = pk.data[0]
        element = self.toc.get_element_by_id(var_id)
        if element:
            if self._useV2:
                value = struct.unpack(element.pytype, pk.data[id_index + 2:])[0]
            else:
                value = struct.unpack(element.pytype, pk.data[1:])[0]
            value_s = value.__str__()
            complete_name = '%s.%s' % (element.group, element.name)

            # Save the value for synchronous access
            if element.group not in self.values:
                self.values[element.group] = {}
            self.values[element.group][element.name] = value_s

            logger.debug('Updated parameter [%s]' % complete_name)
            if complete_name in self.param_update_callbacks:
                self.param_update_callbacks[complete_name].call(complete_name, value_s)
            if element.group in self.group_update_callbacks:
                self.group_update_callbacks[element.group].call(complete_name, value_s)
            self.all_update_callback.call(complete_name, value_s)

            # Once all the parameters are updated call the
            # callback for "everything updated"
            if self._check_if_all_updated() and not self.is_updated:
                self.is_updated = True
                self._initialized.set()
                self.all_updated.call()
        else:
            logger.debug('Variable id [%d] not found in TOC', var_id)

    def remove_update_callback(self, group, name=None, cb=None):
        """Remove the supplied callback for a group or a group.name"""
        if not cb:
            return

        if not name:
            if group in self.group_update_callbacks:
                self.group_update_callbacks[group].remove_callback(cb)
        else:
            paramname = '{}.{}'.format(group, name)
            if paramname in self.param_update_callbacks:
                self.param_update_callbacks[paramname].remove_callback(cb)

    def add_update_callback(self, group=None, name=None, cb=None):
        """
        Add a callback for a specific parameter name. This callback will be
        executed when a new value is read from the Crazyflie.
        """
        if not group and not name:
            self.all_update_callback.add_callback(cb)
        elif not name:
            if group not in self.group_update_callbacks:
                self.group_update_callbacks[group] = Caller()
            self.group_update_callbacks[group].add_callback(cb)
        else:
            paramname = '{}.{}'.format(group, name)
            if paramname not in self.param_update_callbacks:
                self.param_update_callbacks[paramname] = Caller()
            self.param_update_callbacks[paramname].add_callback(cb)

    def refresh_toc(self, refresh_done_callback, toc_cache):
        """
        Initiate a refresh of the parameter TOC.
        """
        def refresh_done():
            extended_elements = list()

            for group in self.toc.toc:
                for element in self.toc.toc[group].values():
                    if element.is_extended():
                        extended_elements.append(element)

            if len(extended_elements) > 0:
                extended_type_fetcher = _ExtendedTypeFetcher(self.cf, self.toc)
                extended_type_fetcher.start()
                extended_type_fetcher.set_callback(refresh_done_callback)
                extended_type_fetcher.request_extended_types(extended_elements)
            else:
                refresh_done_callback()

        self._useV2 = self.cf.platform.get_protocol_version() >= 4
        toc_fetcher = TocFetcher(self.cf, ParamTocElement,
                                 CRTPPort.PARAM, self.toc,
                                 refresh_done, toc_cache)
        toc_fetcher.start()

    def _connection_requested(self, uri):
        # Reset the internal state on connect to make sure we have a clean state
        self.is_updated = False
        self.toc = Toc()
        self.values = {}
        self._initialized.clear()

    def _disconnected(self, uri):
        """Disconnected callback from Crazyflie API"""
        self.param_updater.close()

        # Do not clear self.is_updated here as we might get spurious parameter updates later

        # Clear all values from the previous Crazyflie
        self.toc = Toc()
        self.values = {}

    def request_param_update(self, complete_name):
        """
        Request an update of the value for the supplied parameter.
        """
        self.param_updater.request_param_update(
            self.toc.get_element_id(complete_name))

    def set_value_raw(self, complete_name, type, value):
        """
        Set a parameter value using the complete name and the type. Does not
        need to have received the TOC.
        """
        char_array = bytes(complete_name.replace('.', '\0') + '\0', 'utf-8')
        len_array = len(char_array)

        # This gives us the type for the struct.pack
        pytype = ParamTocElement.types[type][1][1]

        pk = CRTPPacket()
        pk.set_header(CRTPPort.PARAM, MISC_CHANNEL)
        pk.data = struct.pack(f'<B{len_array}sB{pytype}', 0, char_array, type, value)

        # We will not get an update callback when using raw (MISC_CHANNEL)
        # so just send.
        self.cf.send_packet(pk)

    def set_value(self, complete_name, value):
        """
        Set the value for the supplied parameter.
        """
        if not self._initialized.isSet():
            if self.cf.is_called_by_incoming_handler_thread():
                raise Exception('Can not set parameter from callback until fully connected.')
            if not self._initialized.wait(timeout=60):
                raise Exception('Connection timed out')

        element = self.toc.get_element_by_complete_name(complete_name)

        if not element:
            logger.warning("Cannot set value for [%s], it's not in the TOC!",
                           complete_name)
            raise KeyError('{} not in param TOC'.format(complete_name))
        elif element.access == ParamTocElement.RO_ACCESS:
            logger.debug('[%s] is read only, no trying to set value',
                         complete_name)
            raise AttributeError('{} is read-only!'.format(complete_name))
        else:
            varid = element.ident
            pk = CRTPPacket()
            pk.set_header(CRTPPort.PARAM, WRITE_CHANNEL)
            if self._useV2:
                pk.data = struct.pack('<H', varid)
            else:
                pk.data = struct.pack('<B', varid)

            if element.pytype == '<f' or element.pytype == '<d':
                value_nr = float(value)
            else:
                value_nr = int(value)

            pk.data += struct.pack(element.pytype, value_nr)
            self.param_updater.request_param_setvalue(pk)

    def get_value(self, complete_name, timeout=60):
        """
        Read a value for the supplied parameter. This can block for a period
        of time if the parameter values have not been fetched yet.
        """
        if not self._initialized.isSet():
            if self.cf.is_called_by_incoming_handler_thread():
                raise Exception('Can not get parameter from callback until fully connected.')
            if not self._initialized.wait(timeout=60):
                raise Exception('Connection timed out')

        [group, name] = complete_name.split('.')
        return self.values[group][name]

    def get_default_value(self, complete_name, callback):
        """
        Get the default value of the specified parameter.
        The supplied callback will be called with the name of the parameter
        as well as the default value. None if there is an error.

        @param complete_name The 'group.name' name of the parameter to store
        @param callback The callback should take `complete_name` and default value as argument
        """
        element = self.toc.get_element_by_complete_name(complete_name)

        def new_packet_cb(pk):
            if pk.channel == MISC_CHANNEL and pk.data[0] == MISC_GET_DEFAULT_VALUE:
                if pk.data[3] == errno.ENOENT:
                    callback(complete_name, None)
                    self.cf.remove_port_callback(CRTPPort.PARAM, new_packet_cb)
                    return

                default_value, = struct.unpack(element.pytype, pk.data[3:])
                callback(complete_name, default_value)
                self.cf.remove_port_callback(CRTPPort.PARAM, new_packet_cb)

        self.cf.add_port_callback(CRTPPort.PARAM, new_packet_cb)

        pk = CRTPPacket()
        pk.set_header(CRTPPort.PARAM, MISC_CHANNEL)
        pk.data = struct.pack('<BH', MISC_GET_DEFAULT_VALUE, element.ident)
        self.param_updater.send_param_misc(pk)

    def persistent_clear(self, complete_name, callback=None):
        """
        Clear the current value of the specified persistent parameter from
        eeprom. The supplied callback will be called with `True` as an
        argument on success and with `False` as an argument on failure.

        @param complete_name The 'group.name' name of the parameter to store
        @param callback Optional callback should take `complete_name` and boolean status as arguments
        """
        element = self.toc.get_element_by_complete_name(complete_name)
        if not element.is_persistent():
            raise AttributeError(f"Param '{complete_name}' is not persistent")

        def new_packet_cb(pk):
            if pk.channel == MISC_CHANNEL and pk.data[0] == MISC_PERSISTENT_CLEAR:
                callback(complete_name, pk.data[3] == 0)
                self.cf.remove_port_callback(CRTPPort.PARAM, new_packet_cb)

        if callback is not None:
            self.cf.add_port_callback(CRTPPort.PARAM, new_packet_cb)

        pk = CRTPPacket()
        pk.set_header(CRTPPort.PARAM, MISC_CHANNEL)
        pk.data = struct.pack('<BH', MISC_PERSISTENT_CLEAR, element.ident)
        self.param_updater.send_param_misc(pk)

    def persistent_store(self, complete_name, callback=None):
        """
        Store the current value of the specified persistent parameter to
        eeprom. The supplied callback will be called with `True` as an
        argument on success, and with `False` as an argument on failure.

        @param complete_name The 'group.name' name of the parameter to store
        @param callback Optional callback should take `complete_name` and boolean status as arguments
        """
        element = self.toc.get_element_by_complete_name(complete_name)
        if not element.is_persistent():
            raise AttributeError(f"Param '{complete_name}' is not persistent")

        def new_packet_cb(pk):
            if pk.channel == MISC_CHANNEL and pk.data[0] == MISC_PERSISTENT_STORE:
                callback(complete_name, pk.data[3] == 0)
                self.cf.remove_port_callback(CRTPPort.PARAM, new_packet_cb)

        if callback is not None:
            self.cf.add_port_callback(CRTPPort.PARAM, new_packet_cb)

        pk = CRTPPacket()
        pk.set_header(CRTPPort.PARAM, MISC_CHANNEL)
        pk.data = struct.pack('<BH', MISC_PERSISTENT_STORE, element.ident)
        self.param_updater.send_param_misc(pk)

    def persistent_get_state(self, complete_name, callback):
        """
        Get the state of the specified persistent parameter. The state will be
        returned in the supplied callback. The state is represented as a
        namedtuple with members: `is_stored`, `default_value` and
        `stored_value`. The state is `None` if the parameter is not persistent
        or if something goes wrong.

        | Member            | Description                                     |
        | ----------------- | ----------------------------------------------- |
        | `is_stored`       | `True` if the value is stored to eeprom         |
        | `default_value`   | The default value supplied by the firmware      |
        | `stored_value`    | Value stored in eeprom, None if `not is_stored` |

        @param complete_name The 'group.name' name of the parameter to store
        @param callback Callback, takes `complete_name` and PersistentParamState namedtuple as arg
        """
        element = self.toc.get_element_by_complete_name(complete_name)
        if not element.is_persistent():
            raise AttributeError(f"Param '{complete_name}' is not persistent")

        def new_packet_cb(pk):
            if pk.channel == MISC_CHANNEL and pk.data[0] == MISC_PERSISTENT_GET_STATE:
                if pk.data[3] == errno.ENOENT:
                    callback(complete_name, None)
                    self.cf.remove_port_callback(CRTPPort.PARAM, new_packet_cb)
                    return

                is_stored = pk.data[3] == 1
                if not is_stored:
                    default_value, = struct.unpack(element.pytype, pk.data[4:])
                else:
                    # Remove little-endian indicator ('<')
                    just_type = element.pytype[1:]
                    default_value, stored_value = struct.unpack(f'<{just_type * 2}', pk.data[4:])

                callback(complete_name,
                         PersistentParamState(
                             is_stored,
                             default_value,
                             stored_value if is_stored else None
                         )
                         )
                self.cf.remove_port_callback(CRTPPort.PARAM, new_packet_cb)

        self.cf.add_port_callback(CRTPPort.PARAM, new_packet_cb)
        pk = CRTPPacket()
        pk.set_header(CRTPPort.PARAM, MISC_CHANNEL)
        pk.data = struct.pack('<BH', MISC_PERSISTENT_GET_STATE, element.ident)
        self.param_updater.send_param_misc(pk)


class _ExtendedTypeFetcher(Thread):

    def __init__(self, cf, toc):
        Thread.__init__(self)
        self.setDaemon(True)
        self._lock = Lock()

        self._cf = cf
        self._toc = toc
        self._done_callback = None

        self.request_queue = Queue()
        self._cf.add_port_callback(CRTPPort.PARAM, self._new_packet_cb)
        self._should_close = False
        self._req_param = -1
        self._count = -1

    def _new_packet_cb(self, pk):
        """Callback for newly arrived packets"""
        if pk.channel == MISC_CHANNEL:
            var_id = struct.unpack('<H', pk.data[1:3])[0]

            if self._req_param == var_id:
                extended_type = pk.data[3]
                if extended_type == ParamTocElement.EXTENDED_PERSISTENT:
                    self._toc.get_element_by_id(var_id).mark_persistent()
                self._count -= 1
                if self._count == 0:
                    if self._done_callback is not None:
                        self._done_callback()
                    self._close()

                self._req_param = -1
                try:
                    self._lock.release()
                except Exception:
                    pass

    def set_callback(self, callback):
        self._done_callback = callback

    def request_extended_types(self, elements):
        self._count = len(elements)
        for element in elements:
            pk = CRTPPacket()
            pk.set_header(CRTPPort.PARAM, MISC_CHANNEL)

            pk.data = struct.pack('<BH', MISC_GET_EXTENDED_TYPE, element.ident)
            self.request_queue.put(pk)

    def _close(self):
        # First empty the queue from all packets
        try:
            while True:
                self.request_queue.get(block=False)
        except Empty:
            pass

        # Then force an unlock of the mutex if we are waiting for a packet
        # we didn't get back due to a disconnect for example.
        try:
            self._lock.release()
        except RuntimeError:
            pass

    def run(self):
        while not self._should_close:
            pk = self.request_queue.get()  # Wait for request update
            self._lock.acquire()
            if self._cf.link:
                self._req_param = struct.unpack('<H', pk.data[1:3])[0]
                self._cf.send_packet(pk, expected_reply=(tuple(pk.data[:3])))
            else:
                self._lock.release()


class _ParamUpdater(Thread):
    """This thread will update params through a queue to make sure that we
    get back values"""

    def __init__(self, cf, useV2, updated_callback):
        """Initialize the thread"""
        Thread.__init__(self)
        self.setDaemon(True)
        self.wait_lock = Lock()
        self.cf = cf
        self._useV2 = useV2
        self.updated_callback = updated_callback
        self.request_queue = Queue()
        self.cf.add_port_callback(CRTPPort.PARAM, self._new_packet_cb)
        self._should_close = False
        self._lock_pattern = None

    def close(self):
        # First empty the queue from all packets
        try:
            while True:
                self.request_queue.get(block=False)
        except Empty:
            pass

        # Then force an unlock of the mutex if we are waiting for a packet
        # we didn't get back due to a disconnect for example.
        try:
            self.wait_lock.release()
        except RuntimeError:
            pass

    def request_param_setvalue(self, pk):
        """Place a param set value request on the queue. When this is sent to
        the Crazyflie it will answer with the update param value. """
        self.request_queue.put(pk)

    def send_param_misc(self, pk):
        """Place a param misc request on the queue. When this is sent to
        the Crazyflie it will answer with the same var_id and command. """
        self.request_queue.put(pk)

    def _new_packet_cb(self, pk):
        """Callback for newly arrived packets"""
        if pk.channel == READ_CHANNEL or pk.channel == WRITE_CHANNEL:
            if self._useV2:
                release_pattern = pk.data[:2]
                if pk.channel == READ_CHANNEL:
                    pk.data = pk.data[:2] + pk.data[3:]
            else:
                release_pattern = pk.data[:1]

            if (pk.channel != TOC_CHANNEL and self._lock_pattern == release_pattern and
                    pk is not None):
                self.updated_callback(pk)
                self._lock_pattern = None
                try:
                    self.wait_lock.release()
                except Exception:
                    pass
        elif pk.channel == MISC_CHANNEL:
            command = pk.data[0]
            if command == MISC_VALUE_UPDATED:
                self.updated_callback(pk)

            release_pattern = pk.data[:3]
            if self._lock_pattern == release_pattern:
                self._lock_pattern = None
                self.wait_lock.release()

    def request_param_update(self, var_id):
        """Place a param update request on the queue"""
        self._useV2 = self.cf.platform.get_protocol_version() >= 4
        pk = CRTPPacket()
        pk.set_header(CRTPPort.PARAM, READ_CHANNEL)
        if self._useV2:
            pk.data = struct.pack('<H', var_id)
        else:
            pk.data = struct.pack('<B', var_id)
        logger.debug('Requesting request to update param [%d]', var_id)
        self.request_queue.put(pk)

    def run(self):
        while not self._should_close:
            pk = self.request_queue.get()  # Wait for request update
            self.wait_lock.acquire()
            if self.cf.link:
                if self._useV2:
                    if pk.channel == MISC_CHANNEL:
                        self._lock_pattern = pk.data[:3]
                    else:
                        self._lock_pattern = pk.data[:2]

                    self.cf.send_packet(pk, expected_reply=(tuple(self._lock_pattern)))
                else:
                    self._lock_pattern = pk.data[:1]
                    self.cf.send_packet(pk, expected_reply=(tuple(pk.data[:1])))
            else:
                self.wait_lock.release()
