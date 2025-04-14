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
import unittest

import numpy as np
import numpy.typing as npt
from scipy.spatial.transform import Rotation

from cflib.localization.lighthouse_types import Pose


class LighthouseTestBase(unittest.TestCase):
    """
    Utilitis to simplify testing of lighthouse code
    """

    def assertVectorsAlmostEqual(self, expected: npt.ArrayLike, actual: npt.ArrayLike, places: int = 5) -> None:
        _expected = np.array(expected)
        _actual = np.array(actual)

        self.assertEqual(_expected.shape[0], _actual.shape[0], 'Shape differs')

        for i in range(_expected.shape[0]):
            self.assertAlmostEqual(_expected[i], _actual[i], places, f'Lists differs in element {i}')

    def assertPosesAlmostEqual(self, expected: Pose, actual: Pose, places: int = 5):
        translation_diff = expected.translation - actual.translation
        self.assertAlmostEqual(0.0, np.linalg.norm(translation_diff), places,
                               f'Translation different, expected: {expected.translation}, actual: {actual.translation}')

        _expected_rot = Rotation.from_rotvec(expected.rot_vec)
        _actual_rot = Rotation.from_rotvec(actual.rot_vec)

        # Compute the rotation needed to go from expected to actual.
        # This avoids sign ambiguity in rotvecs (e.g., π vs. -π) by comparing actual orientation difference.
        _relative_rot = _expected_rot.inv() * _actual_rot

        angle_diff = _relative_rot.magnitude()
        self.assertAlmostEqual(0.0, angle_diff, places,
                               f'Rotation different, expected: {expected.rot_vec}, actual: {actual.rot_vec}')
