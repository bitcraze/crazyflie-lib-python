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
from test.localization.lighthouse_fixtures import LighthouseFixtures
from test.localization.lighthouse_test_base import LighthouseTestBase

from cflib.localization.lighthouse_geometry_solver import LighthouseGeometrySolver
from cflib.localization.lighthouse_initial_estimator import LighthouseInitialEstimator
from cflib.localization.lighthouse_types import LhCfPoseSample
from cflib.localization.lighthouse_types import LhDeck4SensorPositions


class TestLighthouseGeometrySolver(LighthouseTestBase):
    def setUp(self):
        self.fixtures = LighthouseFixtures()

    def test_that_two_bs_poses_in_one_sample_are_estimated(self):
        # Fixture
        # CF_ORIGIN is used in the first sample and will define the global reference frame
        bs_id0 = 3
        bs_id1 = 1
        matched_samples = [
            LhCfPoseSample(angles_calibrated={
                bs_id0: self.fixtures.angles_cf_origin_bs0,
                bs_id1: self.fixtures.angles_cf_origin_bs1,
            }),
        ]

        initial_guess, cleaned_matched_samples = LighthouseInitialEstimator.estimate(matched_samples,
                                                                                     LhDeck4SensorPositions.positions)

        # Test
        actual = LighthouseGeometrySolver.solve(
            initial_guess, cleaned_matched_samples, LhDeck4SensorPositions.positions)

        # Assert
        bs_poses = actual.bs_poses
        self.assertPosesAlmostEqual(self.fixtures.BS0_POSE, bs_poses[bs_id0], places=3)
        self.assertPosesAlmostEqual(self.fixtures.BS1_POSE, bs_poses[bs_id1], places=3)

    def test_that_linked_bs_poses_in_multiple_samples_are_estimated(self):
        # Fixture
        # CF_ORIGIN is used in the first sample and will define the global reference frame
        bs_id0 = 7
        bs_id1 = 2
        bs_id2 = 9
        bs_id3 = 3
        matched_samples = [
            LhCfPoseSample(angles_calibrated={
                bs_id0: self.fixtures.angles_cf_origin_bs0,
                bs_id1: self.fixtures.angles_cf_origin_bs1,
            }),
            LhCfPoseSample(angles_calibrated={
                bs_id1: self.fixtures.angles_cf1_bs1,
                bs_id2: self.fixtures.angles_cf1_bs2,
            }),
            LhCfPoseSample(angles_calibrated={
                bs_id2: self.fixtures.angles_cf2_bs2,
                bs_id3: self.fixtures.angles_cf2_bs3,
            }),
        ]

        initial_guess, cleaned_matched_samples = LighthouseInitialEstimator.estimate(matched_samples,
                                                                                     LhDeck4SensorPositions.positions)

        # Test
        actual = LighthouseGeometrySolver.solve(
            initial_guess, cleaned_matched_samples, LhDeck4SensorPositions.positions)

        # Assert
        bs_poses = actual.bs_poses
        self.assertPosesAlmostEqual(self.fixtures.BS0_POSE, bs_poses[bs_id0], places=3)
        self.assertPosesAlmostEqual(self.fixtures.BS1_POSE, bs_poses[bs_id1], places=3)
        self.assertPosesAlmostEqual(self.fixtures.BS2_POSE, bs_poses[bs_id2], places=3)
        self.assertPosesAlmostEqual(self.fixtures.BS3_POSE, bs_poses[bs_id3], places=3)
