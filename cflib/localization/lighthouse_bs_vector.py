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
from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt


class LighthouseBsVector:
    """
    This class is representing a vector from a base station into space,
    in the base station reference frame. Typically the intersection of
    two light planes defined by angles measured by a base station.
    It also provides functionality to convert between lighthouse V1 angles,
    V2 angles and cartesian coordinates.
    """

    T = math.pi / 6

    def __init__(self, lh_v1_horiz_angle: float, lh_v1_vert_angle: float) -> None:
        """
        Initialize from lighthouse V1 angles
        :param lh_v1_horiz_angle: Horizontal sweep angle, 0 straight forward. Right (seen from the bs) is negative,
                                  left is positive
        :param lh_v1_vert_angle: Vertical sweep angle, 0 straight forward. Down is negative, up is positive.
        """
        self._lh_v1_horiz_angle = lh_v1_horiz_angle
        self._lh_v1_vert_angle = lh_v1_vert_angle

    @classmethod
    def from_lh2(cls, lh_v2_angle_1: float, lh_v2_angle_2: float) -> 'LighthouseBsVector':
        """
        Create a LighthouseBsVector object from lighthouse V2 angles
        :param lh_v2_angle_1: First sweep angles, 0 straight ahead
        :param lh_v2_angle_2: Second sweep angles, 0 straight ahead
        """
        a1 = lh_v2_angle_1
        a2 = lh_v2_angle_2
        lh_v1_horiz_angle = (a1 + a2) / 2.0
        lh_v1_vert_angle = math.atan2(math.sin(a2 - a1), math.tan(cls.T) * (math.cos(a1) + math.cos(a2)))

        return cls(lh_v1_horiz_angle, lh_v1_vert_angle)

    @classmethod
    def from_cart(cls, cart_vector: list[float]) -> 'LighthouseBsVector':
        """
        Create a LighthouseBsVector object from cartesian coordinates.
        :param cart_vector: (x, y, z) to a point
        """
        lh_v1_horiz_angle = math.atan2(cart_vector[1], cart_vector[0])
        lh_v1_vert_angle = math.atan2(cart_vector[2], cart_vector[0])

        return cls(lh_v1_horiz_angle, lh_v1_vert_angle)

    @classmethod
    def from_projection(cls, proj_point: list[float]) -> 'LighthouseBsVector':
        """
        Create a LighthouseBsVector object from the projection point on the plane x=1.0
        :param projection point: (y, z)
        """
        lh_v1_horiz_angle = math.atan(proj_point[0])
        lh_v1_vert_angle = math.atan(proj_point[1])

        return cls(lh_v1_horiz_angle, lh_v1_vert_angle)

    @property
    def lh_v1_horiz_angle(self) -> float:
        """
        Lightouse V1 horizontal sweep angle
        """
        return self._lh_v1_horiz_angle

    @property
    def lh_v1_vert_angle(self) -> float:
        """
        Lightouse V1 vertical sweep angle
        """
        return self._lh_v1_vert_angle

    @property
    def lh_v1_angle_pair(self) -> tuple[float, float]:
        """
        Lightouse V1 angle pair (horiz, vert)
        """
        return self._lh_v1_horiz_angle, self._lh_v1_vert_angle,

    @property
    def lh_v2_angle_1(self) -> float:
        """
        Lightouse V2 first sweep angle
        """
        return self._lh_v1_horiz_angle + math.asin(self._q() * math.tan(-self.T))

    @property
    def lh_v2_angle_2(self) -> float:
        """
        Lightouse V2 second sweep angle
        """
        return self._lh_v1_horiz_angle + math.asin(self._q() * math.tan(self.T))

    @property
    def cart(self) -> npt.NDArray[np.float32]:
        """
        A normalized vector in cartesian coordinates
        """
        v = np.float32((1, math.tan(self._lh_v1_horiz_angle), math.tan(self._lh_v1_vert_angle)))
        return v / np.linalg.norm(v)

    @property
    def projection(self) -> npt.NDArray[np.float32]:
        """
        The 2D point (y, z) when projected on the plane x=1.0 (one meter in front of the base station)
        """
        return np.float32((math.tan(self._lh_v1_horiz_angle), math.tan(self._lh_v1_vert_angle)))

    def _q(self):
        return math.tan(self._lh_v1_vert_angle) / math.sqrt(1 + math.tan(self._lh_v1_horiz_angle) ** 2)


class LighthouseBsVectors(list):
    """A list of 4 LighthouseBsVector, one for each sensor.
       LighthouseBsVectors is essentially the same as list[LighthouseBsVector]"""

    def projection_pair_list(self) -> npt.NDArray:
        """
        Genereate a list of projection pairs for all vectors
        """
        result = np.empty((len(self), 2), dtype=float)
        for i, vector in enumerate(self):
            result[i] = vector.projection

        return result

    def angle_list(self) -> npt.NDArray:
        """
        Genereate a list of angles for all vectors, the order is horizontal, vertical, horizontal, vertical...
        """
        result = np.empty((len(self) * 2), dtype=float)
        for i, vector in enumerate(self):
            result[i * 2] = vector.lh_v1_horiz_angle
            result[i * 2 + 1] = vector.lh_v1_vert_angle

        return result
