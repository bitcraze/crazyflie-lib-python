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

import copy

import numpy as np
import numpy.typing as npt

from cflib.localization.lighthouse_bs_vector import LighthouseBsVector
from cflib.localization.lighthouse_types import LhCfPoseSample
from cflib.localization.lighthouse_types import Pose


class LighthouseSystemScaler:
    """This class is used to re-scale a system based on various measurements."""
    @classmethod
    def scale_fixed_point(cls, bs_poses: dict[int, Pose], cf_poses: list[Pose], expected: npt.ArrayLike,
                          actual: Pose) -> tuple[dict[int, Pose], list[Pose], float]:
        """
        Scale a system based on a position in the physical world in relation to where it is in the estimated system
        geometry. Assume the system is aligned and simply use the distance to the points for scaling.

        :param bs_poses: a dictionary with the base station poses in the current reference frame
        :param cf_poses: List of CF poses
        :param expected: The real world position to use as reference
        :param actual: The estimated position in the current system geometry
        :return: a tuple containing a dictionary with the base station poses in the scaled system,
                 a list of Crazyflie poses in the scaled system and the scaling factor
        """
        expected_distance = np.linalg.norm(expected)
        actual_distance = np.linalg.norm(actual.translation)
        scale_factor = expected_distance / actual_distance
        return cls._scale_system(bs_poses, cf_poses, scale_factor)

    @classmethod
    def scale_diagonals(cls, bs_poses: dict[int, Pose], cf_poses: list[Pose], matched_samples: list[LhCfPoseSample],
                        expected_diagonal: float) -> tuple[dict[int, Pose], list[Pose], float]:
        """
        Scale a system based on where base station "rays" intersects the lighthouse deck in relation to sensor
        positions. Calculates the intersection points for all samples and scales the system to match the expected
        distance between sensors on the deck.

        :param bs_poses: a dictionary with the base station poses in the current reference frame
        :param cf_poses: List of CF poses
        :param matched_samples: List of samples. Length must be the same as cf_poses.
        :return: a tuple containing a dictionary with the base station poses in the scaled system,
                 a list of Crazyflie poses in the scaled system and the scaling factor
        """

        estimated_diagonal = cls._calculate_mean_diagonal(bs_poses, cf_poses, matched_samples)
        scale_factor = expected_diagonal / estimated_diagonal
        return cls._scale_system(bs_poses, cf_poses, scale_factor)

    @classmethod
    def _scale_system(cls, bs_poses: dict[int, Pose], cf_poses: list[Pose],
                      scale_factor: float) -> tuple[dict[int, Pose], list[Pose], float]:
        """
        Scale poses of base stations and crazyflie samples.
        """
        bs_scaled = {bs_id: copy.copy(pose) for bs_id, pose in bs_poses.items()}
        for pose in bs_scaled.values():
            pose.scale(scale_factor)

        cf_scaled = [copy.copy(pose) for pose in cf_poses]
        for pose in cf_scaled:
            pose.scale(scale_factor)

        return bs_scaled, cf_scaled, scale_factor

    @classmethod
    def _calculate_mean_diagonal(cls, bs_poses: dict[int, Pose], cf_poses: list[Pose],
                                 matched_samples: list[LhCfPoseSample]) -> float:
        """
        Calculate the average diagonal sensor distance based on where the rays intersect the lighthouse deck
        """
        diagonals: list[float] = []

        for cf_pose, sample in zip(cf_poses, matched_samples):
            for bs_id, vectors in sample.angles_calibrated.items():
                diagonals.append(cls.calc_intersection_distance(vectors[0], vectors[3], bs_poses[bs_id], cf_pose))
                diagonals.append(cls.calc_intersection_distance(vectors[1], vectors[2], bs_poses[bs_id], cf_pose))

        estimated_diagonal = np.mean(diagonals)

        return estimated_diagonal

    @classmethod
    def calc_intersection_distance(cls, vector1: LighthouseBsVector, vector2: LighthouseBsVector,
                                   bs_pose: Pose, cf_pose: Pose) -> float:
        """Calculate distance between intersection points of rays on the plane defined by the lighthouse deck"""

        intersection1 = cls.calc_intersection_point(vector1, bs_pose, cf_pose)
        intersection2 = cls.calc_intersection_point(vector2, bs_pose, cf_pose)
        distance = np.linalg.norm(intersection1 - intersection2)
        return distance

    @classmethod
    def calc_intersection_point(cls, vector: LighthouseBsVector, bs_pose: Pose, cf_pose: Pose) -> npt.NDArray:
        """Calculate the intersetion point of a lines and a plane.
        The line is the intersection of the two light planes from a base station, while the
        plane is defined by the lighthouse deck of the Crazyflie."""

        plane_base = cf_pose.translation
        plane_normal = np.dot(cf_pose.rot_matrix, (0.0, 0.0, 1.0))

        line_base = bs_pose.translation
        line_vector = np.dot(bs_pose.rot_matrix, vector.cart)

        dist_on_line = np.dot((plane_base - line_base), plane_normal) / np.dot(line_vector, plane_normal)

        return line_base + line_vector * dist_on_line
