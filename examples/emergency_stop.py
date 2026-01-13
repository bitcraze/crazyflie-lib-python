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
Demonstrate emergency stop functionality.

Arms the Crazyflie, spins the motors, then sends an emergency stop command.
The emergency stop will immediately cut power to all motors and put the drone
into a locked state that requires a reboot to recover.

WARNING: Only run this when the Crazyflie is in a safe location!
WARNING: After emergency stop, the Crazyflie will require a reboot to function again.

Example usage:
    python emergency_stop.py                              # Use default URI
    python emergency_stop.py radio://0/80/2M/E7E7E7E701   # Custom URI
"""

import argparse
import time

from cflib import Crazyflie


def main() -> None:
    parser = argparse.ArgumentParser(description="Demonstrate emergency stop")
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

    platform = cf.platform()
    commander = cf.commander()
    localization = cf.localization()
    emergency = localization.emergency()

    try:
        print("\n⚠️  WARNING: This will ARM and SPIN the motors!")
        print("⚠️  Ensure the Crazyflie is in a safe location.")
        print("⚠️  After emergency stop, the Crazyflie will require a REBOOT!")
        print()
        input("Press Enter to continue or Ctrl+C to abort...")

        # Arm the Crazyflie
        print("\n1. Arming the Crazyflie...")
        platform.send_arming_request(do_arm=True)
        time.sleep(0.3)
        print("   ✓ Armed!")

        # Send unlock setpoint
        print("\n2. Sending unlock setpoint...")
        commander.send_setpoint_rpyt(roll=0.0, pitch=0.0, yaw_rate=0.0, thrust=0)
        time.sleep(0.1)
        print("   ✓ Unlocked!")

        # Spin motors for 1 second
        print("\n3. Spinning motors at medium thrust for 1 second...")
        start_time = time.time()
        while time.time() - start_time < 1.0:
            commander.send_setpoint_rpyt(
                roll=0.0, pitch=0.0, yaw_rate=0.0, thrust=15000
            )
            time.sleep(0.1)
        print("   ✓ Motors spinning!")

        # Send emergency stop
        print("\n4. Sending emergency stop command...")
        emergency.send_emergency_stop()
        time.sleep(0.5)
        print("   ✓ Emergency stop sent!")

        print("\n⚠️  Drone is now LOCKED and requires a REBOOT to function again.")
        print("✓ Emergency stop demonstration complete!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted! Attempting to disarm for safety...")
        try:
            platform.send_arming_request(do_arm=False)
            print("   ✓ Disarmed!")
        except Exception:
            print("   ⚠️  Could not disarm (may already be in emergency state)")

    finally:
        print("\nDisconnecting...")
        cf.disconnect()
        print("Done!")


if __name__ == "__main__":
    main()
