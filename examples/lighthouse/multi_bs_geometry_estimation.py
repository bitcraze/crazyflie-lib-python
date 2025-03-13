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
from cflib.localization import LighthouseBsVector
from cflib.localization.lighthouse_config_manager import LighthouseConfigWriter
from cflib.localization.lighthouse_config_manager import LighthouseConfigFileManager
from cflib.localization.lighthouse_geometry_solver import LighthouseGeometrySolver
from cflib.localization.lighthouse_initial_estimator import LighthouseInitialEstimator
from cflib.localization.lighthouse_sample_matcher import LighthouseSampleMatcher
from cflib.localization.lighthouse_sweep_angle_reader import LighthouseSweepAngleAverageReader
from cflib.localization.lighthouse_sweep_angle_reader import LighthouseSweepAngleReader
from cflib.localization.lighthouse_system_aligner import LighthouseSystemAligner
# from cflib.localization.lighthouse_system_aligner2 import LighthouseSystemAligner2
from cflib.localization.lighthouse_system_scaler import LighthouseSystemScaler
from cflib.localization.lighthouse_types import LhCfPoseSample
from cflib.localization.lighthouse_types import LhDeck4SensorPositions
from cflib.localization.lighthouse_types import LhMeasurement
from cflib.localization.lighthouse_types import Pose
from cflib.utils import uri_helper


REFERENCE_DIST = 1.0


def clip1(v: float) -> float:
    if v > 1.0:
        return 1.0
    if v < -1.0:
        return -1.0
    return v


def lighthouseCalibrationMeasurementModelLh2(x: float, y: float, z: float, t: float, calib) -> float:
    ax = np.arctan2(y, x)
    r = np.sqrt(x * x + y * y)

    base = ax + np.arcsin(clip1(z * np.tan(t - calib.tilt) / r))
    compGib = -calib.gibmag * np.cos(ax + calib.gibphase)

    return base - (calib.phase + compGib)


def idealToDistortedV2(calib, ideal: list[float]) -> list[float]:
    t30 = np.pi / 6.0
    tan30 = np.tan(t30)

    a1 = ideal[0]
    a2 = ideal[1]

    x = 1.0
    y = np.tan((a2 + a1) / 2.0)
    z = np.sin(a2 - a1) / (tan30 * (np.cos(a2) + np.cos(a1)))

    distorted = [
        lighthouseCalibrationMeasurementModelLh2(x, y, z, -t30, calib.sweeps[0]),
        lighthouseCalibrationMeasurementModelLh2(x, y, z, t30, calib.sweeps[1])]

    return distorted


def lighthouseCalibrationApply(calib, rawAngles: list[float]) -> list[float]:
    max_delta = 0.0005

    # Use distorted angle as a starting point
    estimatedAngles = rawAngles.copy()

    for i in range(5):
        currentDistortedAngles = idealToDistortedV2(calib, estimatedAngles)

        delta0 = rawAngles[0] - currentDistortedAngles[0]
        delta1 = rawAngles[1] - currentDistortedAngles[1]

        estimatedAngles[0] = estimatedAngles[0] + delta0
        estimatedAngles[1] = estimatedAngles[1] + delta1

        if (abs(delta0) < max_delta and abs(delta1) < max_delta):
            break

    return estimatedAngles


def vector_with_compensation(a1: float, a2: float, calibs, bs: int) -> LighthouseBsVector:
    if bs in calibs:
        angles = lighthouseCalibrationApply(calibs[bs], [a1, a2])
    else:
        print(f"Base station {bs} not in calib data")
        angles = [a1, a2]

    return LighthouseBsVector.from_lh2(angles[0], angles[1])


