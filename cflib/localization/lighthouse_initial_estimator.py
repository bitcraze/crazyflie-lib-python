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

import numpy as np
import numpy.typing as npt

from .ippe_cf import IppeCf
from cflib.localization.lighthouse_types import LhBsCfPoses
from cflib.localization.lighthouse_types import LhCfPoseSample
from cflib.localization.lighthouse_types import Pose


class LighthouseInitialEstimator:
    """
    Make initial estimates of base station and CF poses using IPPE (analytical solution).
    The estimates are not good enough to use for flight but is a starting point for further
    calculations.
    """

    OUTLIER_DETECTION_ERROR = 0.5

    @classmethod
    def estimate(cls, matched_samples: list[LhCfPoseSample], sensor_positions: npt.ArrayLike) -> tuple(
            LhBsCfPoses, list[LhCfPoseSample]):
        """
        Make a rough estimate of the poses of all base stations and CF poses found in the samples.

        The pose of the Crazyflie in the first sample is used as a reference and will define the
        global reference frame.

        :param matched_samples: A list of samples with lighthouse angles.
        :param sensor_positions: An array with the sensor positions on the lighthouse deck (3D, CF ref frame)
        :return: an estimate of base station and Crazyflie poses, as well as a cleaned version of matched_samples where
                 outliers are removed.
        """

        bs_positions = cls._find_solutions(matched_samples, sensor_positions)
        # bs_positions is a map from bs-id-pair to position, where the position is the position of the second
        # bs, as seen from the first bs (in the first bs ref frame).

        bs_poses_ref_cfs, cleaned_matched_samples = cls._angles_to_poses(
            matched_samples, sensor_positions, bs_positions)

        # Use the first CF pose as the global reference frame. The pose of the first base station (as estimated by ippe)
        # is used as the "true" position (reference)
        reference_bs_pose = None
        for bs_pose_ref_cfs in bs_poses_ref_cfs:
            if len(bs_pose_ref_cfs) > 0:
                bs_id, reference_bs_pose = list(bs_pose_ref_cfs.items())[0]
                break

        if reference_bs_pose is None:
            raise Exception('Too little data, no reference')
        bs_poses: dict[int, Pose] = {bs_id: reference_bs_pose}

        # Calculate the pose of the remaining base stations, based on the pose of the first CF
        cls._estimate_remaining_bs_poses(bs_poses_ref_cfs, bs_poses)

        # Now that we have estimated the base station poses, estimate the poses of the CF in all the samples
        cf_poses = cls._estimate_cf_poses(bs_poses_ref_cfs, bs_poses)

        return LhBsCfPoses(bs_poses, cf_poses), cleaned_matched_samples

    @classmethod
    def _find_solutions(cls, matched_samples: list[LhCfPoseSample], sensor_positions: npt.ArrayLike
                        ) -> dict[tuple(int, int), npt.NDArray]:
        """
        Find the pose of all base stations, in the reference frame of other base stations.

        Ippe finds two mirror solutions for each sample and the bulk of this method is geared towards finding the
        correct one. The outline of the process is:
        1. For each sample collect all possible permutations (4) of the base station positions
        2. Aggregate the possible positions of all samples in clusters. This is done per base station pair.
        3. Pick the "best" cluster as the correct permutation. The idea is that the mirror solutions will be spread
           out in space, while the correct one will end up more or less in the same spot for all samples.

        :param matched_samples: List of matched samples
        :param sensor_positions: list of sensor positions on the lighthouse deck, CF reference frame
        :return: Base stations poses in the reference frame of the other base stations. The data is organized as a
                 dictionary of tuples with base station id pairs, mapped to positions. For instance the entry with key
                 (2, 1) contains the position of base station 1, in the base station 2 reference frame.
        """

        position_permutations: dict[tuple(int, int), list[list[npt.ArrayLike]]] = {}
        for sample in matched_samples:
            solutions: dict[int, tuple[Pose, Pose]] = {}
            for bs, angles in sample.angles_calibrated.items():
                projections = angles.projection_pair_list()
                estimates_ref_bs = IppeCf.solve(sensor_positions, projections)
                estimates_ref_cf = cls._convert_estimates_to_cf_reference_frame(estimates_ref_bs)
                solutions[bs] = estimates_ref_cf

            cls._add_solution_permutations(solutions, position_permutations)

        return cls._find_most_likely_positions(position_permutations)

    @classmethod
    def _add_solution_permutations(cls, solutions: dict[int, tuple[Pose, Pose]],
                                   position_permutations: dict[tuple[int, int], list[list[npt.ArrayLike]]]):
        """
        Add the possible permutations of base station positions for a sample to a collection of aggregated positions.
        The aggregated collection contains base station positions in the reference frame of other base stations.

        :param solutions: All possible positions of the base stations, in the reference frame of the Crazyflie in one
                          sample
        :param position_permutations: Aggregated possible solutions. A dictionary with base staion pairs as keys, mapped
                                      to lists of lists of possible positions. For instance, the entry for (2, 1) would
                                      contain a list of lists with 4 positions each, for where base station 1 might be
                                      located in the base station 2 reference frame.
        """
        ids = sorted(solutions.keys())

        for i, id_i in enumerate(ids):
            solution_i = solutions[id_i]

            for j in range(i + 1, len(ids)):
                id_j = ids[j]

                solution_j = solutions[id_j]

                pose1 = solution_i[0].inv_rotate_translate_pose(solution_j[0])
                pose2 = solution_i[0].inv_rotate_translate_pose(solution_j[1])
                pose3 = solution_i[1].inv_rotate_translate_pose(solution_j[0])
                pose4 = solution_i[1].inv_rotate_translate_pose(solution_j[1])

                pair = (id_i, id_j)
                if pair not in position_permutations:
                    position_permutations[pair] = []
                position_permutations[pair].append([pose1.translation, pose2.translation,
                                                   pose3.translation, pose4.translation])

    @classmethod
    def _angles_to_poses(cls, matched_samples: list[LhCfPoseSample], sensor_positions: npt.ArrayLike,
                         bs_positions: dict[tuple(int, int), npt.NDArray]) -> tuple(list[dict[int, Pose]],
                                                                                    list[LhCfPoseSample]):
        """
        Estimate the base station poses in the Crazyflie reference frames, for each sample.

        Use Ippe again to find the possible poses of the bases stations and pick the one that best matches the position
        in bs_positions.

        :param matched_samples: List of samples
        :param sensor_positions: Positions of the sensors on the lighthouse deck (CF ref frame)
        :param bs_positions: Dictionary of base station positions (other base station ref frame)
        :return: A list of dictionaries from base station to Pose of all base stations, for each sample, as well as
                 a version of the matched_samples where outliers are removed
        """
        result: list[dict[int, Pose]] = []

        cleaned_matched_samples: list[LhCfPoseSample] = []

        for sample in matched_samples:
            solutions: dict[int, tuple[Pose, Pose]] = {}
            for bs, angles in sample.angles_calibrated.items():
                projections = angles.projection_pair_list()
                estimates_ref_bs = IppeCf.solve(sensor_positions, projections)
                estimates_ref_cf = cls._convert_estimates_to_cf_reference_frame(estimates_ref_bs)
                solutions[bs] = estimates_ref_cf

            poses: dict[int, Pose] = {}
            ids = sorted(solutions.keys())
            first = ids[0]

            for other in ids[1:]:
                pair = (first, other)
                expected = bs_positions[pair]

                firstPose, otherPose = cls._choose_solutions(solutions[first], solutions[other], expected)
                if firstPose is not None:
                    poses[first] = firstPose
                    poses[other] = otherPose
                else:
                    poses = None
                    break

            if poses is not None:
                result.append(poses)
                cleaned_matched_samples.append(sample)

        return result, cleaned_matched_samples

    @classmethod
    def _choose_solutions(cls, solutions_1: tuple[Pose, Pose], solutions_2: tuple[Pose, Pose],
                          expected: npt.ArrayLike) -> tuple[Pose, Pose]:
        """Pick the base pose solutions for a pair of base stations, based on the position in expected"""

        min_dist = 100000.0
        best1 = None
        best2 = None

        for solution_1 in solutions_1:
            for solution_2 in solutions_2:
                pose_second_bs_ref_fr_first = solution_1.inv_rotate_translate_pose(solution_2)
                dist = np.linalg.norm(expected - pose_second_bs_ref_fr_first.translation)
                if dist < min_dist:
                    min_dist = dist
                    best1 = solution_1
                    best2 = solution_2

        if min_dist > cls.OUTLIER_DETECTION_ERROR:
            return None, None

        return best1, best2

    @classmethod
    def _find_most_likely_positions(cls, position_permutations: dict[tuple(int, int),
                                    list[list[npt.ArrayLike]]]) -> dict[tuple(int, int), npt.NDArray]:
        """
        Find the most likely base station positions from all the possible permutations.

        Sort the permutations into buckets based on how close they are to the solutions in the first sample. Solutions
        that are "too" far away and distcarded. The bucket with the most samples in, is considerred the best.
        """
        result: dict[tuple(int, int), npt.NDArray] = {}

        for pair, position_lists in position_permutations.items():
            # Use first as reference to map the others to
            bucket_ref_positions = position_lists[0]
            buckets: list[list[npt.NDArray]] = [[], [], [], []]

            cls._map_positions_to_ref(bucket_ref_positions, position_lists, buckets)
            best_pos = cls._find_best_position_bucket(buckets)
            result[pair] = best_pos

        return result

    @classmethod
    def _map_positions_to_ref(cls, bucket_ref_positions: list[npt.ArrayLike], position_lists: list[list[npt.ArrayLike]],
                              buckets: list[list[npt.ArrayLike]]) -> None:
        """
        Sort solution into buckets based on the distance to the reference position. If no bucket is close enough,
        the solution is discarded.
        """

        accept_radius = 0.8

        for pos_list in position_lists:
            for pos in pos_list:
                for i, ref in enumerate(bucket_ref_positions):
                    if np.linalg.norm(pos - ref) < accept_radius:
                        buckets[i].append(pos)
                        break

    @classmethod
    def _find_best_position_bucket(cls, buckets: list[list[npt.ArrayLike]]) -> npt.NDArray:
        """
        Find the bucket with the most solutions in, this is considered to be the correct solution.
        The final result is the mean of the solution in the bucket.
        """
        max_len = 0
        max_i = 0
        for i, bucket in enumerate(buckets):
            if len(bucket) > max_len:
                max_len = len(bucket)
                max_i = i

        pos = np.mean(buckets[max_i], axis=0)
        return pos

    @classmethod
    def _convert_estimates_to_cf_reference_frame(cls, estimates_ref_bs: list[IppeCf.Solution]) -> tuple[Pose, Pose]:
        """
        Convert the two ippe solutions from the base station reference frame to the CF reference frame
        """
        rot_1 = estimates_ref_bs[0].R.transpose()
        t_1 = np.dot(rot_1, -estimates_ref_bs[0].t)

        rot_2 = estimates_ref_bs[1].R.transpose()
        t_2 = np.dot(rot_2, -estimates_ref_bs[1].t)

        return Pose(rot_1, t_1), Pose(rot_2, t_2)

    @classmethod
    def _estimate_remaining_bs_poses(cls, bs_poses_ref_cfs: list[dict[int, Pose]], bs_poses: dict[int, Pose]) -> None:
        """
        Based on one base station pose, estimate the other base staion poses.

        The process is iterative and runs until all poses are found. Assume we know the pose of base station 0, and we
        have information of base station pairs (0, 2) and (2, 3), from this we can first derive the pose of 2 and after
        that the pose of 3.
        """
        # Find all base stations in the list
        all_bs = set()
        for initial_est_bs_poses in bs_poses_ref_cfs:
            all_bs.update(initial_est_bs_poses.keys())

        # Remove the reference base stations that we already have the poses for
        to_find = all_bs - bs_poses.keys()

        # run through the list of samples until we manage to find them all
        remaining = len(to_find)
        while remaining > 0:
            buckets: dict[int, list[Pose]] = {}
            for bs_poses_in_sample in bs_poses_ref_cfs:
                unknown = to_find.intersection(bs_poses_in_sample.keys())
                known = set(bs_poses.keys()).intersection(bs_poses_in_sample.keys())

                # We need (at least) one known bs pose to use when transforming the other poses to the global ref frame
                if len(known) > 0:
                    known_bs = list(known)[0]

                    # The known BS pose in the global reference frame
                    known_global = bs_poses[known_bs]
                    # The known BS pose in the CF reference frame (of this sample)
                    known_cf = bs_poses_in_sample[known_bs]

                    for bs_id in unknown:
                        # The unknown BS pose in the CF reference frame (of this sample)
                        unknown_cf = bs_poses_in_sample[bs_id]
                        # Finally we can calculate the BS pose in the global reference frame
                        bs_pose = cls._map_pose_to_ref_frame(known_global, known_cf, unknown_cf)
                        if bs_id not in buckets:
                            buckets[bs_id] = []
                        buckets[bs_id].append(bs_pose)

            # Average over poses and add to bs_poses
            for bs_id, poses in buckets.items():
                bs_poses[bs_id] = cls._avarage_poses(poses)

            to_find = all_bs - bs_poses.keys()
            if len(to_find) == 0:
                break

            if len(to_find) == remaining:
                raise RuntimeError('Can not link positions between all base stations')

            remaining = len(to_find)

    @classmethod
    def _avarage_poses(cls, poses: list[Pose]) -> Pose:
        """
        Averaging of quaternions to get the "average" orientation of multiple samples.
        From https://stackoverflow.com/a/61013769
        """
        def q_average(Q, W=None):
            if W is not None:
                Q *= W[:, None]
            eigvals, eigvecs = np.linalg.eig(Q.T@Q)
            return eigvecs[:, eigvals.argmax()]

        positions = map(lambda x: x.translation, poses)
        average_pos = np.average(np.array(list(positions)), axis=0)

        quats = map(lambda x: x.rot_quat, poses)
        average_quaternion = q_average(np.array(list(quats)))

        return Pose.from_quat(R_quat=average_quaternion, t_vec=average_pos)

    @classmethod
    def _estimate_cf_poses(cls, bs_poses_ref_cfs: list[dict[int, Pose]], bs_poses: list[Pose]) -> list[Pose]:
        """
        Find the pose of the Crazyflie in all samples, based on the base station poses.
        """
        cf_poses: list[Pose] = []

        for est_ref_cf in bs_poses_ref_cfs:
            # Average the global pose based on all base stations
            poses = []
            for bs_id, pose_cf in est_ref_cf.items():
                pose_global = bs_poses[bs_id]
                est_ref_global = cls._map_cf_pos_to_cf_pos(pose_global, pose_cf)
                poses.append(est_ref_global)

            cf_poses.append(cls._avarage_poses(poses))

        return cf_poses

    @classmethod
    def _map_pose_to_ref_frame(cls, pose1_ref1: Pose, pose1_ref2: Pose, pose2_ref2: Pose) -> Pose:
        """
        Express pose2 in reference system 1, given pose1 in both reference system 1 and 2
        """
        R_o2_in_1, t_o2_in_1 = cls._map_cf_pos_to_cf_pos(pose1_ref1, pose1_ref2).matrix_vec

        t = np.dot(R_o2_in_1, pose2_ref2.translation) + t_o2_in_1
        R = np.dot(R_o2_in_1, pose2_ref2.rot_matrix)

        return Pose(R, t)

    @classmethod
    def _map_cf_pos_to_cf_pos(cls, pose1_ref1: Pose, pose1_ref2: Pose) -> Pose:
        """
        Find the rotation/translation from ref1 to ref2 given a pose,
        that is the returned Pose will tell us where the origin in ref2 is,
        expressed in ref1
        """

        R_inv_ref2 = np.matrix.transpose(pose1_ref2.rot_matrix)
        R = np.dot(pose1_ref1.rot_matrix, R_inv_ref2)
        t = pose1_ref1.translation - np.dot(R, pose1_ref2.translation)

        return Pose(R, t)
