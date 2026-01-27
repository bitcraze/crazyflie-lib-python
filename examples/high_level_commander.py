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

import asyncio
import math
import argparse

from cflib import Crazyflie, LinkContext


async def main() -> None:
    parser = argparse.ArgumentParser(description="High-level commander example")
    parser.add_argument(
        "uri",
        nargs="?",
        default="radio://0/80/2M/E7E7E7E7E7",
        help="Crazyflie URI (default: radio://0/80/2M/E7E7E7E7E7)",
    )
    args: argparse.Namespace = parser.parse_args()

    ctx = LinkContext()

    print(f"Connecting to {args.uri}...")
    cf = await Crazyflie.connect_from_uri(ctx, args.uri)
    print("Connected!")

    hlc = cf.high_level_commander()

    print("Taking off...")
    try:
        await hlc.take_off(0.5, None, 2.0, None)
        await asyncio.sleep(2.0)
    except Exception as e:
        print(f"Take-off failed: {e}")

    print("Going to first position...")
    try:
        await hlc.go_to(0.0, 0.5, 0.5, 0.0, 2.0, False, False, None)
        await asyncio.sleep(2.0)
    except Exception as e:
        print(f"Go-to failed: {e}")

    print("Going to second position...")
    try:
        await hlc.go_to(-0.25, 0.0, 0.5, 0.0, 2.0, False, False, None)
        await asyncio.sleep(2.0)
    except Exception as e:
        print(f"Go-to failed: {e}")

    print("Moving in a spiral...")
    try:
        await hlc.spiral(-math.pi * 2.0, 0.5, 0.5, 0.0, 2.0, True, True, None)
        await asyncio.sleep(2.0)
    except Exception as e:
        print(f"Spiral failed: {e}")

    print("Landing...")
    try:
        await hlc.land(0.0, None, 2.0, None)
        await asyncio.sleep(2.0)
    except Exception as e:
        print(f"Landing failed: {e}")

    await hlc.stop(None)
    print("Done")

    await cf.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
