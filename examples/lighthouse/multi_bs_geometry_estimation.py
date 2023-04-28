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

Prerequisites:
1. The base station calibration data must have been
received by the Crazyflie before this script is executed.

2. 2 or more base stations
'''
from __future__ import annotations

import logging
import pickle
import time
from threading import Event

import numpy as np

import cflib.crtp  # noqa
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.mem.lighthouse_memory import LighthouseBsGeometry
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.localization.lighthouse_bs_vector import LighthouseBsVectors
from cflib.localization.lighthouse_config_manager import LighthouseConfigWriter
from cflib.localization.lighthouse_geometry_solver import LighthouseGeometrySolver
from cflib.localization.lighthouse_initial_estimator import LighthouseInitialEstimator
from cflib.localization.lighthouse_sample_matcher import LighthouseSampleMatcher
from cflib.localization.lighthouse_sweep_angle_reader import LighthouseSweepAngleAverageReader
from cflib.localization.lighthouse_sweep_angle_reader import LighthouseSweepAngleReader
from cflib.localization.lighthouse_system_aligner import LighthouseSystemAligner
from cflib.localization.lighthouse_system_scaler import LighthouseSystemScaler
from cflib.localization.lighthouse_types import LhCfPoseSample
from cflib.localization.lighthouse_types import LhDeck4SensorPositions
from cflib.localization.lighthouse_types import LhMeasurement
from cflib.localization.lighthouse_types import Pose
from cflib.utils import uri_helper

REFERENCE_DIST = 1.0


def record_angles_average(scf: SyncCrazyflie) -> LhCfPoseSample:
    """Record angles and average over the samples to reduce noise"""
    recorded_angles = None

    is_ready = Event()

    def ready_cb(averages):
        nonlocal recorded_angles
        recorded_angles = averages
        is_ready.set()

    reader = LighthouseSweepAngleAverageReader(scf.cf, ready_cb)
    reader.start_angle_collection()
    is_ready.wait()

    angles_calibrated = {}
    for bs_id, data in recorded_angles.items():
        angles_calibrated[bs_id] = data[1]

    result = LhCfPoseSample(angles_calibrated=angles_calibrated)

    visible = ', '.join(map(lambda x: str(x + 1), recorded_angles.keys()))
    print(f'  Position recorded, base station ids visible: {visible}')

    if len(recorded_angles.keys()) < 2:
        print('Received too few base stations, we need at least two. Please try again!')
        result = None

    return result


def record_angles_sequence(scf: SyncCrazyflie, recording_time_s: float) -> list[LhCfPoseSample]:
    """Record angles and return a list of the samples"""
    result: list[LhCfPoseSample] = []

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


def print_base_stations_poses(base_stations: dict[int, Pose]):
    """Pretty print of base stations pose"""
    for bs_id, pose in sorted(base_stations.items()):
        pos = pose.translation
        print(f'    {bs_id + 1}: ({pos[0]}, {pos[1]}, {pos[2]})')


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


def visualize(cf_poses: list[Pose], bs_poses: list[Pose]):
    """Visualize positions of base stations and Crazyflie positions"""
    # Set to True to visualize positions
    # Requires PyPlot
    visualize_positions = False
    if visualize_positions:
        import matplotlib.pyplot as plt

        positions = np.array(list(map(lambda x: x.translation, cf_poses)))

        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')

        x_cf = positions[:, 0]
        y_cf = positions[:, 1]
        z_cf = positions[:, 2]

        ax.scatter(x_cf, y_cf, z_cf)

        positions = np.array(list(map(lambda x: x.translation, bs_poses)))

        x_bs = positions[:, 0]
        y_bs = positions[:, 1]
        z_bs = positions[:, 2]

        ax.scatter(x_bs, y_bs, z_bs, c='red')

        set_axes_equal(ax)
        print('Close graph window to continue')
        plt.show()


def write_to_file(name: str,
                  origin: LhCfPoseSample,
                  x_axis: list[LhCfPoseSample],
                  xy_plane: list[LhCfPoseSample],
                  samples: list[LhCfPoseSample]):
    with open(name, 'wb') as handle:
        data = (origin, x_axis, xy_plane, samples)
        pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)


def load_from_file(name: str):
    with open(name, 'rb') as handle:
        return pickle.load(handle)


def estimate_geometry(origin: LhCfPoseSample,
                      x_axis: list[LhCfPoseSample],
                      xy_plane: list[LhCfPoseSample],
                      samples: list[LhCfPoseSample]) -> dict[int, Pose]:
    """Estimate the geometry of the system based on samples recorded by a Crazyflie"""
    matched_samples = [origin] + x_axis + xy_plane + LighthouseSampleMatcher.match(samples, min_nr_of_bs_in_match=2)
    initial_guess, cleaned_matched_samples = LighthouseInitialEstimator.estimate(
        matched_samples, LhDeck4SensorPositions.positions)

    print('Initial guess base stations at:')
    print_base_stations_poses(initial_guess.bs_poses)

    print(f'{len(cleaned_matched_samples)} samples will be used')
    visualize(initial_guess.cf_poses, initial_guess.bs_poses.values())

    solution = LighthouseGeometrySolver.solve(initial_guess, cleaned_matched_samples, LhDeck4SensorPositions.positions)
    if not solution.success:
        print('Solution did not converge, it might not be good!')

    start_x_axis = 1
    start_xy_plane = 1 + len(x_axis)
    origin_pos = solution.cf_poses[0].translation
    x_axis_poses = solution.cf_poses[start_x_axis:start_x_axis + len(x_axis)]
    x_axis_pos = list(map(lambda x: x.translation, x_axis_poses))
    xy_plane_poses = solution.cf_poses[start_xy_plane:start_xy_plane + len(xy_plane)]
    xy_plane_pos = list(map(lambda x: x.translation, xy_plane_poses))

    print('Raw solution:')
    print('  Base stations at:')
    print_base_stations_poses(solution.bs_poses)
    print('  Solution match per base station:')
    for bs_id, value in solution.error_info['bs'].items():
        print(f'    {bs_id + 1}: {value}')

    # Align the solution
    bs_aligned_poses, transformation = LighthouseSystemAligner.align(
        origin_pos, x_axis_pos, xy_plane_pos, solution.bs_poses)

    cf_aligned_poses = list(map(transformation.rotate_translate_pose, solution.cf_poses))

    # Scale the solution
    bs_scaled_poses, cf_scaled_poses, scale = LighthouseSystemScaler.scale_fixed_point(bs_aligned_poses,
                                                                                       cf_aligned_poses,
                                                                                       [REFERENCE_DIST, 0, 0],
                                                                                       cf_aligned_poses[1])

    print()
    print('Final solution:')
    print('  Base stations at:')
    print_base_stations_poses(bs_scaled_poses)

    visualize(cf_scaled_poses, bs_scaled_poses.values())

    return bs_scaled_poses


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
    origin, x_axis, xy_plane, samples = load_from_file(file_name)
    estimate_geometry(origin, x_axis, xy_plane, samples)


def connect_and_estimate(uri: str, file_name: str | None = None):
    """Connect to a Crazyflie, collect data and estimate the geometry of the system"""
    print(f'Step 1. Connecting to the Crazyflie on uri {uri}...')
    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        print('  Connected')
        print('')
        print('In the 3 following steps we will define the coordinate system.')

        print('Step 2. Put the Crazyflie where you want the origin of your coordinate system.')

        origin = None
        do_repeat = True
        while do_repeat:
            input('Press return when ready. ')
            print('  Recording...')
            measurement = record_angles_average(scf)
            do_repeat = False
            if measurement is not None:
                origin = measurement
            else:
                do_repeat = True

        print(f'Step 3. Put the Crazyflie on the positive X-axis, exactly {REFERENCE_DIST} meters from the origin. ' +
              'This position defines the direction of the X-axis, but it is also used for scaling of the system.')
        x_axis = []
        do_repeat = True
        while do_repeat:
            input('Press return when ready. ')
            print('  Recording...')
            measurement = record_angles_average(scf)
            do_repeat = False
            if measurement is not None:
                x_axis = [measurement]
            else:
                do_repeat = True

        print('Step 4. Put the Crazyflie somehere in the XY-plane, but not on the X-axis.')
        print('Multiple samples can be recorded if you want to, type "r" before you hit enter to repeat the step.')
        xy_plane = []
        do_repeat = True
        while do_repeat:
            do_repeat = 'r' == input('Press return when ready. ').lower()
            print('  Recording...')
            measurement = record_angles_average(scf)
            if measurement is not None:
                xy_plane.append(measurement)
            else:
                do_repeat = True

        print()
        print('Step 5. We will now record data from the space you plan to fly in and optimize the base station ' +
              'geometry based on this data. Move the Crazyflie around, try to cover all of the space, make sure ' +
              'all the base stations are received and do not move too fast.')
        default_time = 20
        recording_time = input(f'Enter the number of seconds you want to record ({default_time} by default), ' +
                               'recording starts when you hit enter. ')
        recording_time_s = parse_recording_time(recording_time, default_time)
        print('  Recording started...')
        samples = record_angles_sequence(scf, recording_time_s)
        print('  Recording ended')

        if file_name:
            write_to_file(file_name, origin, x_axis, xy_plane, samples)
            print(f'Wrote data to file {file_name}')

        print('Step 6. Estimating geometry...')
        bs_poses = estimate_geometry(origin, x_axis, xy_plane, samples)
        print('  Geometry estimated')

        print('Step 7. Upload geometry to the Crazyflie')
        input('Press enter to upload geometry. ')
        upload_geometry(scf, bs_poses)
        print('Geometry uploaded')


# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

    # Set a file name to write the measurement data to file. Useful for debugging
    file_name = None
    # file_name = 'lh_geo_estimate_data.pickle'

    connect_and_estimate(uri, file_name=file_name)

    # Run the estimation on data from file instead of live measurements
    # estimate_from_file(file_name)
