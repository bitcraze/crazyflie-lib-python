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
from cflib.crazyflie import Crazyflie
from cflib.localization.param_io import ParamFileManager


class ParamFileHelper:
    def __init__(self, crazyflie):
        if isinstance(crazyflie, Crazyflie):
            self._cf = crazyflie
        else:
            raise TypeError("ParamFileHelper only takes a Crazyflie Object")
    
    def store_params_from_file(self, filename):
        print(self._cf.param)
        params = ParamFileManager().read(filename)
        for param, state in params.items():
            self._cf.param.set_value(param, state.stored_value)
            self._cf.param.persistent_store(param)
