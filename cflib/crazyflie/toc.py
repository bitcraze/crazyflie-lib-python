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
A generic TableOfContents module that is used to fetch, store and manipulate
a TOC for logging or parameters.
"""
import logging
import struct

from cflib.crtp.crtpstack import CRTPPacket

__author__ = 'Bitcraze AB'
__all__ = ['Toc', 'TocFetcher']

logger = logging.getLogger(__name__)

TOC_CHANNEL = 0

# Commands used when accessing the Table of Contents
CMD_TOC_ELEMENT = 0  # original version: up to 255 entries
CMD_TOC_INFO = 1    # original version: up to 255 entries
CMD_TOC_ITEM_V2 = 2  # version 2: up to 16k entries
CMD_TOC_INFO_V2 = 3  # version 2: up to 16k entries

# Possible states when receiving TOC
IDLE = 'IDLE'
GET_TOC_INFO = 'GET_TOC_INFO'
GET_TOC_ELEMENT = 'GET_TOC_ELEMENT'


class Toc:
    """Container for TocElements."""

    def __init__(self):
        self.toc = {}

    def clear(self):
        """Clear the TOC"""
        self.toc = {}

    def add_element(self, element):
        """Add a new TocElement to the TOC container."""
        try:
            self.toc[element.group][element.name] = element
        except KeyError:
            self.toc[element.group] = {}
            self.toc[element.group][element.name] = element

    def get_element_by_complete_name(self, complete_name):
        """Get a TocElement element identified by complete name from the
        container."""
        try:
            return self.get_element_by_id(self.get_element_id(complete_name))
        except ValueError:
            # Item not found
            return None

    def get_element_id(self, complete_name):
        """Get the TocElement element id-number of the element with the
        supplied name."""
        [group, name] = complete_name.split('.')
        element = self.get_element(group, name)
        if element:
            return element.ident
        else:
            logger.warning('Unable to find variable [%s]', complete_name)
            return None

    def get_element(self, group, name):
        """Get a TocElement element identified by name and group from the
        container."""
        try:
            return self.toc[group][name]
        except KeyError:
            return None

    def get_element_by_id(self, ident):
        """Get a TocElement element identified by index number from the
        container."""
        for group in list(self.toc.keys()):
            for name in list(self.toc[group].keys()):
                if self.toc[group][name].ident == ident:
                    return self.toc[group][name]
        return None


class TocFetcher:
    """Fetches TOC entries from the Crazyflie"""

    def __init__(self, crazyflie, element_class, port, toc_holder,
                 finished_callback, toc_cache):
        self.cf = crazyflie
        self.port = port
        self._crc = 0
        self.requested_index = None
        self.nbr_of_items = None
        self.state = None
        self.toc = toc_holder
        self._toc_cache = toc_cache
        self.finished_callback = finished_callback
        self.element_class = element_class
        self._useV2 = False

    def start(self):
        """Initiate fetching of the TOC."""
        self._useV2 = self.cf.platform.get_protocol_version() >= 4

        logger.debug('[%d]: Using V2 protocol: %d', self.port, self._useV2)

        logger.debug('[%d]: Start fetching...', self.port)
        # Register callback in this class for the port
        self.cf.add_port_callback(self.port, self._new_packet_cb)

        # Request the TOC CRC
        self.state = GET_TOC_INFO
        pk = CRTPPacket()
        pk.set_header(self.port, TOC_CHANNEL)
        if self._useV2:
            pk.data = (CMD_TOC_INFO_V2,)
            self.cf.send_packet(pk, expected_reply=(CMD_TOC_INFO_V2,))
        else:
            pk.data = (CMD_TOC_INFO,)
            self.cf.send_packet(pk, expected_reply=(CMD_TOC_INFO,))

    def _toc_fetch_finished(self):
        """Callback for when the TOC fetching is finished"""
        self.cf.remove_port_callback(self.port, self._new_packet_cb)
        logger.debug('[%d]: Done!', self.port)
        self.finished_callback()

    def _new_packet_cb(self, packet):
        """Handle a newly arrived packet"""
        chan = packet.channel
        if (chan != 0):
            return
        payload = packet.data[1:]

        if (self.state == GET_TOC_INFO):
            if self._useV2:
                [self.nbr_of_items, self._crc] = struct.unpack(
                    '<HI', payload[:6])
            else:
                [self.nbr_of_items, self._crc] = struct.unpack(
                    '<BI', payload[:5])
            logger.debug('[%d]: Got TOC CRC, %d items and crc=0x%08X',
                         self.port, self.nbr_of_items, self._crc)

            cache_data = self._toc_cache.fetch(self._crc)
            if (cache_data):
                self.toc.toc = cache_data
                logger.info('TOC for port [%s] found in cache' % self.port)
                self._toc_fetch_finished()
            else:
                self.state = GET_TOC_ELEMENT
                self.requested_index = 0
                self._request_toc_element(self.requested_index)

        elif (self.state == GET_TOC_ELEMENT):
            # Always add new element, but only request new if it's not the
            # last one.
            if self._useV2:
                ident = struct.unpack('<H', payload[:2])[0]
            else:
                ident = payload[0]

            if ident != self.requested_index:
                return
            if self._useV2:
                self.toc.add_element(self.element_class(ident, payload[2:]))
            else:
                self.toc.add_element(self.element_class(ident, payload[1:]))
            logger.debug('Added element [%s]', ident)
            if (self.requested_index < (self.nbr_of_items - 1)):
                logger.debug('[%d]: More variables, requesting index %d',
                             self.port, self.requested_index + 1)
                self.requested_index = self.requested_index + 1
                self._request_toc_element(self.requested_index)
            else:  # No more variables in TOC
                self._toc_cache.insert(self._crc, self.toc.toc)
                self._toc_fetch_finished()

    def _request_toc_element(self, index):
        """Request information about a specific item in the TOC"""
        logger.debug('Requesting index %d on port %d', index, self.port)
        pk = CRTPPacket()
        if self._useV2:
            pk.set_header(self.port, TOC_CHANNEL)
            pk.data = (CMD_TOC_ITEM_V2, index & 0x0ff, (index >> 8) & 0x0ff)
            self.cf.send_packet(pk, expected_reply=(
                CMD_TOC_ITEM_V2, index & 0x0ff, (index >> 8) & 0x0ff))
        else:
            pk.set_header(self.port, TOC_CHANNEL)
            pk.data = (CMD_TOC_ELEMENT, index)
            self.cf.send_packet(pk, expected_reply=(CMD_TOC_ELEMENT, index))
