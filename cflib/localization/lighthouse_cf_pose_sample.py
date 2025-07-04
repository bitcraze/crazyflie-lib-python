from typing import NamedTuple

import numpy as np
import numpy.typing as npt
import yaml

from .ippe_cf import IppeCf
from cflib.localization.lighthouse_bs_vector import LighthouseBsVectors
from cflib.localization.lighthouse_types import Pose

ArrayFloat = npt.NDArray[np.float_]


class BsPairPoses(NamedTuple):
    """A type representing the poses of a pair of base stations"""
    bs1: Pose
    bs2: Pose


class LhCfPoseSample:
    """ Represents a sample of a Crazyflie pose in space, it contains:
    - a timestamp (if applicable)
    - lighthouse angles from one or more base stations
    - The the two solutions found by IPPE for each base station, in the cf ref frame.

    The ippe solution is somewhat heavy and is only created on demand by calling augment_with_ippe()
    """

    def __init__(self, angles_calibrated: dict[int, LighthouseBsVectors], timestamp: float = 0.0,
                 is_mandatory: bool = False) -> None:
        self.timestamp: float = timestamp

        # Angles measured by the Crazyflie and compensated using calibration data
        # Stored in a dictionary using base station id as the key
        self.angles_calibrated: dict[int, LighthouseBsVectors] = angles_calibrated

        # A dictionary from base station id to BsPairPoses, The poses represents the two possible poses of the base
        # stations found by IPPE, in the crazyflie reference frame.
        self.ippe_solutions: dict[int, BsPairPoses] = {}
        self.is_augmented = False

        # Some samples are mandatory and must not be removed, even if they appear to be outliers. For instance the
        # the samples that define the origin or x-axis
        self.is_mandatory = is_mandatory

    def augment_with_ippe(self, sensor_positions: ArrayFloat) -> None:
        if not self.is_augmented:
            self.ippe_solutions = self._find_ippe_solutions(self.angles_calibrated, sensor_positions)
            self.is_augmented = True

    def is_empty(self) -> bool:
        """Checks if no angles are set

        Returns:
            bool: True if no angles are set
        """
        return len(self.angles_calibrated) == 0

    def _find_ippe_solutions(self, angles_calibrated: dict[int, LighthouseBsVectors],
                             sensor_positions: ArrayFloat) -> dict[int, BsPairPoses]:

        solutions: dict[int, BsPairPoses] = {}
        for bs, angles in angles_calibrated.items():
            projections = angles.projection_pair_list()
            estimates_ref_bs = IppeCf.solve(sensor_positions, projections)
            estimates_ref_cf = self._convert_estimates_to_cf_reference_frame(estimates_ref_bs)
            solutions[bs] = estimates_ref_cf

        return solutions

    def _convert_estimates_to_cf_reference_frame(self, estimates_ref_bs: list[IppeCf.Solution]) -> BsPairPoses:
        """
        Convert the two ippe solutions from the base station reference frame to the CF reference frame
        """
        rot_1 = estimates_ref_bs[0].R.transpose()
        t_1 = np.dot(rot_1, -estimates_ref_bs[0].t)

        rot_2 = estimates_ref_bs[1].R.transpose()
        t_2 = np.dot(rot_2, -estimates_ref_bs[1].t)

        return BsPairPoses(Pose(rot_1, t_1), Pose(rot_2, t_2))

    def __eq__(self, other):
        if not isinstance(other, LhCfPoseSample):
            return NotImplemented

        return (self.timestamp == other.timestamp and
                self.angles_calibrated == other.angles_calibrated and
                self.is_mandatory == other.is_mandatory)

    @staticmethod
    def yaml_representer(dumper, data: 'LhCfPoseSample'):
        return dumper.represent_mapping('!LhCfPoseSample', {
            'timestamp': data.timestamp,
            'angles_calibrated': data.angles_calibrated,
            'is_mandatory': data.is_mandatory
        })

    @staticmethod
    def yaml_constructor(loader, node):
        values = loader.construct_mapping(node, deep=True)
        timestamp = values.get('timestamp', 0.0)
        angles_calibrated = values.get('angles_calibrated', {})
        is_mandatory = values.get('is_mandatory', False)
        return LhCfPoseSample(angles_calibrated, timestamp, is_mandatory)


yaml.add_representer(LhCfPoseSample, LhCfPoseSample.yaml_representer)
yaml.add_constructor('!LhCfPoseSample', LhCfPoseSample.yaml_constructor)
