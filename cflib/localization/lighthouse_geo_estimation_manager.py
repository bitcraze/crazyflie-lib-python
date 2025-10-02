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
import datetime
import os
import pathlib
import threading
from typing import TextIO

import numpy as np
import numpy.typing as npt
import yaml

from cflib.localization.lighthouse_cf_pose_sample import LhCfPoseSample
from cflib.localization.lighthouse_cf_pose_sample import LhCfPoseSampleStatus
from cflib.localization.lighthouse_cf_pose_sample import LhCfPoseSampleType
from cflib.localization.lighthouse_cf_pose_sample import LhCfPoseSampleWrapper
from cflib.localization.lighthouse_geometry_solution import LighthouseGeometrySolution
from cflib.localization.lighthouse_geometry_solver import LighthouseGeometrySolver
from cflib.localization.lighthouse_initial_estimator import LighthouseInitialEstimator
from cflib.localization.lighthouse_system_aligner import LighthouseSystemAligner
from cflib.localization.lighthouse_system_scaler import LighthouseSystemScaler
from cflib.localization.lighthouse_types import Pose
from cflib.localization.lighthouse_utils import LighthouseCrossingBeam


ArrayFloat = npt.NDArray[np.float64]


class LhGeoEstimationManager():
    REFERENCE_DIST = 1.0  # Reference distance used for scaling the solution

    ESTIMATION_TYPES = (LhCfPoseSampleType.ORIGIN,
                        LhCfPoseSampleType.X_AXIS,
                        LhCfPoseSampleType.XY_PLANE,
                        LhCfPoseSampleType.XYZ_SPACE)

    @classmethod
    def align_and_scale_solution(cls, container: LhGeoInputContainerData, solution: LighthouseGeometrySolution,
                                 samples: list[LhCfPoseSampleWrapper], reference_distance: float):
        bs_poses = solution.bs_poses

        # Note: samples is a subset of solution.samples but samples are never removed from origin, x-axis or xy-plane
        # so we can use the number of samples in the container to determine the indices in the sample list.

        origin_pos = samples[container.origin_index].pose.translation
        x_axis_samples = samples[container.x_axis_slice]
        x_axis_pos = list(map(lambda x: x.pose.translation, x_axis_samples))
        xy_plane_samples = samples[container.xy_plane_slice]
        xy_plane_pos = list(map(lambda x: x.pose.translation, xy_plane_samples))

        # Align the solution
        bs_aligned_poses, trnsfrm = LighthouseSystemAligner.align(origin_pos, x_axis_pos, xy_plane_pos, bs_poses)
        cf_aligned_poses = list(map(lambda sample: trnsfrm.rotate_translate_pose(sample.pose), samples))

        # Scale the solution
        bs_scaled_poses, cf_scaled_poses, scale = LighthouseSystemScaler.scale_fixed_point(bs_aligned_poses,
                                                                                           cf_aligned_poses,
                                                                                           [reference_distance, 0, 0],
                                                                                           cf_aligned_poses[1])

        # Update the solution with the aligned and scaled poses
        solution.bs_poses = bs_scaled_poses
        for sample, pose in zip(samples, cf_scaled_poses):
            sample.pose = pose

    @classmethod
    def estimate_geometry(cls, container: LhGeoInputContainerData) -> LighthouseGeometrySolution:
        """Estimate the geometry of the system based on samples recorded by a Crazyflie"""
        matched_samples = container.get_matched_samples()
        solution = LighthouseGeometrySolution(samples=matched_samples)

        solution.progress_info = 'Data validation'
        validated_matched_samples = cls._data_validation(matched_samples, container, solution)
        if solution.progress_is_ok:
            solution.progress_info = 'Initial estimation of geometry'
            cleaned_matched_samples = LighthouseInitialEstimator.estimate(validated_matched_samples, solution)
            if solution.progress_is_ok:
                solution.progress_info = 'Refining geometry solution'
                LighthouseGeometrySolver.solve(cleaned_matched_samples, container.sensor_positions, solution)
                solution.progress_info = 'Align and scale solution'
                cls.align_and_scale_solution(container, solution, validated_matched_samples,
                                             cls.REFERENCE_DIST)

                cls._create_solution_stats(validated_matched_samples, solution)
                cls._create_verification_stats(solution)

        cls._humanize_error_info(solution, container)

        return solution

    @classmethod
    def _data_validation(cls, matched_samples: list[LhCfPoseSampleWrapper], container: LhGeoInputContainerData,
                         solution: LighthouseGeometrySolution) -> list[LhCfPoseSampleWrapper]:
        """Validate the data collected by the Crazyflie and update the solution object with the results.
        Filter out samples that will not be used for the geometry estimation."""

        result = []

        NO_DATA = 'No data'

        # Check the origin sample
        if len(matched_samples) == 0:
            solution.is_origin_sample_valid = False
            solution.origin_sample_info = NO_DATA
            solution.progress_is_ok = False
            return result
        else:
            origin = matched_samples[0]
            if len(origin.angles_calibrated) == 0:
                origin.status = LhCfPoseSampleStatus.NO_DATA
                solution.progress_is_ok = False
            elif len(origin.angles_calibrated) < 2:
                origin.status = LhCfPoseSampleStatus.TOO_FEW_BS
                solution.progress_is_ok = False

            result.append(origin)

        # Check the x-axis samples
        if container.x_axis_sample_count == 0:
            solution.is_x_axis_samples_valid = False
            solution.x_axis_samples_info = NO_DATA
            solution.progress_is_ok = False

        # Check the xy-plane samples
        if container.xy_plane_sample_count == 0:
            solution.is_xy_plane_samples_valid = False
            solution.xy_plane_samples_info = NO_DATA
            solution.progress_is_ok = False

        # Check the xyz-space samples
        if container.xyz_space_sample_count == 0:
            solution.xyz_space_samples_info = NO_DATA

        # Samples must contain at least two base stations.
        # Skip the origin sample as it is already checked above.
        for sample in matched_samples[1:]:
            if len(sample.angles_calibrated) >= 2:
                if sample.sample_type in cls.ESTIMATION_TYPES:
                    result.append(sample)
            else:
                sample.status = LhCfPoseSampleStatus.TOO_FEW_BS

                # If the sample is mandatory, we cannot remove it, but we can add an issue to the solution
                if sample.is_mandatory:
                    result.append(sample)
                    solution.progress_is_ok = False

        return result

    @classmethod
    def _humanize_error_info(cls, solution: LighthouseGeometrySolution, container: LhGeoInputContainerData) -> None:
        """Humanize the error info in the solution object"""

        # There might already be an error reported earlier, so only check if we think the sample is valid
        if solution.is_origin_sample_valid:
            solution.is_origin_sample_valid, solution.origin_sample_info = cls._error_info_for(
                solution, LhCfPoseSampleType.ORIGIN)
        if solution.is_x_axis_samples_valid:
            solution.is_x_axis_samples_valid, solution.x_axis_samples_info = cls._error_info_for(
                solution, LhCfPoseSampleType.X_AXIS)
        if solution.is_xy_plane_samples_valid:
            solution.is_xy_plane_samples_valid, solution.xy_plane_samples_info = cls._error_info_for(
                solution, LhCfPoseSampleType.XY_PLANE)

    @classmethod
    def _error_info_for(cls, solution: LighthouseGeometrySolution, sample_type: LhCfPoseSampleType) -> tuple[bool, str]:
        """Check if any issue sample is registered and return a human readable error message"""
        info_strings = []
        for sample in solution.samples:
            if sample.sample_type == sample_type and sample.status != LhCfPoseSampleStatus.OK:
                info_strings.append(f'{sample.status}')

        if len(info_strings) > 0:
            return False, ', '.join(info_strings)
        else:
            return True, ''

    @classmethod
    def _create_solution_stats(cls, matched_samples: list[LhCfPoseSampleWrapper], solution: LighthouseGeometrySolution):
        """Calculate statistics about the solution and store them in the solution object"""

        # Estimated worst error for each sample based on crossing beams
        cf_error: list[float] = []

        for sample in matched_samples:
            bs_ids = list(sample.angles_calibrated.keys())

            bs_angle_list = [(solution.bs_poses[bs_id], sample.angles_calibrated[bs_id]) for bs_id in bs_ids]
            sample_error = LighthouseCrossingBeam.max_distance_all_permutations(bs_angle_list)
            sample.error_distance = sample_error
            cf_error.append(sample_error)

        solution.error_stats = LighthouseGeometrySolution.ErrorStats(
            mean=np.mean(cf_error),
            max=np.max(cf_error),
            std=np.std(cf_error)
        )

    @classmethod
    def _create_verification_stats(cls, solution: LighthouseGeometrySolution):
        """Compute poses and errors for the verification samples in the solution using the crossing beam method."""
        # Estimated worst error for each sample based on crossing beams
        cf_error: list[float] = []

        for sample in solution.samples:
            if sample.sample_type == LhCfPoseSampleType.VERIFICATION:
                bs_ids = list(sample.angles_calibrated.keys())

                # Make sure all base stations in the sample are present in the solution
                is_ok = True
                for bs in bs_ids:
                    if bs not in solution.bs_poses:
                        sample.status = LhCfPoseSampleStatus.BS_UNKNOWN
                        is_ok = False
                        continue

                if is_ok:
                    bs_angle_list = [(solution.bs_poses[bs_id], sample.angles_calibrated[bs_id]) for bs_id in bs_ids]
                    position, error = LighthouseCrossingBeam.position_max_distance_all_permutations(bs_angle_list)

                    sample.pose = Pose.from_rot_vec(t_vec=position)
                    sample.error_distance = error
                    cf_error.append(error)

        if len(cf_error) > 0:
            solution.verification_stats = LighthouseGeometrySolution.ErrorStats(
                mean=np.mean(cf_error),
                max=np.max(cf_error),
                std=np.std(cf_error)
            )

    class SolverThread(threading.Thread):
        """This class runs the geometry solver in a separate thread.
        It is used to provide continuous updates of the solution as well as updating the geometry in the Crazyflie.
        """

        def __init__(self, container: LhGeoInputContainer, is_done_cb, is_starting_estimation_cb=None) -> None:
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
            self.is_starting_estimation_cb = is_starting_estimation_cb

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

                        if self.is_starting_estimation_cb:
                            self.is_starting_estimation_cb()

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
    EMPTY_POSE_SAMPLE = LhCfPoseSample(angles_calibrated={})

    def __init__(self, sensor_positions: ArrayFloat, version: int = 0) -> None:
        self.sensor_positions = sensor_positions

        self.origin: LhCfPoseSample = self.EMPTY_POSE_SAMPLE
        self.x_axis: list[LhCfPoseSample] = []
        self.xy_plane: list[LhCfPoseSample] = []
        self.xyz_space: list[LhCfPoseSample] = []

        # Samples that are used to verify the geometry but are not used for the geometry estimation
        self.verification: list[LhCfPoseSample] = []

        # Used by LhGeoInputContainer to track changes in the data
        self.version = version

    @property
    def origin_index(self) -> int:
        """Get the index of the origin sample in the list of samples"""
        return 0

    @property
    def x_axis_start_index(self) -> int:
        """Get the index of the first x-axis sample in the list of samples"""
        return self.origin_index + 1

    @property
    def x_axis_slice(self) -> slice:
        """Get the slice for the x-axis samples in the list of samples"""
        return slice(self.x_axis_start_index, self.x_axis_start_index + len(self.x_axis))

    @property
    def x_axis_sample_count(self) -> int:
        """Get the count of x-axis samples in the list of samples"""
        return len(self.x_axis)

    @property
    def xy_plane_start_index(self) -> int:
        """Get the index of the first xy-plane sample in the list of samples"""
        return self.x_axis_start_index + len(self.x_axis)

    @property
    def xy_plane_slice(self) -> slice:
        """Get the slice for the xy-plane samples in the list of samples"""
        return slice(self.xy_plane_start_index, self.xy_plane_start_index + len(self.xy_plane))

    @property
    def xy_plane_sample_count(self) -> int:
        """Get the count of xy-plane samples in the list of samples"""
        return len(self.xy_plane)

    @property
    def xyz_space_start_index(self) -> int:
        """Get the index of the first xyz-space sample in the list of samples"""
        return self.xy_plane_start_index + len(self.xy_plane)

    @property
    def xyz_space_sample_count(self) -> int:
        """Get the count of xyz-space samples in the container"""
        return len(self.xyz_space)

    def get_matched_samples(self) -> list[LhCfPoseSampleWrapper]:
        """Get all pose samples collected in a list

        Returns:
            list[LhCfPoseSampleWrapper]: A list of pose samples wrapped in LhCfPoseSampleWrapper
        """
        result = [LhCfPoseSampleWrapper(self.origin, sample_type=LhCfPoseSampleType.ORIGIN)]
        result += [LhCfPoseSampleWrapper(sample, sample_type=LhCfPoseSampleType.X_AXIS) for sample in self.x_axis]
        result += [LhCfPoseSampleWrapper(sample, sample_type=LhCfPoseSampleType.XY_PLANE) for sample in self.xy_plane]
        result += [LhCfPoseSampleWrapper(sample, sample_type=LhCfPoseSampleType.XYZ_SPACE) for sample in self.xyz_space]
        result += [
            LhCfPoseSampleWrapper(sample, sample_type=LhCfPoseSampleType.VERIFICATION) for sample in self.verification]

        return result

    def is_empty(self) -> bool:
        """Check if the container is empty, meaning no samples are set

        Returns:
            bool: True if the container is empty, False otherwise
        """
        return (len(self.x_axis) == 0 and
                len(self.xy_plane) == 0 and
                len(self.xyz_space) == 0 and
                self.origin == self.EMPTY_POSE_SAMPLE)

    @staticmethod
    def yaml_representer(dumper, data: LhGeoInputContainerData):
        return dumper.represent_mapping('!LhGeoInputContainerData', {
            'origin': data.origin,
            'x_axis': data.x_axis,
            'xy_plane': data.xy_plane,
            'xyz_space': data.xyz_space,
            'verification': data.verification,
            'sensor_positions': data.sensor_positions.tolist(),
        })

    @staticmethod
    def yaml_constructor(loader, node):
        values = loader.construct_mapping(node, deep=True)
        sensor_positions = np.array(values['sensor_positions'], dtype=np.float64)
        result = LhGeoInputContainerData(sensor_positions)

        result.origin = values['origin'] if 'origin' in values else LhGeoInputContainerData.EMPTY_POSE_SAMPLE
        result.x_axis = values['x_axis'] if 'x_axis' in values else []
        result.xy_plane = values['xy_plane'] if 'xy_plane' in values else []
        result.xyz_space = values['xyz_space'] if 'xyz_space' in values else []
        result.verification = values['verification'] if 'verification' in values else []

        # Augment the samples with the sensor positions
        result.origin.augment_with_ippe(sensor_positions)

        for sample in result.x_axis:
            sample.augment_with_ippe(sensor_positions)

        for sample in result.xy_plane:
            sample.augment_with_ippe(sensor_positions)

        for sample in result.xyz_space:
            sample.augment_with_ippe(sensor_positions)

        for sample in result.verification:
            sample.augment_with_ippe(sensor_positions)

        return result