def read_angles_average_from_lh2_file(file_name: str, calibs) -> LhCfPoseSample:
    with open(file_name, 'r', encoding='utf8') as contents:
        bs_angles = {}
        for line in contents.readlines():
            if line.startswith('full-rotation'):
                parts = line.split(',')
                bs = int(parts[1])
                if bs not in bs_angles:
                    bs_angles[bs] = [[], [], [], [], [], [], [], []]
                for i in range(8):
                    bs_angles[bs][i].append(float(parts[2 + i]))

    angles_calibrated = {}
    for bs, angles in bs_angles.items():
        vectors = []
        for i in range(4):
            vector = vector_with_compensation(np.average(angles[i]), np.average(angles[i + 4]), calibs, bs)
            vectors.append(vector)
        angles_calibrated[bs] = LighthouseBsVectors(vectors)

    return LhCfPoseSample(angles_calibrated=angles_calibrated)


def read_angles_sequence_from_lh2_file(file_name: str, calibs) -> list[LhMeasurement]:
    result: list[LhMeasurement] = []

    print(file_name)

    with open(file_name, 'r', encoding='utf8') as contents:
        for line in contents.readlines():
            if line.startswith('full-rotation'):
                parts = line.split(',')
                bs = int(parts[1])
                now = float(parts[10])

                angles: LighthouseBsVectors = LighthouseBsVectors([
                    vector_with_compensation(float(parts[2]), float(parts[6]), calibs, bs),
                    vector_with_compensation(float(parts[3]), float(parts[7]), calibs, bs),
                    vector_with_compensation(float(parts[4]), float(parts[8]), calibs, bs),
                    vector_with_compensation(float(parts[5]), float(parts[9]), calibs, bs)])

                measurement = LhMeasurement(timestamp=now, base_station_id=bs, angles=angles)
                result.append(measurement)

    return result


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


def print_base_stations_poses(base_stations: dict[int, Pose]):
    """Pretty print of base stations pose"""
    for bs_id, pose in sorted(base_stations.items()):
        pos = pose.translation
        print(f'    {bs_id + 1}: ({pos[0]}, {pos[1]}, {pos[2]})')


def visualize(cf_poses: list[Pose], bs_poses: list[Pose]):
    """Visualize positions of base stations and Crazyflie positions"""
    # Set to True to visualize positions
    # Requires PyPlot
    visualize_positions = True
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

        ax.set_aspect('equal')
        print('Close graph window to continue')
        plt.show()
        print('Continuing...')


def write_to_file(name: str,
                  origin: LhCfPoseSample,
                  x_axis: list[LhCfPoseSample],
                  xy_plane: list[LhCfPoseSample],
                  samples: list[LhMeasurement]):
    with open(name, 'wb') as handle:
        data = (origin, x_axis, xy_plane, samples)
        pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)


def load_from_file(name: str):
    with open(name, 'rb') as handle:
        return pickle.load(handle)


