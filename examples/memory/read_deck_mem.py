# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2019 Bitcraze AB
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
Example of how to read the memory from a deck
"""
import logging
from threading import Event

import cflib.crtp  # noqa
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.mem import MemoryElement
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


class ReadMem:
    def __init__(self, uri):
        self._event = Event()
        self._cf = Crazyflie(rw_cache='./cache')

        with SyncCrazyflie(uri, cf=self._cf) as scf:
            mems = scf.cf.mem.get_mems(MemoryElement.TYPE_DECK_MEMORY)

            count = len(mems)
            if count != 1:
                raise Exception('Unexpected nr of memories found:', count)

            mem = mems[0]
            mem.query_decks(self.query_complete_cb)
            self._event.wait()

            if len(mem.deck_memories.items()) == 0:
                print('No memories to read')

            for id, deck_mem in mem.deck_memories.items():
                print('-----')
                print('Deck id:', id)
                print('Name:', deck_mem.name)
                print('is_started:', deck_mem.is_started)
                print('supports_read:', deck_mem.supports_read)
                print('supports_write:', deck_mem.supports_write)

                if deck_mem.supports_fw_upgrade:
                    print('This deck supports FW upgrades')
                    print(
                        f'  The required FW is: hash={deck_mem.required_hash}, '
                        f'length={deck_mem.required_length}, name={deck_mem.name}')
                    print('  is_fw_upgrade_required:', deck_mem.is_fw_upgrade_required)
                    if (deck_mem.is_bootloader_active):
                        print('  In bootloader mode, ready to be flashed')
                    else:
                        print('  In FW mode')
                    print('')

                if deck_mem.supports_read:
                    print('Reading first 10 bytes of memory')
                    self._event.clear()
                    deck_mem.read(0, 10, self.read_complete, self.read_failed)
                    self._event.wait()

    def query_complete_cb(self, deck_memories):
        self._event.set()

    def read_complete(self, addr, data):
        print(data)
        self._event.set()

    def read_failed(self, addr):
        print('Read failed @ {}'.format(addr))
        self._event.set()


if __name__ == '__main__':
    # URI to the Crazyflie to connect to
    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    rm = ReadMem(uri)
