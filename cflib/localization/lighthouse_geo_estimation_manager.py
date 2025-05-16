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
from cflib.localization.lighthouse_system_aligner import LighthouseSystemAligner
from cflib.localization.lighthouse_system_scaler import LighthouseSystemScaler
from cflib.localization.lighthouse_types import LhBsCfPoses, LhMeasurement
from cflib.localization.lighthouse_sample_matcher import LighthouseSampleMatcher


ArrayFloat = npt.NDArray[np.float_]


class LhGeoEstimationManager():
    @classmethod
    def align_and_scale_solution(cls, container: LhGeoInputContainer, poses: LhBsCfPoses,
                                 reference_distance: float) -> LhBsCfPoses:
        start_idx_x_axis = 1
        start_idx_xy_plane = 1 + len(container.x_axis)

        origin_pos = poses.cf_poses[0].translation
        x_axis_poses = poses.cf_poses[start_idx_x_axis:start_idx_x_axis + len(container.x_axis)]
        x_axis_pos = list(map(lambda x: x.translation, x_axis_poses))
        xy_plane_poses = poses.cf_poses[start_idx_xy_plane:start_idx_xy_plane + len(container.xy_plane)]
        xy_plane_pos = list(map(lambda x: x.translation, xy_plane_poses))

        # Align the solution
        bs_aligned_poses, trnsfrm = LighthouseSystemAligner.align(origin_pos, x_axis_pos, xy_plane_pos, poses.bs_poses)
        cf_aligned_poses = list(map(trnsfrm.rotate_translate_pose, poses.cf_poses))

        # Scale the solution
        bs_scaled_poses, cf_scaled_poses, scale = LighthouseSystemScaler.scale_fixed_point(bs_aligned_poses,
                                                                                           cf_aligned_poses,
                                                                                           [reference_distance, 0, 0],
                                                                                           cf_aligned_poses[1])

        return LhBsCfPoses(bs_poses=bs_scaled_poses, cf_poses=cf_scaled_poses)


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
        self._augment_sample(self.origin, True)

    def set_x_axis_sample(self, x_axis: LhCfPoseSample) -> None:
        """Store/update the sample to be used for the x_axis

        Args:
            x_axis (LhCfPoseSample): the new x-axis sample
        """
        self.x_axis = [x_axis]
        self._augment_samples(self.x_axis, True)

    def set_xy_plane_samples(self, xy_plane: list[LhCfPoseSample]) -> None:
        """Store/update the samples to be used for the xy-plane

        Args:
            xy_plane (list[LhCfPoseSample]): the new xy-plane samples
        """
        self.xy_plane = xy_plane
        self._augment_samples(self.xy_plane, True)

    def set_xyz_space_samples(self, samples: list[LhMeasurement]) -> None:
        """Store/update the samples for the volume

        Args:
            samples (list[LhMeasurement]): the new samples
        """
        self.xyz_space = LighthouseSampleMatcher.match(samples, min_nr_of_bs_in_match=2)
        self._augment_samples(self.xyz_space, False)

    def get_matched_samples(self) -> list[LhCfPoseSample]:
        """Get all pose samples collected in a list

        Returns:
            list[LhCfPoseSample]: _description_
        """
        return [self.origin] + self.x_axis + self.xy_plane + self.xyz_space

    def _augment_sample(self, sample: LhCfPoseSample, is_mandatory: bool) -> None:
        sample.augment_with_ippe(self.sensor_positions)
        sample.is_mandatory = is_mandatory

    def _augment_samples(self, samples: list[LhCfPoseSample], is_mandatory: bool) -> None:
        for sample in samples:
            self._augment_sample(sample, is_mandatory)
