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
from test.localization.lighthouse_test_base import LighthouseTestBase

import numpy as np

from cflib.localization.lighthouse_system_aligner import LighthouseSystemAligner
from cflib.localization.lighthouse_types import Pose


class TestLighthouseSystemAligner(LighthouseTestBase):
    def setUp(self):
        pass

    def test_that_transformation_is_found_for_single_points(self):
        # Fixture
        origin = (1.0, 0.0, 0.0)
        x_axis = [(1.0, 1.0, 0.0)]
        xy_plane = [(2.0, 1.0, 0.0)]

        # Test
        actual = LighthouseSystemAligner._find_transformation(origin, x_axis, xy_plane)

        # Assert
        self.assertVectorsAlmostEqual((0.0, 0.0, 0.0), actual.rotate_translate((1.0, 0.0, 0.0)))

        self.assertVectorsAlmostEqual((1.0, 0.0, 0.0), actual.rotate_translate((1.0, 1.0, 0.0)))
        self.assertVectorsAlmostEqual((0.0, 1.0, 0.0), actual.rotate_translate((0.0, 0.0, 0.0)))
        self.assertVectorsAlmostEqual((0.0, 0.0, 1.0), actual.rotate_translate((1.0, 0.0, 1.0)))

    def test_that_transformation_is_found_for_multiple_points(self):
        # Fixture
        origin = (1.0, 0.0, 0.0)
        x_axis = [(1.0, 1.0, 0.0), (1.0, 4.0, 0.0)]
        xy_plane = [(2.0, 1.0, 0.0), (3.0, -1.0, 0.0), (5.0, 0.0, 0.0)]

        # Test
        actual = LighthouseSystemAligner._find_transformation(origin, x_axis, xy_plane)

        # Assert
        self.assertVectorsAlmostEqual((0.0, 0.0, 0.0), actual.rotate_translate((1.0, 0.0, 0.0)))

        self.assertVectorsAlmostEqual((1.0, 0.0, 0.0), actual.rotate_translate((1.0, 1.0, 0.0)))
        self.assertVectorsAlmostEqual((0.0, 1.0, 0.0), actual.rotate_translate((0.0, 0.0, 0.0)))
        self.assertVectorsAlmostEqual((0.0, 0.0, 1.0), actual.rotate_translate((1.0, 0.0, 1.0)))

    def test_that_base_stations_are_rotated(self):
        # Fixture
        origin = (1.0, 0.0, 0.0)
        x_axis = [(1.0, 1.0, 0.0)]
        xy_plane = [(2.0, 1.0, 0.0)]

        bs_id = 7
        bs_poses = {bs_id: Pose.from_rot_vec(t_vec=(1.0, 0.0, 1.0))}

        # Test
        actual, transform = LighthouseSystemAligner.align(origin, x_axis, xy_plane, bs_poses)

        # Assert
        self.assertPosesAlmostEqual(Pose.from_rot_vec(
            R_vec=(0.0, 0.0, -np.pi / 2), t_vec=(0.0, 0.0, 1.0)), actual[bs_id])

    def test_that_solution_is_de_flipped(self):
        # Fixture
        origin = (0.0, 0.0, 0.0)
        x_axis = [(-1.0, 0.0, 0.0)]
        xy_plane = [(2.0, 1.0, 0.0)]

        bs_id = 7
        bs_poses = {bs_id: Pose.from_rot_vec(t_vec=(0.0, 0.0, 1.0))}
        expected = Pose.from_rot_vec(R_vec=(0.0, 0.0, np.pi), t_vec=(0.0, 0.0, 1.0))

        # Test
        actual, transform = LighthouseSystemAligner.align(origin, x_axis, xy_plane, bs_poses)

        # Assert
        self.assertPosesAlmostEqual(expected, actual[bs_id])

    def test_that_is_aligned_for_multiple_points_where_system_is_rotated_and_poins_are_fuzzy(self):
        # Fixture
        origin = (0.0, 0.0, 0.0)
        x_axis = [(-1.0, 0.0 + 0.01, 0.0), (-2.0, 0.0 - 0.02, 0.0)]
        xy_plane = [(2.0, 2.0, 0.0 + 0.02), (-3.0, -2.0, 0.0 + 0.01), (5.0, 0.0, 0.0 - 0.01)]

        # Note: Z of base stations must be positive (above the floor)
        bs_poses = {
            1: Pose.from_rot_vec(t_vec=(1.0, 0.0, 1.0)),
            2: Pose.from_rot_vec(t_vec=(0.0, 1.0, 1.0)),
            3: Pose.from_rot_vec(t_vec=(0.0, 0.0, 1.0)),
        }

        # Test
        actual, transform = LighthouseSystemAligner.align(origin, x_axis, xy_plane, bs_poses)

        # Assert
        self.assertVectorsAlmostEqual((-1.0, 0.0, 1.0), actual[1].translation, places=1)
        self.assertVectorsAlmostEqual((0.0, -1.0, 1.0), actual[2].translation, places=1)
        self.assertVectorsAlmostEqual((0.0, 0.0, 1.0), actual[3].translation, places=1)
