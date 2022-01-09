# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2021-2022 Bitcraze AB
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
from cflib.localization import LighthouseBsVector
from cflib.localization.lighthouse_bs_vector import LighthouseBsVectors


class LighthouseSweepAngleReader():
    """
    Wrapper to simplify reading of lighthouse sweep angles from the locSrv stream
    """
    ANGLE_STREAM_PARAM = 'locSrv.enLhAngleStream'
    NR_OF_SENSORS = 4

    def __init__(self, cf, data_recevied_cb):
        self._cf = cf
        self._cb = data_recevied_cb
        self._is_active = False

    def start(self):
        """Start reading sweep angles"""
        self._cf.loc.receivedLocationPacket.add_callback(self._packet_received_cb)
        self._angle_stream_activate(True)
        self._is_active = True

    def stop(self):
        """Stop reading sweep angles"""
        if self._is_active:
            self._is_active = False
            self._cf.loc.receivedLocationPacket.remove_callback(self._packet_received_cb)
            self._angle_stream_activate(False)

    def _angle_stream_activate(self, is_active):
        value = 0
        if is_active:
            value = 1
        self._cf.param.set_value(self.ANGLE_STREAM_PARAM, value)

    def _packet_received_cb(self, packet):
        if packet.type != self._cf.loc.LH_ANGLE_STREAM:
            return

        if self._cb:
            base_station_id = packet.data['basestation']
            horiz_angles = packet.data['x']
            vert_angles = packet.data['y']

            result = []
            for i in range(self.NR_OF_SENSORS):
                result.append(LighthouseBsVector(horiz_angles[i], vert_angles[i]))

            self._cb(base_station_id, LighthouseBsVectors(result))


class LighthouseSweepAngleAverageReader():
    """
    Helper class to make it easy read sweep angles for multiple base stations and average the result
    """

    def __init__(self, cf, ready_cb):
        self._reader = LighthouseSweepAngleReader(cf, self._data_recevied_cb)
        self._ready_cb = ready_cb
        self.nr_of_samples_required = 50

        # We store all samples in the storage for averaging when data is collected
        # The storage is a dictionary keyed on the base station channel
        # Each entry is a list of 4 lists, one per sensor.
        # Each list contains LighthouseBsVector objects, representing the sampled sweep angles
        self._sample_storage = None

    def start_angle_collection(self):
        """
        Start collecting angles. The process will terminate when nr_of_samples_required have been
        received
        """
        self._sample_storage = {}
        self._reader.start()

    def stop_angle_collection(self):
        """Premature stop of data collection"""
        self._reader.stop()
        self._sample_storage = None

    def is_collecting(self):
        """True if data collection is in progress"""
        return self._sample_storage is not None

    def _data_recevied_cb(self, base_station_id, bs_vectors):
        self._store_sample(base_station_id, bs_vectors, self._sample_storage)
        if self._has_collected_enough_data(self._sample_storage):
            self._reader.stop()
            if self._ready_cb:
                averages = self._average_all_lists(self._sample_storage)
                self._ready_cb(averages)
            self._sample_storage = None

    def _store_sample(self, base_station_id, bs_vectors, storage):
        if base_station_id not in storage:
            storage[base_station_id] = []
            for sensor in range(self._reader.NR_OF_SENSORS):
                storage[base_station_id].append([])

        for sensor in range(self._reader.NR_OF_SENSORS):
            storage[base_station_id][sensor].append(bs_vectors[sensor])

    def _has_collected_enough_data(self, storage):
        for sample_list in storage.values():
            if len(sample_list[0]) >= self.nr_of_samples_required:
                return True
        return False

    def _average_all_lists(self, storage):
        result = {}

        for id, sample_lists in storage.items():
            averages = self._average_sample_lists(sample_lists)
            count = len(sample_lists[0])
            result[id] = (count, averages)

        return result

    def _average_sample_lists(self, sample_lists):
        result = []

        for i in range(self._reader.NR_OF_SENSORS):
            result.append(self._average_sample_list(sample_lists[i]))

        return LighthouseBsVectors(result)

    def _average_sample_list(self, sample_list):
        sum_horiz = 0.0
        sum_vert = 0.0

        for bs_vector in sample_list:
            sum_horiz += bs_vector.lh_v1_horiz_angle
            sum_vert += bs_vector.lh_v1_vert_angle

        count = len(sample_list)
        return LighthouseBsVector(sum_horiz / count, sum_vert / count)
