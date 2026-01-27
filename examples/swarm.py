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
Demonstrate connecting to multiple Crazyflies using a shared LinkContext.

This example shows how to:
- Share a single LinkContext between multiple Crazyflie connections
- Connect to multiple drones through the same radio
- Read parameters from each drone

The shared LinkContext enables efficient radio multiplexing for swarm operations.

Example usage:
    python swarm.py radio://0/80/2M/E7E7E7E701 radio://0/80/2M/E7E7E7E702
"""

import argparse
import sys

from cflib import Crazyflie, LinkContext


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Connect to multiple Crazyflies using shared LinkContext"
    )
    parser.add_argument(
        "uris",
        nargs="+",
        help="Crazyflie URIs (e.g., radio://0/80/2M/E7E7E7E701 radio://0/80/2M/E7E7E7E702)",
    )
    args: argparse.Namespace = parser.parse_args()

    if len(args.uris) < 2:
        print("Please provide at least 2 URIs to demonstrate swarming")
        sys.exit(1)

    # Create a SINGLE shared LinkContext for all connections
    print("Creating shared LinkContext...")
    context = LinkContext()

    crazyflies: list[Crazyflie] = []

    try:
        # Connect to all Crazyflies using the same context
        for uri in args.uris:
            print(f"Connecting to {uri}...")
            cf = Crazyflie.connect_from_uri(context, uri)
            crazyflies.append(cf)
            print(f"  Connected!")

        print(f"\nSuccessfully connected to {len(crazyflies)} Crazyflies!\n")

        # Read platform info from each Crazyflie
        for i, cf in enumerate(crazyflies):
            platform = cf.platform()
            fw_version = platform.get_firmware_version()
            device_type = platform.get_device_type_name()
            print(
                f"Crazyflie {i + 1} ({args.uris[i]}): {device_type}, firmware {fw_version}"
            )

    finally:
        # Disconnect all
        print("\nDisconnecting all Crazyflies...")
        for cf in crazyflies:
            cf.disconnect()
        print("Done!")


if __name__ == "__main__":
    main()
