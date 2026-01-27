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
Stream accelerometer data from a Crazyflie at 100ms intervals.

Demonstrates how to create a log block, add variables, and stream telemetry
data from the Crazyflie. The example shows proper error handling and cleanup.

Example usage:
    python log.py                              # Connect to default URI
    python log.py radio://0/80/2M/E7E7E7E701   # Connect to custom URI
"""

import argparse
import asyncio

from cflib import Crazyflie, LinkContext


LOG_INTERVAL = 100  # ms


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stream accelerometer data from the Crazyflie"
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
    cf = await Crazyflie.connect_from_uri(context, args.uri)
    print("Connected!")

    log = cf.log()

    # Create log block and add accelerometer variables
    block = await log.create_block()
    await block.add_variable("acc.x")
    await block.add_variable("acc.y")
    await block.add_variable("acc.z")

    log_stream = await block.start(LOG_INTERVAL)
    print(f"\nStreaming at {LOG_INTERVAL}ms intervals. Press Ctrl+C to stop.\n")

    try:
        while True:
            data = await log_stream.next()
            timestamp = data["timestamp"]
            values = data["data"]

            print(
                f"t={timestamp:6d}ms  "
                f"x={values['acc.x']:7.3f}  "
                f"y={values['acc.y']:7.3f}  "
                f"z={values['acc.z']:7.3f}"
            )
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        await log_stream.stop()
        await cf.disconnect()
        print("Disconnected")


if __name__ == "__main__":
    asyncio.run(main())
