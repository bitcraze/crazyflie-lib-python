from typing import NamedTuple
import numpy as np
import numpy.typing as npt

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

    def __init__(self, angles_calibrated: dict[int, LighthouseBsVectors], timestamp: float = 0.0) -> None:
        self.timestamp: float = timestamp

        # Angles measured by the Crazyflie and compensated using calibration data
        # Stored in a dictionary using base station id as the key
        self.angles_calibrated = angles_calibrated

        # A dictionary from base station id to BsPairPoses, The poses represents the two possible poses of the base
        # stations found by IPPE, in the crazyflie reference frame.
        self.ippe_solutions: dict[int, BsPairPoses] = {}

    def augment_with_ippe(self, sensor_positions: ArrayFloat) -> None:
        self.ippe_solutions = self._find_ippe_solutions(self.angles_calibrated, sensor_positions)

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
