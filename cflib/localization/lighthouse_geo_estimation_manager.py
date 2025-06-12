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

import copy
import threading

import numpy as np
import numpy.typing as npt

from cflib.localization.lighthouse_cf_pose_sample import LhCfPoseSample
from cflib.localization.lighthouse_geometry_solver import LighthouseGeometrySolution
from cflib.localization.lighthouse_geometry_solver import LighthouseGeometrySolver
from cflib.localization.lighthouse_initial_estimator import LighthouseInitialEstimator
from cflib.localization.lighthouse_sample_matcher import LighthouseSampleMatcher
from cflib.localization.lighthouse_system_aligner import LighthouseSystemAligner
from cflib.localization.lighthouse_system_scaler import LighthouseSystemScaler
from cflib.localization.lighthouse_types import LhBsCfPoses
from cflib.localization.lighthouse_types import LhMeasurement


ArrayFloat = npt.NDArray[np.float_]


class LhGeoEstimationManager():
    REFERENCE_DIST = 1.0  # Reference distance used for scaling the solution

    @classmethod
    def align_and_scale_solution(cls, container: LhGeoInputContainerData, poses: LhBsCfPoses,
                                 reference_distance: float) -> LhBsCfPoses:

        if len(container.x_axis) == 0 or len(container.xy_plane) == 0:
            # Return unaligned solution for now
            # TODO krri Add information that the solution is not aligned
            return LhBsCfPoses(bs_poses=poses.bs_poses, cf_poses=poses.cf_poses)

        start_idx_x_axis = 1
        start_idx_xy_plane = 1 + len(container.x_axis)
        start_idx_xyz_space = start_idx_xy_plane + len(container.xy_plane)

        origin_pos = poses.cf_poses[0].translation
        x_axis_poses = poses.cf_poses[start_idx_x_axis:start_idx_x_axis + len(container.x_axis)]
        x_axis_pos = list(map(lambda x: x.translation, x_axis_poses))
        xy_plane_poses = poses.cf_poses[start_idx_xy_plane:start_idx_xyz_space]
        xy_plane_pos = list(map(lambda x: x.translation, xy_plane_poses))

        # Align the solution
        bs_aligned_poses, trnsfrm = LighthouseSystemAligner.align(origin_pos, x_axis_pos, xy_plane_pos, poses.bs_poses)
        cf_aligned_poses = list(map(trnsfrm.rotate_translate_pose, poses.cf_poses))

        # Scale the solution
        bs_scaled_poses, cf_scaled_poses, scale = LighthouseSystemScaler.scale_fixed_point(bs_aligned_poses,
                                                                                           cf_aligned_poses,
                                                                                           [reference_distance, 0, 0],
                                                                                           cf_aligned_poses[1])

        return LhBsCfPoses(bs_poses=bs_scaled_poses, cf_poses=cf_scaled_poses)

    @classmethod
    def estimate_geometry(cls, container: LhGeoInputContainerData) -> tuple[LighthouseGeometrySolution, LhBsCfPoses]:
        """Estimate the geometry of the system based on samples recorded by a Crazyflie"""
        matched_samples = container.get_matched_samples()
        initial_guess, cleaned_matched_samples = LighthouseInitialEstimator.estimate(matched_samples)

        solution = LighthouseGeometrySolver.solve(initial_guess, cleaned_matched_samples, container.sensor_positions)
        scaled_solution = cls.align_and_scale_solution(container, solution.poses, cls.REFERENCE_DIST)

        return solution, scaled_solution

    class SolverThread(threading.Thread):
        """This class runs the geometry solver in a separate thread.
        It is used to provide continuous updates of the solution as well as updating the geometry in the Crazyflie.
        """

        def __init__(self, container: LhGeoInputContainer, is_done_cb) -> None:
            """This constructor initializes the solver thread and starts it.
            It takes a container with the input data and an callback that is called when the solution is done.
            The thread will run the geometry solver and return the solution in the callback as soon as the data in the
            container is modified.
            Args:
                container (LhGeoInputContainer): A container with the input data for the geometry estimation.
                is_done_cb: Callback function that is called when the solution is done.
            """
            threading.Thread.__init__(self, name='LhGeoEstimationManager.SolverThread')

            self.container = container
            self.latest_solved_data_version = container._data.version

            self.is_done_cb = is_done_cb

            self.is_running = False
            self.is_done = False
            self.time_to_stop = False

        def run(self):
            """Run the geometry solver in a separate thread"""
            self.is_running = True

            with self.container.is_modified_condition:
                while True:
                    if self.time_to_stop:
                        break

                    if self.container._data.version > self.latest_solved_data_version:
                        self.is_done = False

                        # Copy the container as the original container may be modified while the solver is running
                        container_copy = copy.deepcopy(self.container._data)
                        solution, scaled_solution = LhGeoEstimationManager.estimate_geometry(container_copy)
                        self.latest_solved_data_version = container_copy.version

                        self.is_done = True
                        self.is_done_cb(scaled_solution)

                    self.container.is_modified_condition.wait(timeout=0.1)

            self.is_running = False

        def stop(self):
            """Stop the solver thread"""
            self.time_to_stop = True
            if self.is_running:
                self.join()


