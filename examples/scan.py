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
Scan for Crazyflies on the default address or a custom address provided via command line.

Example usage:
    python scan.py                    # Scan default address E7E7E7E7E7
    python scan.py --address E7E7E7E701  # Scan custom address
"""

import argparse

from cflib._rust import LinkContext


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan for Crazyflies")
    parser.add_argument(
        "--address",
        default="E7E7E7E7E7",
        help="Address to scan (5 bytes in hex, e.g., E7E7E7E7E7)",
    )
    args: argparse.Namespace = parser.parse_args()

    # Parse address from hex string to bytes
    if len(args.address) != 10:
        raise ValueError("Address must be exactly 10 hex characters (5 bytes)")
    if not all(c in "0123456789ABCDEF" for c in args.address):
        raise ValueError(f"Address contains non-hex characters: {args.address}")
    address_bytes: bytes = bytes.fromhex(args.address)

    print(f"Scanning for Crazyflies on address {args.address}...")

    context = LinkContext()
    uris = context.scan(address=list(address_bytes))

    if uris:
        print(f"\nFound {len(uris)} Crazyflie(s):")
        for uri in uris:
            print(f"  - {uri}")
    else:
        print("\nNo Crazyflies found.")


if __name__ == "__main__":
    main()
