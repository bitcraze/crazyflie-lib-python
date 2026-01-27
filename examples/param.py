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
Demonstrate reading and writing Crazyflie parameters.

Shows how to:
- Get a parameter value (pm.lowVoltage - battery low voltage threshold)
- Set a temporary new value (3.8V)
- Restore the original value

Example usage:
    python param.py                              # Use default URI
    python param.py radio://0/80/2M/E7E7E7E701   # Custom URI
"""

import argparse

from cflib import Crazyflie, LinkContext


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Get/set Crazyflie parameters (demonstrates pm.lowVoltage)"
    )
    parser.add_argument(
        "uri",
        nargs="?",
        default="radio://0/80/2M/E7E7E7E7E7",
        help="Crazyflie URI (default: radio://0/80/2M/E7E7E7E7E7)",
    )
    args: argparse.Namespace = parser.parse_args()

    print(f"Connecting to {args.uri}...")
    context = LinkContext()
    cf = Crazyflie.connect_from_uri(context, args.uri)
    print("Connected!")

    param = cf.param()
    param_name = "pm.lowVoltage"

    try:
        # Get original value
        print(f"\n1. Getting original value of '{param_name}'...")
        original_value: int | float = param.get(param_name)
        print(f"   Original value: {original_value}V")

        # Set new value
        new_value: float = 3.8
        print(f"\n2. Setting '{param_name}' to {new_value}V...")
        param.set(param_name, new_value)
        print(f"   Set complete!")

        # Get new value to confirm
        print(f"\n3. Reading back '{param_name}'...")
        current_value: int | float = param.get(param_name)
        print(f"   Current value: {current_value}V")

        # Restore original value
        print(f"\n4. Restoring '{param_name}' to original value ({original_value}V)...")
        param.set(param_name, float(original_value))
        print(f"   Restored!")

        # Get final value to confirm restoration
        print(f"\n5. Verifying restoration of '{param_name}'...")
        final_value: int | float = param.get(param_name)
        print(f"   Final value: {final_value}V")

        if final_value == original_value:
            print("\n✓ Parameter successfully restored to original value!")
        else:
            print(
                f"\n⚠ Warning: Final value ({final_value}) differs from original ({original_value})"
            )

    finally:
        print("\nDisconnecting...")
        cf.disconnect()
        print("Done!")


if __name__ == "__main__":
    main()
