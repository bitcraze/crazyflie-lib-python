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
"""
Functionality to manage lighthouse system configuration (geometry and calibration data).
"""
import yaml

from cflib.crazyflie.mem import LighthouseBsCalibration
from cflib.crazyflie.mem import LighthouseBsGeometry


class LighthouseConfigFileManager:
    TYPE_ID = 'type'
    TYPE = 'lighthouse_system_configuration'
    VERSION_ID = 'version'
    VERSION = '1'
    GEOS_ID = 'geos'
    CALIBS_ID = 'calibs'

    @staticmethod
    def write(file_name, geos={}, calibs={}):
        file = open(file_name, 'w')
        with file:
            file_geos = {}
            for id, geo in geos.items():
                if geo.valid:
                    file_geos[id] = geo.as_file_object()

            file_calibs = {}
            for id, calib in calibs.items():
                if calib.valid:
                    file_calibs[id] = calib.as_file_object()

            data = {
                LighthouseConfigFileManager.TYPE_ID: LighthouseConfigFileManager.TYPE,
                LighthouseConfigFileManager.VERSION_ID: LighthouseConfigFileManager.VERSION,
                LighthouseConfigFileManager.GEOS_ID: file_geos,
                LighthouseConfigFileManager.CALIBS_ID: file_calibs
            }

            yaml.dump(data, file)

    @staticmethod
    def read(file_name):
        file = open(file_name, 'r')
        with file:
            data = yaml.safe_load(file)

            if LighthouseConfigFileManager.TYPE_ID not in data:
                raise Exception('Type field missing')

            if data[LighthouseConfigFileManager.TYPE_ID] != LighthouseConfigFileManager.TYPE:
                raise Exception('Unsupported file type')

            if LighthouseConfigFileManager.VERSION_ID not in data:
                raise Exception('Version field missing')

            if data[LighthouseConfigFileManager.VERSION_ID] != LighthouseConfigFileManager.VERSION:
                raise Exception('Unsupported file version')

            result_geos = {}
            result_calibs = {}

            if LighthouseConfigFileManager.GEOS_ID in data:
                for id, geo in data[LighthouseConfigFileManager.GEOS_ID].items():
                    result_geos[id] = LighthouseBsGeometry.from_file_object(geo)

            if LighthouseConfigFileManager.CALIBS_ID in data:
                for id, calib in data[LighthouseConfigFileManager.CALIBS_ID].items():
                    result_calibs[id] = LighthouseBsCalibration.from_file_object(calib)

            return result_geos, result_calibs
