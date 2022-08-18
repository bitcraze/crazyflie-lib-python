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

import numpy as np

from cflib.localization.lighthouse_initial_estimator import LighthouseInitialEstimator
from cflib.localization.lighthouse_types import LhCfPoseSample
from cflib.localization.lighthouse_types import LhDeck4SensorPositions
from cflib.localization.lighthouse_types import Pose


class TestLighthouseInitialEstimator(LighthouseTestBase):
    def setUp(self):
        self.fixtures = LighthouseFixtures()

    def test_that_one_bs_pose_raises_exception(self):
        # Fixture
        # CF_ORIGIN is used in the first sample and will define the global reference frame
        bs_id = 3
        samples = [
            LhCfPoseSample(angles_calibrated={bs_id: self.fixtures.angles_cf_origin_bs0}),
        ]

        # Test
        # Assert
        with self.assertRaises(Exception):
            LighthouseInitialEstimator.estimate(samples, LhDeck4SensorPositions.positions)

    def test_that_two_bs_poses_in_same_sample_are_found(self):
        # Fixture
        # CF_ORIGIN is used in the first sample and will define the global reference frame
        bs_id0 = 3
        bs_id1 = 1
        samples = [
            LhCfPoseSample(angles_calibrated={
                bs_id0: self.fixtures.angles_cf_origin_bs0,
                bs_id1: self.fixtures.angles_cf_origin_bs1,
            }),
        ]

        # Test
        actual, cleaned_samples = LighthouseInitialEstimator.estimate(samples, LhDeck4SensorPositions.positions)

        # Assert
        self.assertPosesAlmostEqual(self.fixtures.BS0_POSE, actual.bs_poses[bs_id0], places=3)
        self.assertPosesAlmostEqual(self.fixtures.BS1_POSE, actual.bs_poses[bs_id1], places=3)

    def test_that_linked_bs_poses_in_multiple_samples_are_found(self):
        # Fixture
        # CF_ORIGIN is used in the first sample and will define the global reference frame
        bs_id0 = 7
        bs_id1 = 1
        bs_id2 = 5
        bs_id3 = 0
        samples = [
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

        # Test
        actual, cleaned_samples = LighthouseInitialEstimator.estimate(samples, LhDeck4SensorPositions.positions)

        # Assert
        self.assertPosesAlmostEqual(self.fixtures.BS0_POSE, actual.bs_poses[bs_id0], places=3)
        self.assertPosesAlmostEqual(self.fixtures.BS1_POSE, actual.bs_poses[bs_id1], places=3)
        self.assertPosesAlmostEqual(self.fixtures.BS2_POSE, actual.bs_poses[bs_id2], places=3)
        self.assertPosesAlmostEqual(self.fixtures.BS3_POSE, actual.bs_poses[bs_id3], places=3)

    def test_that_cf_poses_are_estimated(self):
        # Fixture
        # CF_ORIGIN is used in the first sample and will define the global reference frame
        bs_id0 = 7
        bs_id1 = 1
        bs_id2 = 5
        bs_id3 = 0
        samples = [
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

        # Test
        actual, cleaned_samples = LighthouseInitialEstimator.estimate(samples, LhDeck4SensorPositions.positions)

        # Assert
        self.assertPosesAlmostEqual(self.fixtures.CF_ORIGIN_POSE, actual.cf_poses[0], places=3)
        self.assertPosesAlmostEqual(self.fixtures.CF1_POSE, actual.cf_poses[1], places=3)
        self.assertPosesAlmostEqual(self.fixtures.CF2_POSE, actual.cf_poses[2], places=3)

    def test_that_the_global_ref_frame_is_used(self):
        # Fixture
        # CF2 is used in the first sample and will define the global reference frame
        bs_id0 = 3
        bs_id1 = 1
        bs_id2 = 2
        samples = [
            LhCfPoseSample(angles_calibrated={
                bs_id0: self.fixtures.angles_cf2_bs0,
                bs_id1: self.fixtures.angles_cf2_bs1,
            }),
            LhCfPoseSample(angles_calibrated={
                bs_id1: self.fixtures.angles_cf1_bs1,
                bs_id2: self.fixtures.angles_cf1_bs2,
            }),
        ]

        # Test
        actual, cleaned_samples = LighthouseInitialEstimator.estimate(samples, LhDeck4SensorPositions.positions)

        # Assert
        self.assertPosesAlmostEqual(
            Pose.from_rot_vec(R_vec=(0.0, 0.0, -np.pi / 2), t_vec=(1.0, 3.0, 3.0)), actual.bs_poses[bs_id0], places=3)
        self.assertPosesAlmostEqual(
            Pose.from_rot_vec(R_vec=(0.0, 0.0, 0.0), t_vec=(-2.0, 1.0, 3.0)), actual.bs_poses[bs_id1], places=3)
        self.assertPosesAlmostEqual(
            Pose.from_rot_vec(R_vec=(0.0, 0.0, np.pi), t_vec=(2.0, 1.0, 3.0)), actual.bs_poses[bs_id2], places=3)

    def test_that_raises_for_isolated_bs(self):
        # Fixture
        bs_id0 = 3
        bs_id1 = 1
        bs_id2 = 2
        bs_id3 = 4
        samples = [
            LhCfPoseSample(angles_calibrated={
                bs_id0: self.fixtures.angles_cf_origin_bs0,
                bs_id1: self.fixtures.angles_cf_origin_bs1,
            }),
            LhCfPoseSample(angles_calibrated={
                bs_id2: self.fixtures.angles_cf1_bs2,
                bs_id3: self.fixtures.angles_cf2_bs2,
            }),
        ]

        # Test
        # Assert
        with self.assertRaises(Exception):
            LighthouseInitialEstimator.estimate(samples, LhDeck4SensorPositions.positions)
