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
"""
Upload and fly a figure-8 trajectory using the high-level commander.

This example demonstrates:
- Creating Poly4D trajectory segments from coefficient arrays
- Uploading trajectory data to Crazyflie memory
- Defining and executing trajectories with the high-level commander
- Using relative positioning and optional relative yaw

The trajectory can work with any positioning system (LPS, Lighthouse, etc.)

Example usage:
    python trajectory_figure8.py                         # Default URI
    python trajectory_figure8.py --relative-yaw          # With relative yaw
    python trajectory_figure8.py radio://0/80/2M/E7E7E7E701  # Custom URI
"""

import argparse
import asyncio

from cflib import Crazyflie, LinkContext
from cflib.trajectory import Poly, Poly4D

# The trajectory to fly
# See https://github.com/whoenig/uav_trajectories for a tool to generate
# trajectories

# Duration,x^0,x^1,x^2,x^3,x^4,x^5,x^6,x^7,y^0,y^1,y^2,y^3,y^4,y^5,y^6,y^7,z^0,z^1,z^2,z^3,z^4,z^5,z^6,z^7,yaw^0,yaw^1,yaw^2,yaw^3,yaw^4,yaw^5,yaw^6,yaw^7
figure8 = [
    [
        1.050000,
        0.000000,
        -0.000000,
        0.000000,
        -0.000000,
        0.830443,
        -0.276140,
        -0.384219,
        0.180493,
        -0.000000,
        0.000000,
        -0.000000,
        0.000000,
        -1.356107,
        0.688430,
        0.587426,
        -0.329106,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
    ],  # noqa
    [
        0.710000,
        0.396058,
        0.918033,
        0.128965,
        -0.773546,
        0.339704,
        0.034310,
        -0.026417,
        -0.030049,
        -0.445604,
        -0.684403,
        0.888433,
        1.493630,
        -1.361618,
        -0.139316,
        0.158875,
        0.095799,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
    ],  # noqa
    [
        0.620000,
        0.922409,
        0.405715,
        -0.582968,
        -0.092188,
        -0.114670,
        0.101046,
        0.075834,
        -0.037926,
        -0.291165,
        0.967514,
        0.421451,
        -1.086348,
        0.545211,
        0.030109,
        -0.050046,
        -0.068177,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
    ],  # noqa
    [
        0.700000,
        0.923174,
        -0.431533,
        -0.682975,
        0.177173,
        0.319468,
        -0.043852,
        -0.111269,
        0.023166,
        0.289869,
        0.724722,
        -0.512011,
        -0.209623,
        -0.218710,
        0.108797,
        0.128756,
        -0.055461,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
    ],  # noqa
    [
        0.560000,
        0.405364,
        -0.834716,
        0.158939,
        0.288175,
        -0.373738,
        -0.054995,
        0.036090,
        0.078627,
        0.450742,
        -0.385534,
        -0.954089,
        0.128288,
        0.442620,
        0.055630,
        -0.060142,
        -0.076163,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
    ],  # noqa
    [
        0.560000,
        0.001062,
        -0.646270,
        -0.012560,
        -0.324065,
        0.125327,
        0.119738,
        0.034567,
        -0.063130,
        0.001593,
        -1.031457,
        0.015159,
        0.820816,
        -0.152665,
        -0.130729,
        -0.045679,
        0.080444,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
    ],  # noqa
    [
        0.700000,
        -0.402804,
        -0.820508,
        -0.132914,
        0.236278,
        0.235164,
        -0.053551,
        -0.088687,
        0.031253,
        -0.449354,
        -0.411507,
        0.902946,
        0.185335,
        -0.239125,
        -0.041696,
        0.016857,
        0.016709,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
    ],  # noqa
    [
        0.620000,
        -0.921641,
        -0.464596,
        0.661875,
        0.286582,
        -0.228921,
        -0.051987,
        0.004669,
        0.038463,
        -0.292459,
        0.777682,
        0.565788,
        -0.432472,
        -0.060568,
        -0.082048,
        -0.009439,
        0.041158,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
    ],  # noqa
    [
        0.710000,
        -0.923935,
        0.447832,
        0.627381,
        -0.259808,
        -0.042325,
        -0.032258,
        0.001420,
        0.005294,
        0.288570,
        0.873350,
        -0.515586,
        -0.730207,
        -0.026023,
        0.288755,
        0.215678,
        -0.148061,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
    ],  # noqa
    [
        1.053185,
        -0.398611,
        0.850510,
        -0.144007,
        -0.485368,
        -0.079781,
        0.176330,
        0.234482,
        -0.153567,
        0.447039,
        -0.532729,
        -0.855023,
        0.878509,
        0.775168,
        -0.391051,
        -0.713519,
        0.391628,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
        0.000000,
    ],  # noqa
]


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fly a figure-8 trajectory using Poly4D segments"
    )
    parser.add_argument(
        "uri",
        nargs="?",
        default="radio://0/80/2M/E7E7E7E7E7",
        help="Crazyflie URI (default: radio://0/80/2M/E7E7E7E7E7)",
    )
    parser.add_argument(
        "--relative-yaw",
        action="store_true",
        help="Enable relative_yaw mode (trajectory rotates based on prior orientation)",
    )
    args: argparse.Namespace = parser.parse_args()

    # Convert trajectory data to Poly4D segments
    print("Preparing trajectory segments...")
    trajectory: list[Poly4D] = []
    total_duration = 0.0

    for row in figure8:
        duration = row[0]
        x = Poly(row[1:9])
        y = Poly(row[9:17])
        z = Poly(row[17:25])
        yaw = Poly(row[25:33])
        trajectory.append(Poly4D(duration, x, y, z, yaw))
        total_duration += duration

    print(
        f"Trajectory has {len(trajectory)} segments, total duration: {total_duration:.1f}s"
    )

    # Connect to Crazyflie
    print(f"Connecting to {args.uri}...")
    ctx = LinkContext()
    cf = await Crazyflie.connect_from_uri(ctx, args.uri)
    print("Connected!")

    try:
        # Upload trajectory to memory
        print("Uploading trajectory to Crazyflie memory...")
        bytes_written = await cf.memory().write_trajectory(trajectory)
        print(f"Uploaded {bytes_written} bytes")

        # Define trajectory in high-level commander
        trajectory_id = 1
        hlc = cf.high_level_commander()
        await hlc.define_trajectory(trajectory_id, 0, len(trajectory), 0)
        print(f"Defined trajectory {trajectory_id}")

        # Execute flight sequence
        print("Starting flight sequence...")

        # Arm the Crazyflie
        print("Arming...")
        await cf.platform().send_arming_request(True)
        await asyncio.sleep(1.0)

        takeoff_yaw = 3.14 / 2 if args.relative_yaw else 0.0
        print("Taking off...")
        await hlc.take_off(1.0, takeoff_yaw, 2.0, None)
        await asyncio.sleep(3.0)

        print("Starting trajectory...")
        await hlc.start_trajectory(
            trajectory_id, 1.0, True, args.relative_yaw, False, None
        )
        await asyncio.sleep(total_duration)

        print("Landing...")
        await hlc.land(0.0, None, 2.0, None)
        await asyncio.sleep(2.0)

        await hlc.stop(None)
        print("Flight sequence complete!")

    finally:
        print("Disconnecting...")
        await cf.disconnect()
        print("Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
