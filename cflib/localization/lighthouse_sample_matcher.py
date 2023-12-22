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

from cflib.localization.lighthouse_types import LhCfPoseSample
from cflib.localization.lighthouse_types import LhMeasurement


class LighthouseSampleMatcher:
    """Utility class to match samples of measurements from multiple lighthouse base stations.

    Assuming that the Crazyflie was moving when the measurements were recorded,
    samples that were measured approximately at the same position are aggregated into
    a list of LhCfPoseSample. Matching is done using the timestamp and a maximum time span.
    The default maximum time span is set to be slightly less than one rotation of a base station.
    """

    @classmethod
    def match(cls, samples: list[LhMeasurement], max_time_diff: float = 0.018,
              min_nr_of_bs_in_match: int = 0) -> list[LhCfPoseSample]:
        """
        Aggregate samples close in time into lists
        """

        result = []
        current: LhCfPoseSample = None

        for sample in samples:
            ts = sample.timestamp
            # print(f"sample at {ts}, bs {sample.base_station_id}")

            if current is None:
                current = LhCfPoseSample(timestamp=ts)
                # print(f"New at {ts}")

            if ts > (current.timestamp + max_time_diff) or ts < current.timestamp:
                cls._append_result(current, result, min_nr_of_bs_in_match)
                current = LhCfPoseSample(timestamp=ts)
                # print(f"New at {ts}")

            # if sample.base_station_id in current.angles_calibrated:
                # print(f"  Overwrite bs {sample.base_station_id}")
            current.angles_calibrated[sample.base_station_id] = sample.angles

        cls._append_result(current, result, min_nr_of_bs_in_match)
        return result

    @classmethod
    def _append_result(cls, current: LhCfPoseSample, result: list[LhCfPoseSample], min_nr_of_bs_in_match: int):
        if current is not None and len(current.angles_calibrated) >= min_nr_of_bs_in_match:
            result.append(current)
