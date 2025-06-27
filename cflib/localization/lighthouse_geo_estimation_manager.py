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
from cflib.localization.lighthouse_geometry_solution import LighthouseGeometrySolution
from cflib.localization.lighthouse_geometry_solver import LighthouseGeometrySolver
from cflib.localization.lighthouse_initial_estimator import LighthouseInitialEstimator
from cflib.localization.lighthouse_system_aligner import LighthouseSystemAligner
from cflib.localization.lighthouse_system_scaler import LighthouseSystemScaler
from cflib.localization.lighthouse_types import LhBsCfPoses


ArrayFloat = npt.NDArray[np.float_]


class LhGeoEstimationManager():
    REFERENCE_DIST = 1.0  # Reference distance used for scaling the solution

    @classmethod
    def align_and_scale_solution(cls, container: LhGeoInputContainerData, poses: LhBsCfPoses,
                                 reference_distance: float) -> LhBsCfPoses:
        start_idx_x_axis = 1
        start_idx_xy_plane = start_idx_x_axis + len(container.x_axis)
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
    def estimate_geometry(cls, container: LhGeoInputContainerData) -> LighthouseGeometrySolution:
        """Estimate the geometry of the system based on samples recorded by a Crazyflie"""
        solution = LighthouseGeometrySolution()

        matched_samples = container.get_matched_samples()
        solution.progress_info = 'Data validation'
        validated_matched_samples = cls._data_validation(matched_samples, container, solution)
        if solution.progress_is_ok:
            solution.progress_info = 'Initial estimation of geometry'
            initial_guess, cleaned_matched_samples = LighthouseInitialEstimator.estimate(validated_matched_samples,
                                                                                         solution)
            solution.poses = initial_guess

            if solution.progress_is_ok:
                solution.progress_info = 'Refining geometry solution'
                LighthouseGeometrySolver.solve(initial_guess, cleaned_matched_samples, container.sensor_positions,
                                               solution)
                solution.progress_info = 'Align and scale solution'
                scaled_solution = cls.align_and_scale_solution(container, solution.poses, cls.REFERENCE_DIST)
                solution.poses = scaled_solution

        cls._humanize_error_info(solution, container)

        # TODO krri indicate in the solution if there is a geometry. progress_is_ok is not a good indicator

        return solution

    @classmethod
    def _data_validation(cls, matched_samples: list[LhCfPoseSample], container: LhGeoInputContainerData,
                         solution: LighthouseGeometrySolution) -> list[LhCfPoseSample]:
        """Validate the data collected by the Crazyflie and update the solution object with the results"""

        result = []

        NO_DATA = 'No data'
        TOO_FEW_BS = 'Too few base stations recorded'

        # Check the origin sample
        origin = container.origin
        if len(origin.angles_calibrated) == 0:
            solution.append_mandatory_issue_sample(origin, NO_DATA)
        elif len(origin.angles_calibrated) == 1:
            solution.append_mandatory_issue_sample(origin, TOO_FEW_BS)

        # Check the x-axis samples
        if len(container.x_axis) == 0:
            solution.is_x_axis_samples_valid = False
            solution.x_axis_samples_info = NO_DATA
            solution.progress_is_ok = False

        if len(container.xy_plane) == 0:
            solution.is_xy_plane_samples_valid = False
            solution.xy_plane_samples_info = NO_DATA
            solution.progress_is_ok = False

        if len(container.xyz_space) == 0:
            solution.xyz_space_samples_info = NO_DATA

        # Samples must contain at least two base stations
        for sample in matched_samples:
            if sample == container.origin:
                result.append(sample)
                continue  # The origin sample is already checked

            if len(sample.angles_calibrated) >= 2:
                result.append(sample)
            else:
                # If the sample is mandatory, we cannot remove it, but we can add an issue to the solution
                if sample.is_mandatory:
                    solution.append_mandatory_issue_sample(sample, TOO_FEW_BS)
                else:
                    # If the sample is not mandatory, we can ignore it
                    solution.xyz_space_samples_info = 'Sample(s) with too few base stations skipped'
                    continue

        return result

    @classmethod
    def _humanize_error_info(cls, solution: LighthouseGeometrySolution, container: LhGeoInputContainerData) -> None:
        """Humanize the error info in the solution object"""

        # There might already be an error reported earlier, so only check if we think the sample is valid
        if solution.is_origin_sample_valid:
            solution.is_origin_sample_valid, solution.origin_sample_info = cls._error_info_for(solution,
                                                                                               [container.origin])
        if solution.is_x_axis_samples_valid:
            solution.is_x_axis_samples_valid, solution.x_axis_samples_info = cls._error_info_for(solution,
                                                                                                 container.x_axis)
        if solution.is_xy_plane_samples_valid:
            solution.is_xy_plane_samples_valid, solution.xy_plane_samples_info = cls._error_info_for(solution,
                                                                                                     container.xy_plane)

    @classmethod
    def _error_info_for(cls, solution: LighthouseGeometrySolution, samples: list[LhCfPoseSample]) -> tuple[bool, str]:
        """Check if any issue sample is registered and return a human readable error message"""
        info_strings = []
        for sample in samples:
            for issue_sample, issue in solution.mandatory_issue_samples:
                if sample == issue_sample:
                    info_strings.append(issue)

        if len(info_strings) > 0:
            return False, ', '.join(info_strings)
        else:
            return True, ''

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
            self.daemon = True

            self.container = container
            self.latest_solved_data_version = -1

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

                    if self.container.get_data_version() > self.latest_solved_data_version:
                        self.is_done = False

                        # Copy the container as the original container may be modified while the solver is running
                        container_copy = self.container.get_data_copy()
                        solution = LhGeoEstimationManager.estimate_geometry(container_copy)
                        self.latest_solved_data_version = container_copy.version

                        self.is_done = True
                        self.is_done_cb(solution)

                    self.container.is_modified_condition.wait(timeout=0.1)

            self.is_running = False

        def stop(self, do_join: bool = True):
            """Stop the solver thread"""
            self.time_to_stop = True
            if do_join:
                # Wait for the thread to finish
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

    def xy_plane_sample_count(self) -> int:
        """Get the number of samples in the xy-plane

        Returns:
            int: The number of samples in the xy-plane
        """
        return len(self._data.xy_plane)

    def set_xyz_space_samples(self, samples: list[LhCfPoseSample]) -> None:
        """Store/update the samples for the volume

        Args:
            samples (list[LhMeasurement]): the new samples
        """
        self._data.xyz_space = []
        self.append_xyz_space_samples(samples)

    def append_xyz_space_samples(self, samples: list[LhCfPoseSample]) -> None:
        """Append to the samples for the volume

        Args:
            samples (LhMeasurement): the new samples
        """
        new_samples = samples
        self._augment_samples(new_samples, False)
        self._data.xyz_space += new_samples
        self._update_version()

    def xyz_space_sample_count(self) -> int:
        """Get the number of samples in the xyz space

        Returns:
            int: The number of samples in the xyz space
        """
        return len(self._data.xyz_space)

    def clear_all_samples(self) -> None:
        """Clear all samples in the container"""
        self._data.origin = self._data.EMPTY_POSE_SAMPLE
        self._data.x_axis = []
        self._data.xy_plane = []
        self._data.xyz_space = []
        self._update_version()

    def _augment_sample(self, sample: LhCfPoseSample, is_mandatory: bool) -> None:
        sample.augment_with_ippe(self._data.sensor_positions)
        sample.is_mandatory = is_mandatory

    def _augment_samples(self, samples: list[LhCfPoseSample], is_mandatory: bool) -> None:
        for sample in samples:
            self._augment_sample(sample, is_mandatory)

    def get_data_version(self) -> int:
        """Get the current data version

        Returns:
            int: The current data version
        """
        return self._data.version

    def get_data_copy(self) -> LhGeoInputContainerData:
        """Get a copy of the data in the container

        Returns:
            LhGeoInputContainerData: A copy of the data in the container
        """
        return copy.deepcopy(self._data)

    def _update_version(self) -> None:
        """Update the data version and notify the waiting thread"""
        with self.is_modified_condition:
            self._data.version += 1
            self.is_modified_condition.notify()
