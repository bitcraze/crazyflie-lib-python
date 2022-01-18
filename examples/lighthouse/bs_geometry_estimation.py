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

This script supports large systems with more than 2 base stations (if
supported by the CF firmware).

This script is a temporary implementation until similar functionality has been
added to the client.

Prerequisite:
1. The base station calibration data must have been
received by the Crazyflie before this script is executed.
2. Base stations must point downwards, towards the floor.
'''
import logging
import time
from threading import Event

import cflib.crtp  # noqa
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.mem.lighthouse_memory import LighthouseBsGeometry
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.localization.lighthouse_config_manager import LighthouseConfigWriter
from cflib.localization.lighthouse_geometry_solver import LighthouseGeometrySolver
from cflib.localization.lighthouse_initial_estimator import LighthouseInitialEstimator
from cflib.localization.lighthouse_sample_matcher import LighthouseSampleMatcher
from cflib.localization.lighthouse_sweep_angle_reader import LighthouseSweepAngleAverageReader
from cflib.localization.lighthouse_sweep_angle_reader import LighthouseSweepAngleReader
from cflib.localization.lighthouse_system_aligner import LighthouseSystemAligner
from cflib.localization.lighthouse_types import LhCfPoseSample
from cflib.localization.lighthouse_types import LhDeck4SensorPositions
from cflib.localization.lighthouse_types import LhMeasurement
from cflib.utils import uri_helper


def record_angles_average(scf):
    recorded_angles = None

    isReady = Event()

    def ready_cb(averages):
        nonlocal recorded_angles
        recorded_angles = averages
        isReady.set()

    reader = LighthouseSweepAngleAverageReader(scf.cf, ready_cb)
    reader.start_angle_collection()
    isReady.wait()

    angles_calibrated = {}
    for bs_id, data in recorded_angles.items():
        angles_calibrated[bs_id] = data[1]

    visible = ', '.join(map(lambda x: str(x + 1), recorded_angles.keys()))
    print(f'  Position recorded, bs visible: {visible}')

    return LhCfPoseSample(angles_calibrated=angles_calibrated)


def record_angles_sequence(scf, recording_time_s):
    result = []

    bs_seen = set()

    def ready_cb(bs_id, angles):
        now = time.time()
        measurement = LhMeasurement(timestamp=now, base_station_id=bs_id, angles=angles)
        result.append(measurement)
        bs_seen.add(str(bs_id + 1))

    reader = LighthouseSweepAngleReader(scf.cf, ready_cb)
    reader.start()
    end_time = time.time() + recording_time_s

    while time.time() < end_time:
        time_left = end_time - time.time()
        visible = ', '.join(sorted(bs_seen))
        print(f'{time_left}s, bs visible: {visible}')
        bs_seen = set()
        time.sleep(0.5)

    reader.stop()

    return result


def parse(recording_time, default):
    try:
        return int(recording_time)
    except ValueError:
        return default


def estimate_geometry(origin, x_axis, xy_plane, samples):
    matched_samples = [origin] + x_axis + xy_plane + LighthouseSampleMatcher.match(samples, min_nr_of_bs_in_match=2)
    initial_guess = LighthouseInitialEstimator.estimate(matched_samples, LhDeck4SensorPositions.positions)
    solution = LighthouseGeometrySolver.solve(initial_guess, matched_samples, LhDeck4SensorPositions.positions)
    if not solution.success:
        print('Solution did not converge, it might not be good!')

    start_x_axis = 1
    start_xy_plane = 1 + len(x_axis)
    origin_pos = solution.cf_poses[0].translation
    x_axis_poses = solution.cf_poses[start_x_axis:start_x_axis + len(x_axis)]
    x_axis_pos = list(map(lambda x: x.translation, x_axis_poses))
    xy_plane_poses = solution.cf_poses[start_xy_plane:start_xy_plane + len(xy_plane)]
    xy_plane_pos = list(map(lambda x: x.translation, xy_plane_poses))
    bs_aligned_poses = LighthouseSystemAligner.align(origin_pos, x_axis_pos, xy_plane_pos, solution.bs_poses)

    print('  Base stations at:')
    for bs_id, pose in sorted(bs_aligned_poses.items()):
        pos = pose.translation
        print(f'    {bs_id + 1}: ({pos[0]}, {pos[1]}, {pos[2]})')
    print('  Solution match per base station:')
    for bs_id, value in solution.error_info['bs'].items():
        print(f'    {bs_id + 1}: {value}')

    return bs_aligned_poses


def upload_geometry(scf, bs_poses):
    geo_dict = {}
    for bs_id, pose in bs_poses.items():
        geo = LighthouseBsGeometry()
        geo.origin = pose.translation.tolist()
        geo.rotation_matrix = pose.rot_matrix.tolist()
        geo.valid = True
        geo_dict[bs_id] = geo

    event = Event()

    def data_written(success):
        event.set()

    helper = LighthouseConfigWriter(scf.cf)
    helper.write_and_store_config(data_written, geos=geo_dict)
    event.wait()


# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

if __name__ == '__main__':
    uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    print(f'Step 1. Connecting to the Crazyflie on uri {uri}...')
    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        print('  Connected')
        print('')
        print('In the 3 following steps we will define the coordinate system.')
        print('Step 2. Put the Crazyflie where you want the origin of your coordinate system.')
        input('Press return when ready. ')
        print('  Recording...')
        origin = record_angles_average(scf)

        print('Step 3. Put the Crazyflie somehere on the positive X-axis.')
        print('Multiple samples can be recorded if you want to, type "r" before you hit enter to repeat the step.')
        x_axis = []
        do_repeat = True
        while do_repeat:
            do_repeat = 'r' == input('Press return when ready. ').lower()
            print('  Recording...')
            x_axis.append(record_angles_average(scf))

        print('Step 4. Put the Crazyflie somehere in the XY-plane, but not on the X-axis.')
        print('Multiple samples can be recorded if you want to, type "r" before you hit enter to repeat the step.')
        xy_plane = []
        do_repeat = True
        while do_repeat:
            do_repeat = 'r' == input('Press return when ready. ').lower()
            print('  Recording...')
            xy_plane.append(record_angles_average(scf))

        print()
        print('Step 5. We will now record data from the space you plan to fly in and optimize the base station ' +
              'geometry based on this data. Move the Crazyflie around, try to cover all of the space, make sure ' +
              'all the base stations are received and do not move too fast. Make sure the Crazyflie is fairly ' +
              'level during the recording.')
        print('This step does not add anything in a system with only one base station, enter 0 in this case.')
        default_time = 10
        recording_time = input(f'Enter the number of seconds you want to record ({default_time} by default), ' +
                               'recording starts when you hit enter. ')
        recording_time_s = parse(recording_time, default_time)
        print('  Recording started...')
        samples = record_angles_sequence(scf, recording_time_s)
        print('  Recording ended')

        print('Step 6. Estimating geometry...')
        bs_poses = estimate_geometry(origin, x_axis, xy_plane, samples)
        print('  Geometry estimated')

        print('Step 7. Upload geometry to the Crazyflie')
        input('Press enter to upload geometry. ')
        upload_geometry(scf, bs_poses)
        print('Geometry uploaded')
