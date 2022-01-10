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
"""
Functionality to handle base station geometry in the lighthouse poistioning system
"""
from __future__ import annotations

from cflib.localization.lighthouse_bs_vector import LighthouseBsVector
from cflib.localization.lighthouse_geometry_solver import LighthouseGeometrySolver
from cflib.localization.lighthouse_initial_estimator import LighthouseInitialEstimator
from cflib.localization.lighthouse_sample_matcher import LighthouseSampleMatcher
from cflib.localization.lighthouse_types import LhDeck4SensorPositions
from cflib.localization.lighthouse_types import LhMeasurement


class LighthouseBsGeoEstimator:
    """
    This class is used to estimate the geometry (position and attitude)
    of a lighthouse base station, given angles measured using a lighthouse deck.
    """

    def __init__(self):
        # Sanity check maximum pos
        self._sanity_max_pos = 15

    def estimate_geometry(self, bs_vectors: list[LighthouseBsVector]):
        """
        Estimate the full pose of a base station based on angles from the 4 sensors
        on a lighthouse deck. The result is a rotation matrix and position of the
        base station, in the Crazyflie reference frame.

        :param bs_vectors A list of 4 LighthouseBsVector objects specifying vectors to the 4 sensors
        :return rot_bs_in_cf_coord: Rotation matrix of the BS in the CFs coordinate system
        :return pos_bs_in_cf_coord: Position vector of the BS in the CFs coordinate system
        """
        bs_id = 0

        samples = [LhMeasurement(timestamp=0.0, base_station_id=bs_id, angles=bs_vectors)]
        matched_samples = LighthouseSampleMatcher.match(samples)
        initial_guess = LighthouseInitialEstimator.estimate(matched_samples, LhDeck4SensorPositions.positions)
        solution = LighthouseGeometrySolver.solve(initial_guess, matched_samples, LhDeck4SensorPositions.positions)
        pose = solution.bs_poses[bs_id]

        return pose.rot_matrix, pose.translation

    def sanity_check_result(self, pos_bs_in_cf_coord):
        """
        Checks if the estimated geometry is within reasonable bounds. It returns
        true if it seems reasonable or false if it doesn't
        """
        for coord in pos_bs_in_cf_coord:
            if (abs(coord) > self._sanity_max_pos):
                return False
        return True
