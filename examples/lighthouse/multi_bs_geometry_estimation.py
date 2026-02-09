# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2022 Bitcraze AB
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
'''
This functionality is experimental and may not work properly!

Script to run a full base station geometry estimation of a lighthouse
system. The script records data from a Crazyflie that is moved around in
the flight space and creates a solution that minimizes the error
in the measured positions.

The execution of the script takes you through a number of steps, please follow
the instructions.

This script works with 2 or more base stations (if supported by the CF firmware).

This script is a temporary implementation until similar functionality has been
added to the client.

REQUIREMENTS:
- Lighthouse v2 base stations are required for this example. The Lighthouse deck
  will be set to Lighthouse v2 mode automatically.

Prerequisites:
1. The base station calibration data must have been
received by the Crazyflie before this script is executed.

2. 2 or more base stations
'''
from __future__ import annotations

import logging
import time
from threading import Event

import numpy as np

import cflib.crtp  # noqa
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.mem.lighthouse_memory import LighthouseBsGeometry
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.localization.lighthouse_bs_vector import LighthouseBsVectors
from cflib.localization.lighthouse_cf_pose_sample import LhCfPoseSample
from cflib.localization.lighthouse_cf_pose_sample import Pose
from cflib.localization.lighthouse_config_manager import LighthouseConfigWriter
from cflib.localization.lighthouse_geo_estimation_manager import LhGeoEstimationManager
from cflib.localization.lighthouse_geo_estimation_manager import LhGeoInputContainer
from cflib.localization.lighthouse_geo_estimation_manager import LhGeoInputContainerData
from cflib.localization.lighthouse_geometry_solution import LighthouseGeometrySolution
from cflib.localization.lighthouse_sweep_angle_reader import LighthouseMatchedSweepAngleReader
from cflib.localization.lighthouse_sweep_angle_reader import LighthouseSweepAngleAverageReader
from cflib.localization.lighthouse_sweep_angle_reader import LighthouseSweepAngleReader
from cflib.localization.lighthouse_types import LhDeck4SensorPositions
from cflib.localization.lighthouse_types import LhMeasurement
from cflib.localization.user_action_detector import UserActionDetector
from cflib.utils import uri_helper

REFERENCE_DIST = 1.0


def record_angles_average(scf: SyncCrazyflie, timeout: float = 5.0) -> LhCfPoseSample | None:
    """Record angles and average over the samples to reduce noise"""
    recorded_angles: dict[int, tuple[int, LighthouseBsVectors]] | None = None

    is_ready = Event()

    def ready_cb(averages: dict[int, tuple[int, LighthouseBsVectors]]):
        nonlocal recorded_angles
        recorded_angles = averages
        is_ready.set()

    reader = LighthouseSweepAngleAverageReader(scf.cf, ready_cb)
    reader.start_angle_collection()

    if not is_ready.wait(timeout):
        print('Recording timed out.')
        return None

    angles_calibrated: dict[int, LighthouseBsVectors] = {}
    for bs_id, data in recorded_angles.items():
        angles_calibrated[bs_id] = data[1]

    result = LhCfPoseSample(angles_calibrated)

    visible = ', '.join(map(lambda x: str(x + 1), recorded_angles.keys()))
    print(f'  Position recorded, base station ids visible: {visible}')

    if len(recorded_angles.keys()) < 2:
        print('Received too few base stations, we need at least two. Please try again!')
        result = None

    return result


def record_angles_sequence(scf: SyncCrazyflie, recording_time_s: float) -> list[LhMeasurement]:
    """Record angles and return a list of the samples"""
    result: list[LhMeasurement] = []

    bs_seen = set()

    def ready_cb(bs_id: int, angles: LighthouseBsVectors):
        now = time.time()
        measurement = LhMeasurement(timestamp=now, base_station_id=bs_id, angles=angles)
        result.append(measurement)
        bs_seen.add(str(bs_id + 1))

    reader = LighthouseSweepAngleReader(scf.cf, ready_cb)
    reader.start()
    end_time = time.time() + recording_time_s

    while time.time() < end_time:
        time_left = int(end_time - time.time())
        visible = ', '.join(sorted(bs_seen))
        print(f'{time_left}s, bs visible: {visible}')
        bs_seen = set()
        time.sleep(0.5)

    reader.stop()

    return result


