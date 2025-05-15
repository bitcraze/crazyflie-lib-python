# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2025 Bitcraze AB
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

import numpy as np
import numpy.typing as npt

from cflib.localization.lighthouse_cf_pose_sample import LhCfPoseSample
from cflib.localization.lighthouse_types import LhMeasurement
from cflib.localization.lighthouse_sample_matcher import LighthouseSampleMatcher


ArrayFloat = npt.NDArray[np.float_]


class LhGeoInputContainer():
    """This class holds the input data required by the geometry estimation functionality.
    """
    def __init__(self, sensor_positions: ArrayFloat) -> None:
        self.EMPTY_POSE_SAMPLE = LhCfPoseSample(angles_calibrated={})
        self.sensor_positions = sensor_positions

        self.origin: LhCfPoseSample = self.EMPTY_POSE_SAMPLE
        self.x_axis: list[LhCfPoseSample] = []
        self.xy_plane: list[LhCfPoseSample] = []
        self.xyz_space: list[LhCfPoseSample] = []

    def set_origin_sample(self, origin: LhCfPoseSample) -> None:
        """Store/update the sample to be used for the origin

        Args:
            origin (LhCfPoseSample): the new origin
        """
        self.origin = origin
        self.origin.augment_with_ippe(self.sensor_positions)

    def set_x_axis_sample(self, x_axis: LhCfPoseSample) -> None:
        """Store/update the sample to be used for the x_axis

        Args:
            x_axis (LhCfPoseSample): the new x-axis sample
        """
        self.x_axis = [x_axis]
        self.x_axis[0].augment_with_ippe(self.sensor_positions)

    def set_xy_plane_samples(self, xy_plane: list[LhCfPoseSample]) -> None:
        """Store/update the samples to be used for the xy-plane

        Args:
            xy_plane (list[LhCfPoseSample]): the new xy-plane samples
        """
        self.xy_plane = xy_plane
        self._augment_samples(self.xy_plane)

    def set_xyz_space_samples(self, samples: list[LhMeasurement]) -> None:
        """Store/update the samples for the volume

        Args:
            samples (list[LhMeasurement]): the new samples
        """
        self.xyz_space = LighthouseSampleMatcher.match(samples, min_nr_of_bs_in_match=2)
        self._augment_samples(self.xyz_space)

    def get_matched_samples(self) -> list[LhCfPoseSample]:
        """Get all pose samples collected in a list

        Returns:
            list[LhCfPoseSample]: _description_
        """
        return [self.origin] + self.x_axis + self.xy_plane + self.xyz_space

    def _augment_samples(self, samples: list[LhCfPoseSample]) -> None:
        for sample in samples:
            sample.augment_with_ippe(self.sensor_positions)