def estimate_geometry(origin: LhCfPoseSample,
                      x_axis: list[LhCfPoseSample],
                      xy_plane: list[LhCfPoseSample],
                      samples: list[LhMeasurement]) -> dict[int, Pose]:
    """Estimate the geometry of the system based on samples recorded by a Crazyflie"""
    matched_samples = [origin] + x_axis + xy_plane + LighthouseSampleMatcher.match(samples, min_nr_of_bs_in_match=2)
    initial_guess, cleaned_matched_samples = LighthouseInitialEstimator.estimate(
        matched_samples, LhDeck4SensorPositions.positions)

    start_time = time.time()

    print('Initial guess base stations at:')
    print_base_stations_poses(initial_guess.bs_poses)
    print('Initial guess origin: {}', initial_guess.cf_poses[0].translation)
    print('Initial guess x-axis points at:')
    for point in initial_guess.cf_poses[1:1 + len(x_axis)]:
        print(point.translation)
    print('Initial guess xy-plane points at:')
    for point in initial_guess.cf_poses[1 + len(x_axis):1 + len(x_axis) + len(xy_plane)]:
        print(point.translation)

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

    if True:
        # Align the solution
        bs_aligned_poses, transformation = LighthouseSystemAligner.align(
            origin_pos, x_axis_pos, xy_plane_pos, solution.bs_poses)

        cf_aligned_poses = list(map(transformation.rotate_translate_pose, solution.cf_poses))

        # Scale the solution
        bs_scaled_poses, cf_scaled_poses, scale = LighthouseSystemScaler.scale_fixed_point(bs_aligned_poses,
                                                                                        cf_aligned_poses,
                                                                                        [REFERENCE_DIST, 0, 0],
                                                                                        cf_aligned_poses[1])
    else:
        # Scale and align to known bs positions
        bs_0_actual = np.array((-3.92, 0.32, 3.10))
        bs_2_actual = np.array((3.01, 0.17, 3.10))
        bs_11_actual = np.array((-4.95, 11.24, 2.99))
        bs_15_actual = np.array((3.45, 14.83, 3.14))

        bs_scaled_poses, cf_scaled_poses = LighthouseSystemAligner2.align(
            [bs_0_actual, bs_2_actual, bs_11_actual, bs_15_actual],
            [solution.bs_poses[0].translation, solution.bs_poses[2].translation, solution.bs_poses[11].translation, solution.bs_poses[15].translation],
            solution.bs_poses, solution.cf_poses)

    print()
    print('Final solution:')
    print('  Base stations at:')
    print_base_stations_poses(bs_scaled_poses)
    print('Final origin: {}', cf_scaled_poses[0].translation)
    print('Final x-axis points at:')
    for point in cf_scaled_poses[1:1 + len(x_axis)]:
        print(point.translation)
    print('Final xy-plane points at:')
    for point in cf_scaled_poses[1 + len(x_axis):1 + len(x_axis) + len(xy_plane)]:
        print(point.translation)

    print(f"Total time: {time.time() - start_time}")

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


