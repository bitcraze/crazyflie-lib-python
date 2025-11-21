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
Demonstrate emergency watchdog failsafe mechanism.

The emergency watchdog provides a safety failsafe: once activated, you must
continuously send watchdog messages at regular intervals (less than 1000ms apart).
If messages stop arriving for longer than the timeout, the drone will
automatically trigger an emergency stop.

This is useful for detecting communication failures or software crashes - if
your control loop stops sending messages, the drone will automatically stop
the motors for safety.

WARNING: Only run this when the Crazyflie is in a safe location!
WARNING: After emergency stop, the Crazyflie will require a reboot to function again.

Example usage:
    python emergency_watchdog.py                              # Use default URI
    python emergency_watchdog.py radio://0/80/2M/E7E7E7E701   # Custom URI
"""

import argparse
import sys
import time

from cflib._rust import Crazyflie


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demonstrate emergency watchdog failsafe"
    )
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
    commander = cf.commander()
    localization = cf.localization()
    emergency = localization.emergency()

    try:
        print("\n⚠️  WARNING: This will ARM and SPIN the motors!")
        print("⚠️  The watchdog will trigger an automatic emergency stop.")
        print("⚠️  After emergency stop, the Crazyflie will require a REBOOT!")
        print()
        input("Press Enter to continue or Ctrl+C to abort...")

        # Arm the Crazyflie
        print("\n1. Arming the Crazyflie...")
        platform.send_arming_request(do_arm=True)
        time.sleep(0.3)
        print("   ✓ Armed!")

        # Send unlock setpoint
        print("\n2. Sending unlock setpoint...")
        commander.send_setpoint_rpyt(roll=0.0, pitch=0.0, yaw_rate=0.0, thrust=0)
        time.sleep(0.1)
        print("   ✓ Unlocked!")

        # Start spinning motors at low thrust
        print("\n3. Starting motors at low thrust...")
        for _ in range(3):
            commander.send_setpoint_rpyt(roll=0.0, pitch=0.0, yaw_rate=0.0, thrust=8000)
            time.sleep(0.1)
        print("   ✓ Motors spinning!")

        # Activate watchdog
        print("\n4. Activating watchdog (1000ms timeout)...")
        emergency.send_emergency_stop_watchdog()
        print("   ✓ Watchdog activated!")

        print(
            "\n5. Sending periodic watchdog messages (every 800ms) while motors spin..."
        )
        print("   Once activated, watchdog MUST be continuously fed!")

        # Send 6 watchdog messages at 800ms intervals
        # Also keep motors spinning with more frequent setpoints
        for i in range(6):
            sys.stdout.write(f"   Message {i + 1}/6")
            sys.stdout.flush()

            # Send watchdog message
            emergency.send_emergency_stop_watchdog()

            # Keep motors spinning and wait 800ms
            for _ in range(8):
                commander.send_setpoint_rpyt(
                    roll=0.0, pitch=0.0, yaw_rate=0.0, thrust=8000
                )
                time.sleep(0.1)

            sys.stdout.write("...✓\n")
            sys.stdout.flush()

        print("\n6. STOPPED sending watchdog messages!")
        print("   Watchdog will trigger in ~1000ms...")

        # Keep motors spinning but DON'T send watchdog messages
        # The watchdog will trigger after 1000ms
        elapsed = 0
        while elapsed < 2.0:  # Wait 2 seconds total
            commander.send_setpoint_rpyt(roll=0.0, pitch=0.0, yaw_rate=0.0, thrust=8000)
            time.sleep(0.1)
            elapsed += 0.1

        print("\n⚠️  Watchdog TRIGGERED! Motors stopped automatically.")
        print("⚠️  Drone is now LOCKED and requires a REBOOT to function again.")
        print("\n✓ Emergency watchdog demonstration complete!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted! Attempting to disarm for safety...")
        try:
            platform.send_arming_request(do_arm=False)
            print("   ✓ Disarmed!")
        except Exception:
            print("   ⚠️  Could not disarm (may already be in emergency state)")

    finally:
        print("\nDisconnecting...")
        cf.disconnect()
        print("Done!")


if __name__ == "__main__":
    main()
