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
Stream lighthouse angle data from a Crazyflie with Lighthouse deck.

This example demonstrates how to:
- Enable lighthouse V2 system
- Enable angle streaming
- Receive and display sweep angles from visible base stations

REQUIREMENTS:
- Crazyflie with Lighthouse deck
- Lighthouse V2 base stations visible to the Crazyflie
- Base station calibration data already received by the Crazyflie

The angle data shows the horizontal (x) and vertical (y) sweep angles
measured by each of the 4 IR sensors on the Lighthouse deck.

Example usage:
    python lighthouse_angles.py                              # Use default URI
    python lighthouse_angles.py radio://0/80/2M/E7E7E7E701   # Custom URI
"""

import argparse
import time

from cflib import Crazyflie


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stream lighthouse angle data from the Crazyflie"
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
    localization = cf.localization()
    lighthouse = localization.lighthouse()

    try:
        # Set lighthouse to V2 mode
        print("\n1. Setting lighthouse to V2 mode...")
        param.set("lighthouse.systemType", 2)
        print("   ✓ Lighthouse set to V2 mode")

        # Enable angle streaming
        print("\n2. Enabling lighthouse angle stream...")
        param.set("locSrv.enLhAngleStream", 1)
        print("   ✓ Angle streaming enabled")

        print("\n3. Streaming lighthouse angles for 10 seconds...")
        print("   Move the Crazyflie around to see different base stations")
        print("   Press Ctrl+C to stop early\n")

        start_time = time.time()
        duration = 10.0  # seconds
        base_stations_seen: set[int] = set()
        sample_count = 0

        while time.time() - start_time < duration:
            # Get angle data (buffered, up to 100 measurements)
            angle_data_list = lighthouse.get_angle_data()

            for angle_data in angle_data_list:
                sample_count += 1
                base_station = angle_data.base_station
                base_stations_seen.add(base_station)

                angles = angle_data.angles
                x_angles = angles.x
                y_angles = angles.y

                print(
                    f"BS {base_station}: "
                    f"x=[{x_angles[0]:6.3f}, {x_angles[1]:6.3f}, {x_angles[2]:6.3f}, {x_angles[3]:6.3f}], "
                    f"y=[{y_angles[0]:6.3f}, {y_angles[1]:6.3f}, {y_angles[2]:6.3f}, {y_angles[3]:6.3f}]"
                )

            # Small delay to avoid busy-waiting
            time.sleep(0.001)

        # Disable angle streaming
        print("\n4. Disabling angle stream...")
        param.set("locSrv.enLhAngleStream", 0)
        print("   ✓ Angle streaming disabled")

        # Show summary
        print("\nSummary:")
        print(f"  Total samples: {sample_count}")
        if base_stations_seen:
            bs_sorted = sorted(base_stations_seen)
            print(f"  Base stations seen: {bs_sorted}")
        else:
            print("  Base stations seen: None (no lighthouse signal detected)")

        print("\n✓ Lighthouse angle streaming demonstration complete!")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        print("\nDisabling angle stream...")
        try:
            param.set("locSrv.enLhAngleStream", 0)
            print("   ✓ Angle streaming disabled")
        except Exception as e:
            print(f"   ⚠️  Could not disable angle stream: {e}")

    finally:
        print("\nDisconnecting...")
        cf.disconnect()
        print("Done!")


if __name__ == "__main__":
    main()
