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
Send external pose (position + orientation) data to the Crazyflie's Kalman filter.

This example demonstrates how to send motion capture data to the Crazyflie for
position control. It:
- Configures the Kalman filter estimator
- Sends a circular trajectory with full 6DOF pose (position + quaternion)
- Monitors the state estimate using log blocks to verify tracking
- Shows Euler-to-quaternion conversion using Crazyflie's convention

This is useful for motion capture systems, optical tracking, or any external
positioning system that provides 6DOF pose data.

Example usage:
    python external_position.py                              # Use default URI
    python external_position.py radio://0/80/2M/E7E7E7E701   # Custom URI
"""

import argparse
import math
import time

from cflib import Crazyflie


def euler_to_quaternion(roll: float, pitch: float, yaw: float) -> list[float]:
    """
    Convert Euler angles (roll, pitch, yaw) to quaternion.

    Uses Tait-Bryan ZYX convention matching Crazyflie's rpy2quat() function.
    NOTE: Pitch is negated for coordinate system compatibility.

    Args:
        roll: Roll angle in radians
        pitch: Pitch angle in radians
        yaw: Yaw angle in radians

    Returns:
        Quaternion as [qx, qy, qz, qw]
    """
    # Negate pitch for Crazyflie coordinate system
    roll_rad = roll
    pitch_rad = -pitch
    yaw_rad = yaw

    # Half angles
    cr = math.cos(roll_rad / 2.0)
    sr = math.sin(roll_rad / 2.0)
    cp = math.cos(pitch_rad / 2.0)
    sp = math.sin(pitch_rad / 2.0)
    cy = math.cos(yaw_rad / 2.0)
    sy = math.sin(yaw_rad / 2.0)

    # Tait-Bryan ZYX conversion (from Crazyflie math3d.h)
    qx = sr * cp * cy - cr * sp * sy
    qy = cr * sp * cy + sr * cp * sy
    qz = cr * cp * sy - sr * sp * cy
    qw = cr * cp * cy + sr * sp * sy

    return [qx, qy, qz, qw]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send external pose data to Kalman filter"
    )
    parser.add_argument(
        "uri",
        nargs="?",
        default="radio://0/80/2M/E7E7E7E7E7",
        help="Crazyflie URI (default: radio://0/80/2M/E7E7E7E7E7)",
    )
    args: argparse.Namespace = parser.parse_args()

    print(f"Connecting to {args.uri}...")
    cf = Crazyflie.connect_from_uri(args.uri)
    print("Connected!")

    param = cf.param()
    log = cf.log()
    localization = cf.localization()
    external_pose = localization.external_pose()

    try:
        # Configure Kalman filter estimator
        print("\n1. Configuring Kalman filter estimator...")
        param.set("stabilizer.estimator", 2)  # 2 = Kalman filter
        print("   ✓ Set estimator to Kalman filter")

        # Set standard deviation for quaternion data
        print("\n2. Configuring orientation sensitivity...")
        param.set("locSrv.extQuatStdDev", 0.008)  # 8.0e-3
        print("   ✓ Set quaternion std deviation to 0.008")

        # Reset the estimator
        print("\n3. Resetting Kalman filter...")
        param.set("kalman.resetEstimation", 1)
        time.sleep(0.1)
        param.set("kalman.resetEstimation", 0)
        print("   ✓ Estimator reset")

        # Wait for estimator to stabilize
        print("\n4. Waiting for estimator to stabilize (2 seconds)...")
        time.sleep(2)
        print("   ✓ Estimator ready")

        # Create log blocks for monitoring state estimate
        print("\n5. Setting up log blocks...")
        quat_block = log.create_block()
        quat_block.add_variable("stateEstimate.qx")
        quat_block.add_variable("stateEstimate.qy")
        quat_block.add_variable("stateEstimate.qz")
        quat_block.add_variable("stateEstimate.qw")

        pos_block = log.create_block()
        pos_block.add_variable("stateEstimate.x")
        pos_block.add_variable("stateEstimate.y")
        pos_block.add_variable("stateEstimate.z")

        log_period_ms = 100
        update_period_ms = 50
        log_every_n = log_period_ms // update_period_ms

        quat_stream = quat_block.start(log_period_ms)
        pos_stream = pos_block.start(log_period_ms)
        print("   ✓ Log blocks created and started")

        # Send circular trajectory with pose data
        print("\n6. Sending external pose data (circular trajectory)...")
        print("   Press Ctrl+C to stop\n")

        iteration = 0
        max_iterations = 500  # Run for ~25 seconds (500 * 50ms)

        while iteration < max_iterations:
            t = iteration * 0.01

            # Circular trajectory
            x = math.cos(t) * 0.5
            y = math.sin(t) * 0.5
            z = 0.0

            # Oscillating orientation
            roll = math.sin(t * 2.0 * math.pi) * 0.2  # Small roll oscillation
            pitch = math.cos(t * 2.0 * math.pi) * 0.15  # Small pitch oscillation
            yaw = 1.2  # Steady yaw rotation

            # Convert to quaternion
            quat = euler_to_quaternion(roll, pitch, yaw)

            # Send pose to Crazyflie
            external_pose.send_external_pose(pos=[x, y, z], quat=quat)

            # Log every N iterations
            if iteration % log_every_n == 0:
                pos_data = pos_stream.next()
                quat_data = quat_stream.next()

                pos_values = pos_data["data"]
                quat_values = quat_data["data"]

                state_x = pos_values["stateEstimate.x"]
                state_y = pos_values["stateEstimate.y"]
                state_z = pos_values["stateEstimate.z"]
                state_qx = quat_values["stateEstimate.qx"]
                state_qy = quat_values["stateEstimate.qy"]
                state_qz = quat_values["stateEstimate.qz"]
                state_qw = quat_values["stateEstimate.qw"]

                print(
                    f"Sent:  pos=[{x:5.2f}, {y:5.2f}, {z:5.2f}] "
                    f"quat=[{quat[0]:6.3f}, {quat[1]:6.3f}, {quat[2]:6.3f}, {quat[3]:6.3f}]"
                )
                print(
                    f"State: pos=[{state_x:5.2f}, {state_y:5.2f}, {state_z:5.2f}] "
                    f"quat=[{state_qx:6.3f}, {state_qy:6.3f}, {state_qz:6.3f}, {state_qw:6.3f}]\n"
                )

            iteration += 1
            time.sleep(update_period_ms / 1000.0)

        print("\n✓ External pose demonstration complete!")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    finally:
        print("\nDisconnecting...")
        cf.disconnect()
        print("Done!")


if __name__ == "__main__":
    main()
