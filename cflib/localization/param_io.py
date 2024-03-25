# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2024 Bitcraze AB
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
import yaml

from cflib.crazyflie.param import PersistentParamState


class ParamFileManager():
    """Reads and writes parameter configurations from file"""
    TYPE_ID = 'type'
    TYPE = 'persistent_param_state'
    VERSION_ID = 'version'
    VERSION = '1'
    PARAMS_ID = 'params'

    @staticmethod
    def write(file_name, params={}):
        file = open(file_name, 'w')
        with file:
            file_params = {}
            for id, param in params.items():
                assert isinstance(param, PersistentParamState)
                if isinstance(param, PersistentParamState):
                    file_params[id] = {'is_stored': param.is_stored,
                                       'default_value': param.default_value, 'stored_value': param.stored_value}

            data = {
                ParamFileManager.TYPE_ID: ParamFileManager.TYPE,
                ParamFileManager.VERSION_ID: ParamFileManager.VERSION,
                ParamFileManager.PARAMS_ID: file_params
            }

            yaml.dump(data, file)

    @staticmethod
    def read(file_name):
        file = open(file_name, 'r')
        with file:
            data = None
            try:
                data = yaml.safe_load(file)
            except yaml.YAMLError as exc:
                print(exc)

            if ParamFileManager.TYPE_ID not in data:
                raise Exception('Type field missing')

            if data[ParamFileManager.TYPE_ID] != ParamFileManager.TYPE:
                raise Exception('Unsupported file type')

            if ParamFileManager.VERSION_ID not in data:
                raise Exception('Version field missing')

            if data[ParamFileManager.VERSION_ID] != ParamFileManager.VERSION:
                raise Exception('Unsupported file version')

            def get_data(input_data):
                persistent_params = {}
                for id, param in input_data.items():
                    persistent_params[id] = PersistentParamState(
                        param['is_stored'], param['default_value'], param['stored_value'])
                return persistent_params

            if ParamFileManager.PARAMS_ID in data:
                return get_data(data[ParamFileManager.PARAMS_ID])
            else:
                return {}
