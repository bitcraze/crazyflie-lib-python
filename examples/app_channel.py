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
Demonstrate bidirectional app channel communication with Crazyflie.

This example communicates with the Crazyflie's App channel test example:
https://github.com/bitcraze/crazyflie-firmware/tree/master/examples/app_appchannel_test

The example sends 3 floats, the Crazyflie sums the 3 floats and returns the sum
as one float.

Example usage:
    python app_channel.py                              # Connect to default URI
    python app_channel.py radio://0/80/2M/E7E7E7E701   # Connect to custom URI
"""

import argparse
import struct
import time

from cflib._rust import Crazyflie


def main() -> None:
    parser = argparse.ArgumentParser(description="Test bidirectional app channel")
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

    platform = cf.platform()
    app_channel = platform.get_app_channel()

    if app_channel is None:
        print("Error: Could not acquire app channel (already in use?)")
        cf.disconnect()
        return

    print("\nApp channel acquired!")
    print("Communicating with app_appchannel_test firmware example...")
    print("-" * 60)

    try:
        # Test 1: 0+0+0 = 0
        print("\nTest 1: Sending 0+0+0...")
        packet = struct.pack("<fff", 0.0, 0.0, 0.0)
        app_channel.send(packet)

        # Wait a bit for response
        time.sleep(0.1)

        responses = app_channel.receive()
        if responses:
            result = struct.unpack("<f", responses[0])[0]
            print(f"Received: {result}")
            assert result == 0.0, f"Expected 0.0, got {result}"
            print("✓ Test 1 passed!")

        # Test 2: 1+2+3 = 6
        print("\nTest 2: Sending 1+2+3...")
        a, b, c = 1.0, 2.0, 3.0
        packet = struct.pack("<fff", a, b, c)
        app_channel.send(packet)

        # Wait a bit for response
        time.sleep(0.1)

        responses = app_channel.receive()
        if responses:
            result = struct.unpack("<f", responses[0])[0]
            expected = a + b + c
            print(f"Received: {result}")
            assert abs(result - expected) < 0.001, f"Expected {expected}, got {result}"
            print("✓ Test 2 passed!")

        # Test 3: 5.5+10.25+3.75 = 19.5
        print("\nTest 3: Sending 5.5+10.25+3.75...")
        a, b, c = 5.5, 10.25, 3.75
        packet = struct.pack("<fff", a, b, c)
        app_channel.send(packet)

        # Wait a bit for response
        time.sleep(0.1)

        responses = app_channel.receive()
        if responses:
            result = struct.unpack("<f", responses[0])[0]
            expected = a + b + c
            print(f"Received: {result}")
            assert abs(result - expected) < 0.001, f"Expected {expected}, got {result}"
            print("✓ Test 3 passed!")

        print("\n" + "-" * 60)
        print("All tests passed! ✓")

    except ValueError as e:
        print(f"\nError: {e}")
    except KeyboardInterrupt:
        print("\n" + "-" * 60)
        print("Interrupted by user")
    finally:
        print("\nDisconnecting...")
        cf.disconnect()
        print("Done!")


if __name__ == "__main__":
    main()