yaml.add_representer(LhGeoInputContainerData, LhGeoInputContainerData.yaml_representer)
yaml.add_constructor('!LhGeoInputContainerData', LhGeoInputContainerData.yaml_constructor)


class LhGeoInputContainer():
    """This class holds the input data required by the geometry estimation functionality.
    """
    FILE_TYPE_VERSION = 1

    def __init__(self, sensor_positions: ArrayFloat) -> None:
        self._data = LhGeoInputContainerData(sensor_positions)
        self.is_modified_condition = threading.Condition()

        self._session_name = None
        self._session_path = os.getcwd()
        self._auto_save = False

    def set_origin_sample(self, origin: LhCfPoseSample) -> None:
        """Store/update the sample to be used for the origin

        Args:
            origin (LhCfPoseSample): the new origin
        """
        with self.is_modified_condition:
            self._data.origin = origin
            self._augment_sample(self._data.origin)
            self._handle_data_modification()

    def set_x_axis_sample(self, x_axis: LhCfPoseSample) -> None:
        """Store/update the sample to be used for the x_axis

        Args:
            x_axis (LhCfPoseSample): the new x-axis sample
        """
        with self.is_modified_condition:
            self._data.x_axis = [x_axis]
            self._augment_samples(self._data.x_axis)
            self._handle_data_modification()

    def set_xy_plane_samples(self, xy_plane: list[LhCfPoseSample]) -> None:
        """Store/update the samples to be used for the xy-plane

        Args:
            xy_plane (list[LhCfPoseSample]): the new xy-plane samples
        """
        with self.is_modified_condition:
            self._data.xy_plane = xy_plane
            self._augment_samples(self._data.xy_plane)
            self._handle_data_modification()

    def append_xy_plane_sample(self, xy_plane: LhCfPoseSample) -> None:
        """append to the samples to be used for the xy-plane

        Args:
            xy_plane (LhCfPoseSample): the new xy-plane sample
        """
        with self.is_modified_condition:
            self._augment_sample(xy_plane)
            self._data.xy_plane.append(xy_plane)
            self._handle_data_modification()

    def xy_plane_sample_count(self) -> int:
        """Get the number of samples in the xy-plane

        Returns:
            int: The number of samples in the xy-plane
        """
        with self.is_modified_condition:
            return len(self._data.xy_plane)

    def set_xyz_space_samples(self, samples: list[LhCfPoseSample]) -> None:
        """Store/update the samples for the xyz space

        Args:
            samples (list[LhMeasurement]): the new samples
        """
        new_samples = samples
        self._augment_samples(new_samples)
        with self.is_modified_condition:
            self._data.xyz_space = []
            self.append_xyz_space_samples(new_samples)
            self._handle_data_modification()

    def append_xyz_space_samples(self, samples: list[LhCfPoseSample]) -> None:
        """Append to the samples for the xyz space

        Args:
            samples (list[LhMeasurement]): the new samples
        """
        new_samples = samples
        self._augment_samples(new_samples)
        with self.is_modified_condition:
            self._data.xyz_space += new_samples
            self._handle_data_modification()

    def xyz_space_sample_count(self) -> int:
        """Get the number of samples in the xyz space

        Returns:
            int: The number of samples in the xyz space
        """
        with self.is_modified_condition:
            return len(self._data.xyz_space)

    def append_verification_samples(self, samples: list[LhCfPoseSample]) -> None:
        """Append to the samples for verification

        Args:
            samples (list[LhCfPoseSample]): the new samples
        """
        new_samples = samples
        self._augment_samples(new_samples)
        with self.is_modified_condition:
            self._data.verification += new_samples
            self._handle_data_modification()

    def verification_sample_count(self) -> int:
        """Get the number of samples used for verification

        Returns:
            int: The number of samples used for verification
        """
        with self.is_modified_condition:
            return len(self._data.verification)

    def remove_sample(self, uid: int) -> None:
        """Remove a sample from the container by UID.

        Args:
            uid (int): The UID of the sample to remove
        """
        with self.is_modified_condition:
            sample = self._remove_sample_by_uid(uid)
            if sample is not None:
                self._handle_data_modification()

    def convert_to_verification_sample(self, uid: int) -> None:
        """Convert a sample to a verification sample by UID.
        The sample will be moved to the verification list and removed from the other lists.

        Args:
            uid (int): The UID of the sample to convert
        """
        print(f'Converting sample with UID {uid} to verification sample')
        with self.is_modified_condition:
            sample = self._remove_sample_by_uid(uid)
            if sample is not None:
                self._data.verification.append(sample)
                self._handle_data_modification()

    def convert_to_xyz_space_sample(self, uid: int) -> None:
        """Convert a sample to a xyz-space sample by UID.
        The sample will be moved to the xyz-space list and removed from the other lists.

        Args:
            uid (int): The UID of the sample to convert
        """
        with self.is_modified_condition:
            sample = self._remove_sample_by_uid(uid)
            if sample is not None:
                self._data.xyz_space.append(sample)
                self._handle_data_modification()

    def clear_all_samples(self) -> None:
        """Clear all samples in the container"""
        self._set_new_data_container(LhGeoInputContainerData(self._data.sensor_positions))

    def get_data_version(self) -> int:
        """Get the current data version

        Returns:
            int: The current data version
        """
        with self.is_modified_condition:
            return self._data.version

    def get_data_copy(self) -> LhGeoInputContainerData:
        """Get a copy of the data in the container

        Returns:
            LhGeoInputContainerData: A copy of the data in the container
        """
        with self.is_modified_condition:
            return copy.deepcopy(self._data)

    def is_empty(self) -> bool:
        """Check if the container is empty

        Returns:
            bool: True if the container is empty, False otherwise
        """
        with self.is_modified_condition:
            return self._data.is_empty()

    def save_as_yaml_file(self, text_io: TextIO):
        """Save the data container as a YAML file

        Args:
            text_io (TextIO): The text IO stream to write the YAML data to
        """
        with self.is_modified_condition:
            self.save_data_container_as_yaml(self._data, text_io)

    @classmethod
    def save_data_container_as_yaml(cls, container_data: LhGeoInputContainerData, text_io: TextIO):
        """Save the data container as a YAML string suitable for saving to a file

        Args:
            container_data (LhGeoInputContainerData): The data container to save
            text_io (TextIO): The text IO stream to write the YAML data to
        """
        file_data = {
            'file_type_version': cls.FILE_TYPE_VERSION,
            'data': container_data
        }
        yaml.dump(file_data, text_io, default_flow_style=False)

    def populate_from_file_yaml(self, text_io: TextIO) -> None:
        """Load the data from file

        Args:
            text_io (TextIO): The text IO stream to read the YAML data from
        Raises:
            ValueError: If the file type version is not supported
        """
        file_yaml = yaml.load(text_io, Loader=yaml.FullLoader)
        if file_yaml['file_type_version'] != self.FILE_TYPE_VERSION:
            raise ValueError(f'Unsupported file type version: {file_yaml["file_type_version"]}')
        self._set_new_data_container(file_yaml['data'])

    def enable_auto_save(self, session_path: str = os.getcwd()) -> None:
        """Enable auto-saving of the session data to a file in the specified path.
        Session files will be named with the current date and time.

        Args:
            session_path (str): The path to save the session data to. Defaults to the current working directory.
        """
        self._session_path = session_path
        self._auto_save = True

    def _remove_sample_by_uid(self, uid: int) -> LhCfPoseSample | None:
        removed = None
        if self._data.origin != LhGeoInputContainerData.EMPTY_POSE_SAMPLE:
            if self._data.origin.uid == uid:
                removed = self._data.origin
                self._data.origin = LhGeoInputContainerData.EMPTY_POSE_SAMPLE

        if removed is None:
            for index, sample in enumerate(self._data.x_axis):
                if sample.uid == uid:
                    removed = self._data.x_axis.pop(index)
                    break

        if removed is None:
            for index, sample in enumerate(self._data.xy_plane):
                if sample.uid == uid:
                    removed = self._data.xy_plane.pop(index)
                    break

        if removed is None:
            for index, sample in enumerate(self._data.xyz_space):
                if sample.uid == uid:
                    removed = self._data.xyz_space.pop(index)
                    break

        if removed is None:
            for index, sample in enumerate(self._data.verification):
                if sample.uid == uid:
                    removed = self._data.verification.pop(index)
                    break

        return removed

    def _set_new_data_container(self, new_data: LhGeoInputContainerData) -> None:
        """Set a new data container and update the version"""

        # Maintain version
        with self.is_modified_condition:
            current_version = self._data.version
            self._data = new_data
            self._data.version = current_version

            self._new_session()
            self._handle_data_modification()

    def _augment_sample(self, sample: LhCfPoseSample) -> None:
        sample.augment_with_ippe(self._data.sensor_positions)

    def _augment_samples(self, samples: list[LhCfPoseSample]) -> None:
        for sample in samples:
            self._augment_sample(sample)

    def _handle_data_modification(self) -> None:
        """Update the data version and notify the waiting thread"""
        with self.is_modified_condition:
            self._data.version += 1
            self.is_modified_condition.notify()

        self._save_session()

    def _save_session(self) -> None:
        if self._auto_save and not self.is_empty():
            if self._session_name is None:
                self._session_name = datetime.datetime.now().isoformat(timespec='seconds')

            file_name = os.path.join(self._session_path, f'lh_geo_{self._session_name}.yaml')
            pathlib.Path(self._session_path).mkdir(parents=True, exist_ok=True)
            with open(file_name, 'w', encoding='UTF8') as handle:
                self.save_as_yaml_file(handle)

    def _new_session(self) -> None:
        """Start a new session"""
        self._session_name = None
