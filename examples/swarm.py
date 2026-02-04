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
- Optionally use TOC file caching for faster reconnections

The shared LinkContext enables efficient radio multiplexing for swarm operations.

Example usage:
    python swarm.py radio://0/80/2M/E7E7E7E701 radio://0/80/2M/E7E7E7E702
    python swarm.py --cache radio://0/80/2M/E7E7E7E701 radio://0/80/2M/E7E7E7E702
"""

import argparse
import asyncio
import sys
import tempfile
import time
from pathlib import Path

from cflib import Crazyflie, LinkContext, FileTocCache, NoTocCache


async def timed_connect(
    context: LinkContext, uri: str, cache: FileTocCache | NoTocCache
) -> tuple[Crazyflie, float]:
    """Connect to a Crazyflie and return the connection time."""
    start = time.perf_counter()
    cf = await Crazyflie.connect_from_uri(context, uri, cache)
    elapsed = time.perf_counter() - start
    return cf, elapsed


async def get_info(cf: Crazyflie) -> tuple[str, str]:
    """Get firmware version and device type.

    Async function that directly uses async methods.
    """
    platform = cf.platform()
    fw = await platform.get_firmware_version()
    device = await platform.get_device_type_name()
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
    parser.add_argument(
        "--cache",
        action="store_true",
        help="Enable TOC file caching (uses OS temp directory)",
    )
    args: argparse.Namespace = parser.parse_args()

    # Set up TOC cache (file-based if --cache specified, otherwise no caching)
    if args.cache:
        # cache_dir = str(Path(tempfile.gettempdir()) / "crazyflie_toc_cache")
        cache_dir = str(Path.cwd() / "cache")
        cache = FileTocCache(cache_dir)
        print(f"Using TOC cache: {cache.get_cache_dir()}")
    else:
        cache = NoTocCache()

    # Shared LinkContext for all connections
    context = LinkContext()

    # Connect to all concurrently
    print(f"Connecting to {len(args.uris)} Crazyflies...")
    start = time.perf_counter()
    results = await asyncio.gather(
        *[timed_connect(context, uri, cache) for uri in args.uris]
    )
    total_time = time.perf_counter() - start
    cfs = [cf for cf, _ in results]
    connect_times = [t for _, t in results]

    print("All connected!\n")
    print("Connection times:")
    for uri, t in zip(args.uris, connect_times):
        print(f"  {uri}: {t:.3f}s")
    print(f"  Total (wall-clock): {total_time:.3f}s\n")

    try:
        # Run get_info() for each drone in parallel, wait for all to finish
        infos = await asyncio.gather(*[get_info(cf) for cf in cfs])

        for uri, (fw, device) in zip(args.uris, infos):
            print(f"{uri}: {device}, firmware {fw}")

    finally:
        # Disconnect all concurrently
        print("\nDisconnecting...")
        await asyncio.gather(*[cf.disconnect() for cf in cfs])
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
