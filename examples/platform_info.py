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
Read and display Crazyflie platform information.

Shows protocol version, firmware version, and device type.
Note: Protocol version is automatically checked by the Rust library
to ensure compatibility.

Example usage:
    python platform_info.py                              # Use default URI
    python platform_info.py radio://0/80/2M/E7E7E7E701   # Custom URI
"""

import argparse
import asyncio

from cflib import Crazyflie, LinkContext


async def main() -> None:
    parser = argparse.ArgumentParser(description="Read Crazyflie platform information")
    parser.add_argument(
        "uri",
        nargs="?",
        default="radio://0/80/2M/E7E7E7E7E7",
        help="Crazyflie URI (default: radio://0/80/2M/E7E7E7E7E7)",
    )
    args: argparse.Namespace = parser.parse_args()

    print(f"Connecting to {args.uri}...")
    context = LinkContext()
    cf = await Crazyflie.connect_from_uri(context, args.uri)
    print("Connected!")

    platform = cf.platform()

    try:
        print("\nReading platform information...")
        print("-" * 60)

        # Get protocol version
        protocol_version: int = await platform.get_protocol_version()
        print(f"Protocol version: {protocol_version}")

        # Get firmware version
        firmware_version: str = await platform.get_firmware_version()
        print(f"Firmware version: {firmware_version}")

        # Get device type name
        device_type: str = await platform.get_device_type_name()
        print(f"Device type:      {device_type}")

        print("-" * 60)
        print("\n✓ Platform information retrieved successfully!")

    finally:
        print("\nDisconnecting...")
        await cf.disconnect()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