def parse_recording_time(recording_time: str, default: int) -> int:
    """Interpret recording time input by user"""
    try:
        return int(recording_time)
    except ValueError:
        return default


def print_base_stations_poses(base_stations: dict[int, Pose], printer=print):
    """Pretty print of base stations pose"""
    for bs_id, pose in sorted(base_stations.items()):
        pos = pose.translation
        printer(f'    {bs_id + 1}: ({pos[0]}, {pos[1]}, {pos[2]})')


def set_axes_equal(ax):
    '''Make axes of 3D plot have equal scale so that spheres appear as spheres,
    cubes as cubes, etc..  This is one possible solution to Matplotlib's
    ax.set_aspect('equal') and ax.axis('equal') not working for 3D.

    Input
    ax: a matplotlib axis, e.g., as output from plt.gca().
    '''

    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_range = abs(x_limits[1] - x_limits[0])
    x_middle = np.mean(x_limits)
    y_range = abs(y_limits[1] - y_limits[0])
    y_middle = np.mean(y_limits)
    z_range = abs(z_limits[1] - z_limits[0])
    z_middle = np.mean(z_limits)

    # The plot bounding box is a sphere in the sense of the infinity
    # norm, hence I call half the max range the plot radius.
    plot_radius = 0.5*max([x_range, y_range, z_range])

    ax.set_xlim3d([x_middle - plot_radius, x_middle + plot_radius])
    ax.set_ylim3d([y_middle - plot_radius, y_middle + plot_radius])
    ax.set_zlim3d([z_middle - plot_radius, z_middle + plot_radius])


def load_from_file(name: str) -> LhGeoInputContainerData:
    container = LhGeoInputContainer(LhDeck4SensorPositions.positions)
    with open(name, 'r', encoding='UTF8') as handle:
        container.populate_from_file_yaml(handle)
        return container.get_data_copy()


def print_solution(solution: LighthouseGeometrySolution):
    def _print(msg: str):
        print(f'      * {msg}')
    _print('Solution ready --------------------------------------')
    _print('  Base stations at:')
    bs_poses = solution.bs_poses
    print_base_stations_poses(bs_poses, printer=_print)

    _print(f'Converged: {solution.has_converged}')
    _print(f'Progress info: {solution.progress_info}')
    _print(f'Progress is ok: {solution.progress_is_ok}')
    _print(f'Origin: {solution.is_origin_sample_valid}, {solution.origin_sample_info}')
    _print(f'X-axis: {solution.is_x_axis_samples_valid}, {solution.x_axis_samples_info}')
    _print(f'XY-plane: {solution.is_xy_plane_samples_valid}, {solution.xy_plane_samples_info}')
    _print(f'XYZ space: {solution.xyz_space_samples_info}')
    _print(f'General info: {solution.general_failure_info}')
    _print(f'Error info: {solution.error_stats}')
    if solution.verification_stats:
        _print(f'Verification info: {solution.verification_stats}')


def upload_geometry(scf: SyncCrazyflie, bs_poses: dict[int, Pose]):
    """Upload the geometry to the Crazyflie"""
    geo_dict = {}
    for bs_id, pose in bs_poses.items():
        geo = LighthouseBsGeometry()
        geo.origin = pose.translation.tolist()
        geo.rotation_matrix = pose.rot_matrix.tolist()
        geo.valid = True
        geo_dict[bs_id] = geo

    event = Event()

    def data_written(_):
        event.set()

    helper = LighthouseConfigWriter(scf.cf)
    helper.write_and_store_config(data_written, geos=geo_dict)
    event.wait()


def estimate_from_file(file_name: str):
    container_data = load_from_file(file_name)
    solution = LhGeoEstimationManager.estimate_geometry(container_data)
    print_solution(solution)


