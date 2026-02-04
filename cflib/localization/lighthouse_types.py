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

from typing import NamedTuple

import numpy as np
import numpy.typing as npt
import yaml
from scipy.spatial.transform import Rotation

from cflib.localization.lighthouse_bs_vector import LighthouseBsVectors


class Pose:
    """ Holds the full pose (position and orientation) of an object.
    Contains functionality to convert between various formats."""

    _NO_ROTATION_MTX = np.identity(3)
    _NO_ROTATION_VCT = np.array((0.0, 0.0, 0.0))
    _NO_ROTATION_QUAT = np.array((0.0, 0.0, 0.0, 0.0))
    _ORIGIN = np.array((0.0, 0.0, 0.0))

    def __init__(self, R_matrix: npt.ArrayLike = _NO_ROTATION_MTX, t_vec: npt.ArrayLike = _ORIGIN) -> None:
        # Rotation as a matix
        self._R_matrix = np.array(R_matrix)

        # Translation vector
        self._t_vec = np.array(t_vec)

    @classmethod
    def from_rot_vec(cls, R_vec: npt.ArrayLike = _NO_ROTATION_VCT, t_vec: npt.ArrayLike = _ORIGIN) -> 'Pose':
        """
        Create a Pose from a rotation vector and translation vector
        """
        return Pose(Rotation.from_rotvec(R_vec).as_matrix(), t_vec)

    @classmethod
    def from_quat(cls, R_quat: npt.ArrayLike = _NO_ROTATION_QUAT, t_vec: npt.ArrayLike = _ORIGIN) -> 'Pose':
        """
        Create a Pose from a quaternion and translation vector
        """
        return Pose(Rotation.from_quat(R_quat).as_matrix(), t_vec)

    @classmethod
    def from_rpy(cls, roll: float = 0.0, pitch: float = 0.0, yaw: float = 0.0, t_vec: npt.ArrayLike = _ORIGIN,
                 seq: str='xyz', degrees: bool=False,) -> 'Pose':
        """Create a Pose from roll, pitch and yaw angles and translation vector

        Args:
            roll (float, optional): Roll angle. Defaults to 0.0.
            pitch (float, optional): _Pitch angle. Defaults to 0.0.
            yaw (float, optional): Yaw angle. Defaults to 0.0.
            t_vec (npt.ArrayLike, optional): Position vector. Defaults to _ORIGIN.
            seq (str, optional): The order of roll, pitch and yaw, see scipy documentation for Rotation.from_euler.
            degrees (bool, optional): Whether the angles are in degrees. Defaults to False.

        Returns:
            Pose: The created Pose object
        """

        return Pose(Rotation.from_euler(seq, [roll, pitch, yaw], degrees=degrees).as_matrix(), t_vec)

    @classmethod
    def from_cf_rpy(cls, roll: float = 0.0, pitch: float = 0.0, yaw: float = 0.0, t_vec: npt.ArrayLike = _ORIGIN) -> 'Pose':
        """Create a Pose from roll, pitch and yaw angles in the Crazyflie convention and translation vector

        Args:
            roll (float, optional): Roll angle as used in the CF (degrees). Defaults to 0.0.
            pitch (float, optional): Pitch angle as used in the CF (degrees). Defaults to 0.0.
            yaw (float, optional): Yaw angle as used in the CF (degrees). Defaults to 0.0.
            t_vec (npt.ArrayLike, optional): Position vector. Defaults to _ORIGIN.

        Returns:
            Pose: The created Pose object
        """

        return Pose.from_rpy(roll, -pitch, yaw, t_vec, seq='xyz', degrees=True)

    def scale(self, scale) -> None:
        """
        quiet
        """
        self._t_vec = self._t_vec * scale

    @property
    def rot_matrix(self) -> npt.NDArray:
        """
        Get the rotation matrix of the pose
        """
        return self._R_matrix

    @property
    def rot_vec(self) -> npt.NDArray:
        """
        Get the rotation vector of the pose
        """
        return Rotation.from_matrix(self._R_matrix).as_rotvec()

    @property
    def rot_quat(self) -> npt.NDArray:
        """
        Get the quaternion of the pose
        """
        return Rotation.from_matrix(self._R_matrix).as_quat()

    def rot_euler(self, seq: str='xyz', degrees: bool=False) -> npt.NDArray:
        """ Get the euler angles of the pose

        Args:
            seq (str, optional): The order of roll, pitch and yaw, see scipy documentation for Rotation.as_euler.
                                 use 'xyz' for the Crazyflie convention (default).
            degrees (bool, optional): Whether to return the angles in degrees. Defaults to False.

        Returns:
            npt.NDArray: The euler angles of the pose
        """
        return Rotation.from_matrix(self._R_matrix).as_euler(seq, degrees=degrees)

    @property
    def rot_cf_rpy(self) -> tuple[float, float, float]:
        """ Get roll, pitch and yaw of the pose in the Crazyflie convention (degrees)

        Returns:
            tuple[float, float, float]: roll, pitch, yaw in degrees as used in the CF
        """
        rpy = self.rot_euler(seq='xyz', degrees=True)
        return (rpy[0], -rpy[1], rpy[2])

    @property
    def translation(self) -> npt.NDArray:
        """
        Get the translation vector of the pose
        """
        return self._t_vec

    @property
    def matrix_vec(self) -> tuple[npt.NDArray, npt.NDArray]:
        """
        Get the pose as a rotation matrix and translation vector
        """
        return self._R_matrix, self._t_vec

    def rotate_translate(self, point: npt.ArrayLike) -> npt.NDArray:
        """
        Rotate and translate a point, that is transform from local
        to global reference frame
        """
        return np.dot(self.rot_matrix, point) + self.translation

    def inv_rotate_translate(self, point: npt.ArrayLike) -> npt.NDArray:
        """
        Inverse rotate and translate a point, that is transform from global
        to local reference frame
        """
        return np.dot(np.transpose(self.rot_matrix), point - self.translation)

    def rotate_translate_pose(self, pose: 'Pose') -> 'Pose':
        """
        Rotate and translate a pose
        """
        t = np.dot(self.rot_matrix, pose.translation) + self.translation
        R = np.dot(self.rot_matrix, pose.rot_matrix)

        return Pose(R_matrix=R, t_vec=t)

    def inv_rotate_translate_pose(self, pose: 'Pose') -> 'Pose':
        """
        Inverse rotate and translate a point, that is transform from global
        to local reference frame
        """
        inv_rot_matrix = np.transpose(self.rot_matrix)
        t = np.dot(inv_rot_matrix, pose.translation - self.translation)
        R = np.dot(inv_rot_matrix, pose.rot_matrix)

        return Pose(R_matrix=R, t_vec=t)

    def __eq__(self, other):
        if not isinstance(other, Pose):
            return NotImplemented

        return np.array_equal(self._R_matrix, other._R_matrix) and np.array_equal(self._t_vec, other._t_vec)

    @staticmethod
    def yaml_representer(dumper, data: Pose):
        """Represent a Pose object in YAML"""
        return dumper.represent_mapping('!Pose', {
            'R_matrix': data.rot_matrix.tolist(),
            't_vec': data.translation.tolist()
        })

    @staticmethod
    def yaml_constructor(loader, node):
        """Construct a Pose object from YAML"""
        values = loader.construct_mapping(node, deep=True)
        R_matrix = np.array(values['R_matrix'])
        t_vec = np.array(values['t_vec'])
        return Pose(R_matrix=R_matrix, t_vec=t_vec)


yaml.add_representer(Pose, Pose.yaml_representer)
yaml.add_constructor('!Pose', Pose.yaml_constructor)


class LhMeasurement(NamedTuple):
    """Represents a measurement from one base station."""
    timestamp: float
    base_station_id: int
    angles: LighthouseBsVectors


class LhDeck4SensorPositions:
    """ Positions of the sensors on the Lighthouse 4 deck """
    # Sensor distances on the lighthouse deck
    _sensor_distance_width = 0.015
    _sensor_distance_length = 0.03

    # Sensor positions in the Crazyflie reference frame
    positions = np.array([
        (-_sensor_distance_length / 2, _sensor_distance_width / 2, 0.0),
        (-_sensor_distance_length / 2, -_sensor_distance_width / 2, 0.0),
        (_sensor_distance_length / 2, _sensor_distance_width / 2, 0.0),
        (_sensor_distance_length / 2, -_sensor_distance_width / 2, 0.0)])

    diagonal_distance = np.sqrt(_sensor_distance_length ** 2 + _sensor_distance_length ** 2)


class LhException(RuntimeError):
    """Base exception for lighthouse exceptions"""
