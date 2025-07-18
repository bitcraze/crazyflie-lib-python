#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2025 Bitcraze AB
#
#  Crazyflie Nano Quadcopter Client
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
from collections import namedtuple

from cflib.localization.lighthouse_cf_pose_sample import LhCfPoseSampleWrapper
from cflib.localization.lighthouse_types import Pose


class LighthouseGeometrySolution:
    """
    A class to represent the solution of a lighthouse geometry problem.
    """

    ErrorStats = namedtuple('ErrorStats', ['mean', 'max', 'std'])

    def __init__(self, samples: list[LhCfPoseSampleWrapper]):
        # The samples used to estimate the geometry of the system. The samples are wrapped in
        # LhCfPoseSampleWrapper to provide additional information about the sample type and status. The status can be
        # altered during the solution process to indicate if the sample is valid or not.
        # The estimated pose of the CF is also stored in the wrapper.
        self.samples = samples

        # The estimated poses of the base stations. The keys are the base station ids and the values are the poses.
        self.bs_poses: dict[int, Pose] = {}

        # Information about errors for the samples that are used in the solution
        self.error_stats = self.ErrorStats(0.0, 0.0, 0.0)

        # Information about the verification samples
        self.verification_stats: None | LighthouseGeometrySolution.ErrorStats = None

        # Indicates if the solution converged (True).
        # If it did not converge, the solution is possibly not good enough to use
        self.has_converged = False

        # Progress information stating how far in the solution process we got
        self.progress_info = ''

        # Indicates that all previous steps in the solution process were successful and that the next step
        # can be executed. This is used to determine if the solution process can continue.
        self.progress_is_ok = True

        # Issue descriptions
        self.is_origin_sample_valid = True
        self.origin_sample_info = ''
        self.is_x_axis_samples_valid = True
        self.x_axis_samples_info = ''
        self.is_xy_plane_samples_valid = True
        self.xy_plane_samples_info = ''
        # For the xyz space, there are not any stopping errors, this string may contain information for the user though
        self.xyz_space_samples_info = ''

        # General failure information if the problem is not related to a specific sample
        self.general_failure_info = ''

        # The number of links between base stations. The data is organized as a dictionary with base station ids as
        # keys, mapped to a dictionary of base station ids and the number of links to other base stations.
        # For example: link_count[1][2] = 3 means that base station 1 has 3 links to base station 2.
        self.link_count: dict[int, dict[int, int]] = {}
