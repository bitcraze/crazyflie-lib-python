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
Persist lighthouse geometry and calibration data to permanent storage.

This example demonstrates how to save lighthouse base station geometry and
calibration data from RAM to the Crazyflie's permanent storage (flash memory).

IMPORTANT: This example assumes geometry/calibration data has already been
written to the Crazyflie's RAM via the memory subsystem (not shown here).

In a real scenario, you would:
1. Estimate or load geometry data (e.g., from a lighthouse positioning system)
2. Write it to RAM via memory subsystem (NOT YET IMPLEMENTED in Python bindings)
3. Use this persist function to save to permanent storage

After persisting, the data will be available after reboot without needing
to re-estimate or re-upload.

REQUIREMENTS:
- Crazyflie with Lighthouse deck
- Geometry/calibration data already in RAM (via memory subsystem)

NOTE: The memory subsystem is not yet implemented in the Python bindings,
so this example demonstrates the persist API usage but may not work without
first uploading data via the memory subsystem.

Example usage:
    python lighthouse_persist.py                              # Use default URI
    python lighthouse_persist.py radio://0/80/2M/E7E7E7E701   # Custom URI
"""

import argparse

from cflib import Crazyflie, LinkContext


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Persist lighthouse data to permanent storage"
    )
    parser.add_argument(
        "uri",
        nargs="?",
        default="radio://0/80/2M/E7E7E7E7E7",
        help="Crazyflie URI (default: radio://0/80/2M/E7E7E7E7E7)",
    )
    parser.add_argument(
        "--geo",
        type=int,
        nargs="+",
        default=[0, 1],
        help="Base station IDs to persist geometry for (default: 0 1)",
    )
    parser.add_argument(
        "--calib",
        type=int,
        nargs="+",
        default=[0],
        help="Base station IDs to persist calibration for (default: 0)",
    )
    args: argparse.Namespace = parser.parse_args()

    print(f"Connecting to {args.uri}...")
    context = LinkContext()
    cf = Crazyflie.connect_from_uri(context, args.uri)
    print("Connected!")

    localization = cf.localization()
    lighthouse = localization.lighthouse()

    try:
        print(
            "\n⚠️  NOTE: This example assumes geometry/calibration data is already in RAM"
        )
        print("⚠️  The memory subsystem (for uploading data) is not yet implemented")
        print(
            "⚠️  This will ONLY work if data was previously uploaded via another method\n"
        )

        print("This example demonstrates the persist API usage.")
        print(f"\nGeometry base stations to persist: {args.geo}")
        print(f"Calibration base stations to persist: {args.calib}")
        print()
        input("Press Enter to continue or Ctrl+C to abort...")

        # Persist lighthouse data
        print("\n1. Persisting lighthouse data...")
        print("   Waiting for confirmation (5 second timeout)...")

        success = lighthouse.persist_lighthouse_data(
            geo_list=args.geo, calib_list=args.calib
        )

        if success:
            print("   ✓ Data persisted successfully!")
            print(
                "\n   The geometry and calibration data have been saved to permanent storage."
            )
            print("   This data will be available after reboot without re-uploading.")
        else:
            print("   ✗ Persistence failed!")
            print("\n   Possible reasons:")
            print("   - Geometry/calibration data not present in RAM")
            print("   - Invalid base station IDs")
            print("   - Memory subsystem error")
            print(
                "\n   Make sure to upload data via memory subsystem first (not yet implemented)."
            )

        print("\n✓ Lighthouse persist demonstration complete!")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    except Exception as e:
        print(f"\n✗ Error: {e}")

    finally:
        print("\nDisconnecting...")
        cf.disconnect()
        print("Done!")


if __name__ == "__main__":
    main()
