# -*- coding: utf-8 -*-
#
#  Copyright (C) 2015 Danilo Bargen
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
Flash the DS28E05 EEPROM via CRTP.
"""
import datetime
import os
import sys
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.mem import MemoryElement


class NotConnected(RuntimeError):
    pass


class Flasher(object):
    """
    A class that can flash the DS28E05 EEPROM via CRTP.
    """

    def __init__(self, link_uri):
        self._cf = Crazyflie()
        self._link_uri = link_uri

        # Add some callbacks from the Crazyflie API
        self._cf.connected.add_callback(self._connected)
        self._cf.disconnected.add_callback(self._disconnected)
        self._cf.connection_failed.add_callback(self._connection_failed)
        self._cf.connection_lost.add_callback(self._connection_lost)

        # Initialize variables
        self.connected = False
        self.refreshed = False

    # Public methods

    def connect(self):
        """
        Connect to the crazyflie.
        """
        print('Connecting to %s' % self._link_uri)
        self._cf.open_link(self._link_uri)

    def disconnect(self):
        print('Disconnecting from %s' % self._link_uri)
        self._cf.close_link()

    def wait_for_connection(self, timeout=10):
        """
        Busy loop until connection is established.

        Will abort after timeout (seconds). Return value is a boolean, whether
        connection could be established.

        """
        start_time = datetime.datetime.now()
        while True:
            if self.connected:
                return True
            now = datetime.datetime.now()
            if (now - start_time).total_seconds() > timeout:
                return False
            time.sleep(0.5)

    def search_memories(self):
        """
        Search and return list of 1-wire memories.
        """
        if not self.connected:
            raise NotConnected()
        return self._cf.mem.get_mems(MemoryElement.TYPE_MEMORY_USD)

    def refresh_memories(self):
        """
        Search and return list of 1-wire memories.
        """
        if not self.connected:
            raise NotConnected()
        return self._cf.mem.refresh(self._refresh)


    # Callbacks

    def _refresh(self):
        print('refreshed')
        self.refreshed = True

    def _connected(self, link_uri):
        print('Connected to %s' % link_uri)
        self.connected = True

    def _disconnected(self, link_uri):
        print('Disconnected from %s' % link_uri)
        self.connected = False

    def _connection_failed(self, link_uri, msg):
        print('Connection to %s failed: %s' % (link_uri, msg))
        self.connected = False

    def _connection_lost(self, link_uri, msg):
        print('Connection to %s lost: %s' % (link_uri, msg))
        self.connected = False


def choose(items, title_text, question_text):
    """
    Interactively choose one of the items.
    """
    print(title_text)

    for i, item in enumerate(items, start=1):
        print('%d) %s' % (i, item))
        print('%d) Abort' % (i + 1))

    selected = input(question_text)
    try:
        index = int(selected)
    except ValueError:
        index = -1
    if not (index - 1) in range(len(items)):
        print('Aborting.')
        return None

    return items[index - 1]


def scan():
    """
    Scan for Crazyflie and return its URI.
    """

    # Initiate the low level drivers
    cflib.crtp.init_drivers(enable_debug_driver=False)

    # Scan for Crazyflies
    print('Scanning interfaces for Crazyflies...')
    available = cflib.crtp.scan_interfaces()
    interfaces = [uri for uri, _ in available]

    if not interfaces:
        return None
    return choose(interfaces, 'Crazyflies found:', 'Select interface: ')

def r_cb(a):
    print("new data recived")

if __name__ == '__main__':
    radio_uri = scan()
    if radio_uri is None:
        print('None found.')
        sys.exit(1)

    # Show info about bug 166
    print('\n###\n'
          'Please make sure that your NRF firmware is compiled without\n'
          'BLE support for this to work.\n'
          'See '
          'https://github.com/bitcraze/crazyflie-clients-python/issues/166\n'
          '###\n')

    # Initialize flasher
    flasher = Flasher(radio_uri)

    def abort():
        flasher.disconnect()
        sys.exit(1)

    # Connect to Crazyflie
    flasher.connect()
    connected = flasher.wait_for_connection()
    if not connected:
        print('Connection failed.')
        abort()

    # Search for memories
    stop = False

    while stop == False:
        flasher.refresh_memories()
        while flasher.refreshed ==  False:
            pass
        flasher.refreshed =  False
        mems = flasher.search_memories()

        mem = choose(mems, 'Available memories:', 'Select memory: ')
        if mem is None:
            stop = True
            print('Aborting.')
            abort()
        else:
            if not mem.size == 0:
                mem.read_data(0, mem.size, r_cb)
                while mem._data is None:
                    pass
                with open('log.bin', 'wb') as the_file:
                    the_file.write(mem._data)
                mem._data = None
                print("finished")
            else:
                print("uSD empty")
            

    flasher.disconnect()
