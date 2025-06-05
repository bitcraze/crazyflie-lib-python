# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2022 Bitcraze AB
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
from __future__ import annotations

from cflib.localization.lighthouse_bs_vector import LighthouseBsVectors
from cflib.localization.lighthouse_cf_pose_sample import LhCfPoseSample
from cflib.localization.lighthouse_types import LhMeasurement


class LighthouseSampleMatcher:
    """Utility class to match samples of measurements from multiple lighthouse base stations.

    Assuming that the Crazyflie was moving when the measurements were recorded,
    samples that were measured approximately at the same position are aggregated into
    a list of LhCfPoseSample. Matching is done using the timestamp and a maximum time span.
    """

    def __init__(self, max_time_diff: float = 0.020, min_nr_of_bs_in_match: int = 1) -> None:
        self.max_time_diff = max_time_diff
        self.min_nr_of_bs_in_match = min_nr_of_bs_in_match

        self._current_angles: dict[int, LighthouseBsVectors] = {}
        self._current_ts = 0.0

    def match_one(self, sample: LhMeasurement) -> LhCfPoseSample | None:
        """Aggregate samples close in time.
        This function is used to match samples from multiple base stations into a single LhCfPoseSample.
        The function will return None if the number of base stations in the sample is less than
        the minimum number of base stations required for a match.
        Note that a pose sample is returned upon the next call to this function, that is when the maximum time diff of
        the first sample in the group has been exceeded.

        Args:
            sample (LhMeasurement): angles from one base station

        Returns:
            LhCfPoseSample | None: a pose sample if available, otherwise None
        """
        result = None
        if len(self._current_angles) > 0:
            if sample.timestamp > (self._current_ts + self.max_time_diff):
                if len(self._current_angles) >= self.min_nr_of_bs_in_match:
                    result = LhCfPoseSample(self._current_angles, timestamp=self._current_ts)

                self._current_angles = {}

        if len(self._current_angles) == 0:
            self._current_ts = sample.timestamp

        self._current_angles[sample.base_station_id] = sample.angles

        return result

    def purge(self) -> LhCfPoseSample | None:
        """Purge the current angles and return a pose sample if available.

        Returns:
            LhCfPoseSample | None: a pose sample if available, otherwise None
        """
        result = None

        if len(self._current_angles) >= self.min_nr_of_bs_in_match:
            result = LhCfPoseSample(self._current_angles, timestamp=self._current_ts)

        self._current_angles = {}
        self._current_ts = 0.0

        return result

    @classmethod
    def match(cls, samples: list[LhMeasurement], max_time_diff: float = 0.020,
              min_nr_of_bs_in_match: int = 1) -> list[LhCfPoseSample]:
        """
        Aggregate samples in a list
        """

        result = []
        matcher = cls(max_time_diff, min_nr_of_bs_in_match)

        for sample in samples:
            pose_sample = matcher.match_one(sample)
            if pose_sample is not None:
                result.append(pose_sample)

        pose_sample = matcher.purge()
        if pose_sample is not None:
            result.append(pose_sample)

        return result