class LhGeoInputContainerData():
    def __init__(self, sensor_positions: ArrayFloat) -> None:
        self.EMPTY_POSE_SAMPLE = LhCfPoseSample(angles_calibrated={})
        self.sensor_positions = sensor_positions

        self.origin: LhCfPoseSample = self.EMPTY_POSE_SAMPLE
        self.x_axis: list[LhCfPoseSample] = []
        self.xy_plane: list[LhCfPoseSample] = []
        self.xyz_space: list[LhCfPoseSample] = []

        self.version = 0

    def get_matched_samples(self) -> list[LhCfPoseSample]:
        """Get all pose samples collected in a list

        Returns:
            list[LhCfPoseSample]: _description_
        """
        return [self.origin] + self.x_axis + self.xy_plane + self.xyz_space


class LhGeoInputContainer():
    """This class holds the input data required by the geometry estimation functionality.
    """

    def __init__(self, sensor_positions: ArrayFloat) -> None:
        self._data = LhGeoInputContainerData(sensor_positions)
        self.is_modified_condition = threading.Condition()

    def set_origin_sample(self, origin: LhCfPoseSample) -> None:
        """Store/update the sample to be used for the origin

        Args:
            origin (LhCfPoseSample): the new origin
        """
        self._data.origin = origin
        self._augment_sample(self._data.origin, True)
        self._update_version()

    def set_x_axis_sample(self, x_axis: LhCfPoseSample) -> None:
        """Store/update the sample to be used for the x_axis

        Args:
            x_axis (LhCfPoseSample): the new x-axis sample
        """
        self._data.x_axis = [x_axis]
        self._augment_samples(self._data.x_axis, True)
        self._update_version()

    def set_xy_plane_samples(self, xy_plane: list[LhCfPoseSample]) -> None:
        """Store/update the samples to be used for the xy-plane

        Args:
            xy_plane (list[LhCfPoseSample]): the new xy-plane samples
        """
        self._data.xy_plane = xy_plane
        self._augment_samples(self._data.xy_plane, True)
        self._update_version()

    def append_xy_plane_sample(self, xy_plane: LhCfPoseSample) -> None:
        """append to the samples to be used for the xy-plane

        Args:
            xy_plane (LhCfPoseSample): the new xy-plane sample
        """
        self._augment_sample(xy_plane, True)
        self._data.xy_plane.append(xy_plane)
        self._update_version()

    def set_xyz_space_samples(self, samples: list[LhMeasurement]) -> None:
        """Store/update the samples for the volume

        Args:
            samples (list[LhMeasurement]): the new samples
        """
        self._data.xyz_space = LighthouseSampleMatcher.match(samples, min_nr_of_bs_in_match=2)
        self._augment_samples(self._data.xyz_space, False)
        self._update_version()

    def append_xyz_space_samples(self, samples: list[LhMeasurement]) -> None:
        """Append to the samples for the volume

        Args:
            samples (LhMeasurement): the new samples
        """
        new_samples = LighthouseSampleMatcher.match(samples, min_nr_of_bs_in_match=2)
        self._augment_samples(new_samples, False)
        self._data.xyz_space += new_samples
        self._update_version()

    def _augment_sample(self, sample: LhCfPoseSample, is_mandatory: bool) -> None:
        sample.augment_with_ippe(self._data.sensor_positions)
        sample.is_mandatory = is_mandatory

    def _augment_samples(self, samples: list[LhCfPoseSample], is_mandatory: bool) -> None:
        for sample in samples:
            self._augment_sample(sample, is_mandatory)

    def _update_version(self) -> None:
        """Update the data version and notify the waiting thread"""
        with self.is_modified_condition:
            self._data.version += 1
            self.is_modified_condition.notify()
