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

from cflib.localization.lighthouse_cf_pose_sample import LhCfPoseSample
from cflib.localization.lighthouse_types import LhMeasurement
from cflib.localization.lighthouse_bs_vector import LighthouseBsVectors


class LighthouseSampleMatcher:
    """Utility class to match samples of measurements from multiple lighthouse base stations.

    Assuming that the Crazyflie was moving when the measurements were recorded,
    samples that were measured approximately at the same position are aggregated into
    a list of LhCfPoseSample. Matching is done using the timestamp and a maximum time span.
    """

    @classmethod
    def match(cls, samples: list[LhMeasurement], max_time_diff: float = 0.020,
              min_nr_of_bs_in_match: int = 1) -> list[LhCfPoseSample]:
        """
        Aggregate samples close in time into lists
        """

        result = []
        current_angles: dict[int, LighthouseBsVectors] = {}
        current_ts = 0.0

        for sample in samples:
            if len(current_angles) > 0:
                if sample.timestamp > (current_ts + max_time_diff):
                    if len(current_angles) >= min_nr_of_bs_in_match:
                        pose_sample = LhCfPoseSample(timestamp=current_ts, angles_calibrated=current_angles)
                        result.append(pose_sample)

                    current_angles = {}

            if len(current_angles) == 0:
                current_ts = sample.timestamp
            current_angles[sample.base_station_id] = sample.angles

        if len(current_angles) >= min_nr_of_bs_in_match:
            pose_sample = LhCfPoseSample(timestamp=current_ts, angles_calibrated=current_angles)
            result.append(pose_sample)

        return result
