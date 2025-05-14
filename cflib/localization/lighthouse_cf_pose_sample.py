from typing import NamedTuple

from cflib.localization.lighthouse_bs_vector import LighthouseBsVectors
from cflib.localization.lighthouse_types import Pose


class BsPairPoses(NamedTuple):
    """A type representing the poses of a pair of base stations"""
    bs1: Pose
    bs2: Pose


class LhCfPoseSample:
    """ Represents a sample of a Crazyflie pose in space, it contains
    various data related to the pose such as:
    - lighthouse angles from one or more base stations
    - The solutions found by IPPE, two solutions for each base station
    """

    def __init__(self, timestamp: float = 0.0, angles_calibrated: dict[int, LighthouseBsVectors] = None) -> None:
        self.timestamp: float = timestamp

        # Angles measured by the Crazyflie and compensated using calibration data
        # Stored in a dictionary using base station id as the key
        self.angles_calibrated: dict[int, LighthouseBsVectors] = angles_calibrated
        if self.angles_calibrated is None:
            self.angles_calibrated = {}

        # A dictionary from base station id to BsPairPoses, The poses represents the two possible poses of the base
        # stations found by IPPE, in the crazyflie reference frame.
        self.ippe_solutions: dict[int, BsPairPoses] = {}
