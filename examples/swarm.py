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
import asyncio
import sys

from cflib import Crazyflie, LinkContext


def get_info(cf: Crazyflie) -> tuple[str, str]:
    """Get firmware version and device type.

    This is a regular blocking function - all calls inside run sequentially.
    We run one instance per drone in separate threads via asyncio.to_thread(),
    so multiple drones execute this function in parallel.
    """
    platform = cf.platform()
    fw = platform.get_firmware_version()
    device = platform.get_device_type_name()
    return fw, device


async def main() -> None:
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

    # Shared LinkContext for all connections
    context = LinkContext()

    # Connect to all concurrently - each connection runs in its own thread,
    # asyncio.gather() waits for all to complete before continuing
    print(f"Connecting to {len(args.uris)} Crazyflies...")
    cfs = await asyncio.gather(
        *[
            asyncio.to_thread(Crazyflie.connect_from_uri, context, uri)
            for uri in args.uris
        ]
    )
    print("All connected!\n")

    try:
        # Run get_info() for each drone in parallel threads, wait for all to finish
        infos = await asyncio.gather(*[asyncio.to_thread(get_info, cf) for cf in cfs])

        for uri, (fw, device) in zip(args.uris, infos):
            print(f"{uri}: {device}, firmware {fw}")

    finally:
        # Disconnect all concurrently
        print("\nDisconnecting...")
        await asyncio.gather(*[asyncio.to_thread(cf.disconnect) for cf in cfs])
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
