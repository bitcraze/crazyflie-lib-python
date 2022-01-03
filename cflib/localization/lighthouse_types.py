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

from typing import NamedTuple
import numpy as np
import numpy.typing as npt

from cflib.localization.lighthouse_bs_vector import LighthouseBsVector

class Pose:
    """ Holds the full pose (position and orientation) of an object.
    Contains functionality to convert between various formats."""

    def __init__(self, R_matrix: npt.ArrayLike, t_vec: npt.ArrayLike) -> None:
        # Rotation as a matix
        self.R_matrix = np.array(R_matrix)

        # Rotation as a Rodrigues vector
        self.R_vec = None

        self.t_vec = np.array(t_vec)

    def matrix_vec():
        pass

    def rotvec_vec():
        pass

    def rotvec_vec_list():
        pass


class LhMeasurement(NamedTuple):
    """Represents a measurement from one base station."""
    timestamp: float
    base_station_id: int
    angles: LighthouseBsVector


class LhCfPoseSample:
    """ Represents a sample of a Crazyflie pose in space, it contains
    various data related to the pose such as:
    - lighthouse angles from one or more base stations
    - initial estimate of the pose
    - refined estimate of the pose
    - estimated errors
    """

    def __init__(self, timestamp: float =0.0) -> None:
        self.timestamp: float = timestamp
        self.angles_calibrated = {}
