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
Demonstrate arming and disarming the Crazyflie.

Arms the Crazyflie (enabling motors), waits a few seconds, then disarms.
When armed, motors can spin if thrust commands are sent.
When disarmed, motors will not spin even if thrust commands are sent.

WARNING: Only run this when the Crazyflie is in a safe location!

Example usage:
    python arming.py                              # Use default URI
    python arming.py radio://0/80/2M/E7E7E7E701   # Custom URI
"""

import argparse
import time

from cflib import Crazyflie


def main() -> None:
    parser = argparse.ArgumentParser(description="Arm and disarm the Crazyflie")
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

    try:
        print("\n⚠️  WARNING: This will ARM the Crazyflie!")
        print("⚠️  Ensure it is in a safe location before continuing.")
        print()
        input("Press Enter to continue or Ctrl+C to abort...")

        # Arm the Crazyflie
        print("\n1. Arming the Crazyflie...")
        platform.send_arming_request(do_arm=True)
        print("   ✓ Armed! Motors can now spin.")

        # Wait a few seconds
        wait_time = 3
        print(f"\n2. Waiting {wait_time} seconds...")
        for i in range(wait_time, 0, -1):
            print(f"   {i}...")
            time.sleep(1)

        # Disarm the Crazyflie
        print("\n3. Disarming the Crazyflie...")
        platform.send_arming_request(do_arm=False)
        print("   ✓ Disarmed! Motors are now disabled.")

        print("\n✓ Arming cycle complete!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted! Disarming for safety...")
        platform.send_arming_request(do_arm=False)
        print("   ✓ Disarmed!")

    finally:
        print("\nDisconnecting...")
        cf.disconnect()
        print("Done!")


if __name__ == "__main__":
    main()
