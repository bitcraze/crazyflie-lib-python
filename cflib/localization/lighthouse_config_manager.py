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
import time

import yaml

from cflib.crazyflie.mem import LighthouseBsCalibration
from cflib.crazyflie.mem import LighthouseBsGeometry
from cflib.crazyflie.mem import LighthouseMemHelper


class LighthouseConfigFileManager:
    TYPE_ID = 'type'
    TYPE = 'lighthouse_system_configuration'
    VERSION_ID = 'version'
    VERSION = '1'
    GEOS_ID = 'geos'
    CALIBS_ID = 'calibs'
    SYSTEM_TYPE_ID = 'systemType'

    SYSTEM_TYPE_V1 = 1
    SYSTEM_TYPE_V2 = 2

    @staticmethod
    def write(file_name, geos={}, calibs={}, system_type=SYSTEM_TYPE_V2):
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
                LighthouseConfigFileManager.SYSTEM_TYPE_ID: system_type,
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

            result_system_type = LighthouseConfigFileManager.SYSTEM_TYPE_V2
            if LighthouseConfigFileManager.SYSTEM_TYPE_ID in data:
                result_system_type = data[LighthouseConfigFileManager.SYSTEM_TYPE_ID]

            result_geos = {}
            result_calibs = {}

            if LighthouseConfigFileManager.GEOS_ID in data:
                for id, geo in data[LighthouseConfigFileManager.GEOS_ID].items():
                    result_geos[id] = LighthouseBsGeometry.from_file_object(geo)

            if LighthouseConfigFileManager.CALIBS_ID in data:
                for id, calib in data[LighthouseConfigFileManager.CALIBS_ID].items():
                    result_calibs[id] = LighthouseBsCalibration.from_file_object(calib)

            return result_geos, result_calibs, result_system_type


class LighthouseConfigWriter:
    """
    This class is used to write system config data to the Crazyflie RAM and persis to permanent storage
    """

    def __init__(self, cf, nr_of_base_stations=16):
        self._cf = cf
        self._helper = LighthouseMemHelper(cf)
        self._data_stored_cb = None
        self._geos_to_write = None
        self._geos_to_persist = []
        self._calibs_to_persist = []
        self._write_failed_for_one_or_more_objects = False
        self._nr_of_base_stations = nr_of_base_stations

    def write_and_store_config(self, data_stored_cb, geos=None, calibs=None, system_type=None):
        """
        Transfer geometry and calibration data to the Crazyflie and persist to permanent storage.
        The callback is called when done.
        If geos or calibs is None, no data will be written for that data type.
        If geos or calibs is a dictionary, the values for the base stations in the dictionary will
        transfered to the Crazyflie, data for all other base stations will be invalidated.
        """
        if self._data_stored_cb is not None:
            raise Exception('Write already in prgress')
        self._data_stored_cb = data_stored_cb

        self._cf.loc.receivedLocationPacket.add_callback(self._received_location_packet)

        self._geos_to_write = self._prepare_geos(geos)
        self._calibs_to_write = self._prepare_calibs(calibs)

        self._geos_to_persist = []
        if self._geos_to_write is not None:
            self._geos_to_persist = list(range(self._nr_of_base_stations))

        self._calibs_to_persist = []
        if self._calibs_to_write is not None:
            self._calibs_to_persist = list(range(self._nr_of_base_stations))

        self._write_failed_for_one_or_more_objects = False

        if system_type is not None:
            # Change system type first as this will erase calib and geo data in the CF.
            # Changing system type may trigger a lengthy operation (up to 0.5 s) if the persistant memory requires
            # defrag. Setting a param is an asynchronous operataion, and it is not possible to know if the system
            # swich is finished before we continue.
            self._cf.param.set_value('lighthouse.systemType', system_type)

            # We add a sleep here to make sure the change of system type is finished. It is dirty but will have to
            # do for now. A more propper solution would be to add support for Remote Procedure Calls (RPC) with
            # synchronous function calls.
            time.sleep(0.8)

        self._next()

    def write_and_store_config_from_file(self, data_stored_cb, file_name):
        """
        Read system configuration data from file and write/persist to the Crazyflie.
        Geometry and calibration data for base stations that are not in the config file will be invalidated.
        """
        geos, calibs, system_type = LighthouseConfigFileManager.read(file_name)
        self.write_and_store_config(data_stored_cb, geos=geos, calibs=calibs, system_type=system_type)

    def _next(self):
        if self._geos_to_write is not None:
            self._helper.write_geos(self._geos_to_write, self._upload_done)
            self._geos_to_write = None
            return

        if self._calibs_to_write is not None:
            self._helper.write_calibs(self._calibs_to_write, self._upload_done)
            self._calibs_to_write = None
            return

        if len(self._geos_to_persist) > 0 or len(self._calibs_to_persist) > 0:
            self._cf.loc.send_lh_persist_data_packet(self._geos_to_persist, self._calibs_to_persist)
            self._geos_to_persist = []
            self._calibs_to_persist = []
            return

        tmp_callback = self._data_stored_cb
        self._data_stored_cb = None
        if tmp_callback is not None:
            tmp_callback(not self._write_failed_for_one_or_more_objects)

    def _upload_done(self, sucess):
        if not sucess:
            self._write_failed_for_one_or_more_objects = True
        self._next()

    def _received_location_packet(self, packet):
        # New geo data has been written and stored in the CF
        if packet.type == self._cf.loc.LH_PERSIST_DATA:
            self._next()

    def _prepare_geos(self, geos):
        result = None

        if geos is not None:
            result = dict(geos)

            # Pad for base stations without data
            empty_geo = LighthouseBsGeometry()
            for id in range(self._nr_of_base_stations):
                if id not in result:
                    result[id] = empty_geo

        return result

    def _prepare_calibs(self, calibs):
        result = None

        if calibs is not None:
            result = dict(calibs)

            # Pad for base stations without data
            empty_calib = LighthouseBsCalibration()
            for id in range(self._nr_of_base_stations):
                if id not in result:
                    result[id] = empty_calib

        return result
