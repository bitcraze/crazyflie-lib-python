# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2024 Bitcraze AB
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
from threading import Event

from cflib.crazyflie import Crazyflie
from cflib.localization.param_io import ParamFileManager


class ParamFileHelper:
    '''ParamFileHelper is a helper to synchonously write multiple paramteters
    from a file and store them in persistent memory'''

    def __init__(self, crazyflie):
        if isinstance(crazyflie, Crazyflie):
            self._cf = crazyflie
            self.persistent_sema = None
            self.success = False
        else:
            raise TypeError('ParamFileHelper only takes a Crazyflie Object')

    def _persistent_stored_callback(self, complete_name, success):
        self.success = success
        if not success:
            print(f'Persistent params: failed to store {complete_name}!')
        else:
            print(f'Persistent params: stored {complete_name}!')
        self.persistent_sema.set()

    def store_params_from_file(self, filename):
        params = ParamFileManager().read(filename)
        for param, state in params.items():
            self.persistent_sema = Event()
            self._cf.param.set_value(param, state.stored_value)
            self._cf.param.persistent_store(param, self._persistent_stored_callback)
            self.persistent_sema.wait()
            if not self.success:
                break
        return self.success