def get_recording(scf: SyncCrazyflie) -> LhCfPoseSample:
    data = None
    while True:  # Infinite loop, will break on valid measurement
        input('Press return when ready. ')
        print('  Recording...')
        measurement = record_angles_average(scf)
        if measurement is not None:
            data = measurement
            scf.cf.platform.send_user_notification(True)
            break  # Exit the loop if a valid measurement is obtained
        else:
            scf.cf.platform.send_user_notification(False)
            time.sleep(1)
            print('Invalid measurement, please try again.')
    return data


def get_multiple_recordings(scf: SyncCrazyflie) -> list[LhCfPoseSample]:
    data: list[LhCfPoseSample] = []
    first_attempt = True

    while True:
        if first_attempt:
            user_input = input('Press return to record a measurement: ').lower()
            first_attempt = False
        else:
            user_input = input('Press return to record another measurement, or "q" to continue: ').lower()

        if user_input == 'q' and data:
            break
        elif user_input == 'q' and not data:
            print('You must record at least one measurement.')
            continue

        print('  Recording...')
        measurement = record_angles_average(scf)
        if measurement is not None:
            scf.cf.platform.send_user_notification(True)
            data.append(measurement)
        else:
            scf.cf.platform.send_user_notification(False)
            time.sleep(1)
            print('Invalid measurement, please try again.')

    return data


def connect_and_estimate(uri: str, file_name: str | None = None):
    """Connect to a Crazyflie, collect data and estimate the geometry of the system"""
    print(f'Step 1. Connecting to the Crazyflie on uri {uri}...')
    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        container = LhGeoInputContainer(LhDeck4SensorPositions.positions)
        container.enable_auto_save('lh_geo_sessions')
        print('Starting geometry estimation thread...')

        def _local_solution_handler(solution: LighthouseGeometrySolution):
            print_solution(solution)
            if solution.progress_is_ok:
                upload_geometry(scf, solution.poses.bs_poses)
                print('Geometry uploaded to Crazyflie.')

        thread = LhGeoEstimationManager.SolverThread(container, is_done_cb=_local_solution_handler)
        thread.start()

        print('  Connected')

        print('  Setting lighthouse deck to v2 mode...')
        scf.cf.param.set_value('lighthouse.systemType', 2)
        print('  Lighthouse deck set to v2 mode')
        print('')
        print('In the 3 following steps we will define the coordinate system.')

        print('Step 2. Put the Crazyflie where you want the origin of your coordinate system.')

        container.set_origin_sample(get_recording(scf))

        print(f'Step 3. Put the Crazyflie on the positive X-axis, exactly {REFERENCE_DIST} meters from the origin. ' +
              'This position defines the direction of the X-axis, but it is also used for scaling the system.')
        container.set_x_axis_sample(get_recording(scf))

        print('Step 4. Put the Crazyflie somewhere in the XY-plane, but not on the X-axis.')
        print('Multiple samples can be recorded if you want to.')
        container.set_xy_plane_samples(get_multiple_recordings(scf))

        print()
        print('Step 5. We will now record data from the space you plan to fly in and optimize the base station ' +
              'geometry based on this data. Sample a position by quickly rotating the Crazyflie ' +
              'around the Z-axis. This will trigger a measurement of the base station angles. ')

        def matched_angles_cb(sample: LhCfPoseSample):
            print('Position stored')
            scf.cf.platform.send_user_notification(True)
            container.append_xyz_space_samples([sample])
            scf.cf.platform.send_user_notification()

        def timeout_cb():
            print('Timeout, no angles received. Please try again.')
            scf.cf.platform.send_user_notification(False)
        angle_reader = LighthouseMatchedSweepAngleReader(scf.cf, matched_angles_cb, timeout_cb=timeout_cb)

        def user_action_cb():
            print('Sampling...')
            angle_reader.start(timeout=1.0)
        detector = UserActionDetector(scf.cf, cb=user_action_cb)

        detector.start()
        input('Press return to terminate the script when all required positions have been sampled.')

        detector.stop()
        thread.stop()


# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

    # Set a file name to write the measurement data to file. Useful for debugging
    file_name = None
    file_name = 'lh_geo_estimate_data.yaml'

    connect_and_estimate(uri, file_name=file_name)

    # Run the estimation on data from file instead of live measurements
    # estimate_from_file(file_name)