def estimate_from_lhv2_files(origin_file: str, x_axis_files: list[str], xy_plane_files: list[str], samples_files: list[str], calibs_file: str, result_file: str):
    geos_ignore, calibs, system_type = LighthouseConfigFileManager.read(calibs_file)
    origin = read_angles_average_from_lh2_file(origin_file, calibs)
    x_axis = []
    for file_name in x_axis_files:
        x_axis.append(read_angles_average_from_lh2_file(file_name, calibs))

    xy_plane = []
    for file_name in xy_plane_files:
        xy_plane.append(read_angles_average_from_lh2_file(file_name, calibs))

    samples = []
    for samples_file in samples_files:
        print(samples_file)
        samples += read_angles_sequence_from_lh2_file(samples_file, calibs)

    bs_est = estimate_geometry(origin, x_axis, xy_plane, samples)

    if result_file is not None:
        geos = {}
        for id, pose in bs_est.items():
            geos[id] = LighthouseBsGeometry()
            geos[id].origin = pose.translation.tolist()
            geos[id].rotation_matrix = pose.rot_matrix.tolist()
            geos[id].valid = True
        LighthouseConfigFileManager.write(result_file, geos=geos, calibs=calibs)


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

    # uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')
    uri = 'radio://0/100/2M/E7E7E7E706'

    # Set a file name to write the measurement data to file. Useful for debugging
    file_name = None
    # file_name = 'lh_geo_estimate_data.pickle'

    # root_dir = '/home/kristoffer/code/bitcraze/lighthouse16-firmware/algos/examples/the-full-shebang-v2/'
    # estimate_from_lhv2_files(
    #     root_dir + 'origo-rots.txt',
    #     [root_dir + 'new_1m-rots.txt'],
    #     [root_dir + 'floor1-rots.txt'],
    #     [root_dir + 'move-rots.txt'],
    #     '/home/kristoffer/Documents/lighthouse/arena_all.yaml', None)


    # root_dir = '/home/kristoffer/code/bitcraze/lighthouse16-firmware/algos/examples/recodings-with-bs-1-4/'
    # estimate_from_lhv2_files(
    #     root_dir + 'LH_RAW-20231130-095339-origo-rots.txt',
    #     [root_dir + 'LH_RAW-20231130-095359-1m-from-origo-rots.txt'],
    #     [root_dir + 'LH_RAW-20231130-095514-random-on-floor-rots.txt'],
    #     [root_dir + 'LH_RAW-20231130-095540-moving-around-rots.txt'],
    #     '/home/kristoffer/Documents/lighthouse/arena_all.yaml', None)

    # root_dir = '/home/knmcguire/development/bitcraze/lighthouse16/lighthouse16-firmware/algos/examples/large_arena_lighthouse_system/'
    # estimate_from_lhv2_files(
    #     root_dir + 'LH_RAW-20231130-095339-origo-rots.txt',
    #     [root_dir + 'LH_RAW-20231130-095359-1m-from-origo-rots.txt'],
    #     [root_dir + 'LH_RAW-20231130-095514-random-on-floor-rots.txt', '/home/kristoffer/code/bitcraze/lighthouse16-firmware/algos/examples/the-full-shebang-v2/floor5-rots.txt', '/home/kristoffer/code/bitcraze/lighthouse16-firmware/algos/examples/the-full-shebang-v2/floor4-rots.txt'],
    #     '/home/kristoffer/code/bitcraze/lighthouse16-firmware/algos/examples/the-full-shebang-v2/move-rots.txt',
    #     '/home/kristoffer/Documents/lighthouse/arena_all.yaml', '/home/kristoffer/Documents/lighthouse/arena_16.yaml')

    # root_dir = '/home/knmcguire/development/bitcraze/lighthouse16/lighthouse16-firmware/algos/examples/large_arena_lighthouse_system/'
    # estimate_from_lhv2_files(
    #     root_dir + 'A-rots.txt',
    #     [root_dir + 'B-rots.txt'],
    #     [root_dir + 'F-rots.txt'],
    #     [root_dir + 'K-1m-rots.txt'],
    #     root_dir + 'arena_all.yaml', root_dir + 'arena_16.yaml')

    # root_dir = '/home/knmcguire/development/bitcraze/lighthouse16/lighthouse16-firmware/algos/examples/large_arena_LH_20240222/'
    # estimate_from_lhv2_files(
    #    root_dir + 'A-240222-rots.txt',
    #    [root_dir + 'B-240222-rots.txt'],
    #    [root_dir + 'F-240222-rots.txt',root_dir + 'E-240222-rots.txt',root_dir + 'G-240222-rots.txt'],
    #    [root_dir + 'figure-eight-240222-rots.txt'],
    #    root_dir + 'arena_all.yaml', root_dir + 'arena_16.yaml')

    root_dir = '/home/aris/Morgens/Code/Library.venv/crazyflie-lib-python-lighthouse16branch/Geo_Estimation_Files/'
    estimate_from_lhv2_files(
        root_dir + '1_Origin_2025-03-12-rots.txt',  # origin_file: str
        [root_dir + '2_X-axis_2025-03-12-rots.txt'],  # x_axis_files: list[str]
        [root_dir + '3_XY-plane_pointA_2025-03-12-rots.txt',root_dir + '4_XY-plane_pointB_2025-03-12-rots.txt', root_dir + '5_XY-plane_pointC_2025-03-12-rots.txt', root_dir + '6_XY-plane_pointD_2025-03-12-rots.txt'],  # xy_plane_files: list[str]
        [root_dir + '7_Samples_2025-03-12-rots.txt'],  # samples_files: list[str]
        root_dir + '8_Calibs_2025-03-12.yaml', root_dir + 'Lighthouse_x16.yaml')  # calibs_file: str, result_file: str
    # connect_and_estimate(uri, file_name=file_name)

    # Run the estimation on data from file instead of live measurements
    # estimate_from_file(file_name)
