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

from cflib.localization.lighthouse_bs_vector import LighthouseBsVector
from cflib.localization.lighthouse_bs_vector import LighthouseBsVectors
from cflib.localization.lighthouse_types import Pose


class LighthouseCrossingBeam:
    """A class to calculate the crossing point of two "beams" from two base stations. The beams are defined by the line
    where the two light planes intersect. In a perfect world the crossing point of the two beams is the position of
    a sensor on the Crazyflie Lighthouse deck, but in reality the beams will most likely not cross and instead we
    use the closest point between the two beams as the position estimate. The (minimum) distance between the beams
    is also calculated and can be used as an error estimate for the position.
    """

    @classmethod
    def position_distance(cls,
                          bs1: Pose, angles_bs1: LighthouseBsVector,
                          bs2: Pose, angles_bs2: LighthouseBsVector) -> tuple[npt.NDArray, float]:
        """Calculate the estimated position of the crossing point of the beams
        from two base stations as well as the distance.

        Args:
            bs1 (Pose): The pose of the first base station.
            angles_bs1 (LighthouseBsVector): The sweep angles of the first base station.
            bs2 (Pose): The pose of the second base station.
            angles_bs2 (LighthouseBsVector): The sweep angles of the second base station.

        Returns:
            tuple[npt.NDArray, float]: The estimated position of the crossing point and the distance between the beams.
        """
        orig_1 = bs1.translation
        vec_1 = bs1.rot_matrix @ angles_bs1.cart

        orig_2 = bs2.translation
        vec_2 = bs2.rot_matrix @ angles_bs2.cart

        return cls._position_distance(orig_1, vec_1, orig_2, vec_2)

    @classmethod
    def position(cls,
                 bs1: Pose, angles_bs1: LighthouseBsVector,
                 bs2: Pose, angles_bs2: LighthouseBsVector) -> npt.NDArray:
        """Calculate the estimated position of the crossing point of the beams
        from two base stations.

        Args:
            bs1 (Pose): The pose of the first base station.
            angles_bs1 (LighthouseBsVector): The sweep angles of the first base station.
            bs2 (Pose): The pose of the second base station.
            angles_bs2 (LighthouseBsVector): The sweep angles of the second base station.

        Returns:
            npt.NDArray: The estimated position of the crossing point of the two beams.
        """
        position, _ = cls.position_distance(bs1, angles_bs1, bs2, angles_bs2)
        return position

    @classmethod
    def distance(cls,
                 bs1: Pose, angles_bs1: LighthouseBsVector,
                 bs2: Pose, angles_bs2: LighthouseBsVector) -> float:
        """Calculate the minimum distance between the beams from two base stations.

        Args:
            bs1 (Pose): The pose of the first base station.
            angles_bs1 (LighthouseBsVector): The sweep angles of the first base station.
            bs2 (Pose): The pose of the second base station.
            angles_bs2 (LighthouseBsVector): The sweep angles of the second base station.

        Returns:
            float: The shortest distance between the beams.
        """
        _, distance = cls.position_distance(bs1, angles_bs1, bs2, angles_bs2)
        return distance

    @classmethod
    def distances(cls,
                  bs1: Pose, angles_bs1: LighthouseBsVectors,
                  bs2: Pose, angles_bs2: LighthouseBsVectors) -> list[float]:
        """Calculate the minimum distance between the beams from two base stations for all sensors.

        Args:
            bs1 (Pose): The pose of the first base station.
            angles_bs1 (LighthouseBsVectors): The sweep angles of the first base station.
            bs2 (Pose): The pose of the second base station.
            angles_bs2 (LighthouseBsVectors): The sweep angles of the second base station.

        Returns:
            list[float]: A list of the distances.
        """
        return [cls.distance(bs1, angles1, bs2, angles2) for angles1, angles2 in zip(angles_bs1, angles_bs2)]

    @classmethod
    def max_distance(cls,
                     bs1: Pose, angles_bs1: LighthouseBsVectors,
                     bs2: Pose, angles_bs2: LighthouseBsVectors) -> float:
        """Calculate the maximum distance between the beams from two base stations for all sensors.

        Args:
            bs1 (Pose): The pose of the first base station.
            angles_bs1 (LighthouseBsVectors): The sweep angles of the first base station.
            bs2 (Pose): The pose of the second base station.
            angles_bs2 (LighthouseBsVectors): The sweep angles of the second base station.

        Returns:
            float: The maximum distance between the beams.
        """
        return max(cls.distances(bs1, angles_bs1, bs2, angles_bs2))

    @classmethod
    def max_distance_all_permutations(cls, bs_angles: list[tuple[Pose, LighthouseBsVectors]]) -> float:
        """Calculate the maximum distance between the beams from base stations for all sensors. All permutations of
        base stations are considered. This result can be used as an estimation of the maximum error.

        Args:
            bs_angles (list[tuple[Pose, LighthouseBsVectors]]): A list of tuples containing the pose of the base
            stations and their sweep angles.

        Returns:
            float: The maximum distance between the beams from all permutations of base stations.
        """
        if len(bs_angles) < 2:
            raise ValueError('At least two base stations are required to calculate the maximum distance.')

        max_distance = 0.0
        bs_count = len(bs_angles)
        for i1 in range(bs_count - 1):
            for i2 in range(i1 + 1, bs_count):
                bs1, angles_bs1 = bs_angles[i1]
                bs2, angles_bs2 = bs_angles[i2]
                # Calculate the distance for this pair of base stations
                distance = cls.max_distance(bs1, angles_bs1, bs2, angles_bs2)
                max_distance = max(max_distance, distance)

        return max_distance

    @classmethod
    def _position_distance(cls,
                           orig_1: npt.NDArray, vec_1: npt.NDArray,
                           orig_2: npt.NDArray, vec_2: npt.NDArray) -> tuple[npt.NDArray, float]:
        w0 = orig_1 - orig_2
        a = np.dot(vec_1, vec_1)
        b = np.dot(vec_1, vec_2)
        c = np.dot(vec_2, vec_2)
        d = np.dot(vec_1, w0)
        e = np.dot(vec_2, w0)

        denom = a * c - b * b

        # Closest point to line 2 on line 1
        t = (b * e - c * d) / denom
        pt1 = orig_1 + t * vec_1

        # Closest point to line 1 on line 2
        t = (a * e - b * d) / denom
        pt2 = orig_2 + t * vec_2

        # Point between the two lines
        pt = (pt1 + pt2) / 2

        # Distance between the two closest points of the beams
        distance = np.linalg.norm(pt1 - pt2)

        return pt, float(distance)
