"""
Example demonstrating the Rust-powered Crazyflie library.

This example shows the new clean API with full Rust implementation.

Usage:
    python examples/rust_example.py
"""
# from cflib._rust import LinkContext
from cflib.crazyflie import Crazyflie


def main():
    """Main example function."""

    # print("Scanning for Crazyflies...")
    # ctx = LinkContext()
    # uris = ctx.scan()

    # if not uris:
    #     print("No Crazyflies found!")
    #     print("Make sure a Crazyflie is turned on and in range.")
    #     return

    # print(f"Found {len(uris)} Crazyflie(s):")
    # for uri in uris:
    #     print(f"  - {uri}")
    # print()

    # Connect to the first one using context manager
    # uri = uris[0]
    uri = 'radio://0/60/2M/F00D2BEFED'  # Change to your Crazyflie URI
    print(f"Connecting to {uri}...")

    try:
        with Crazyflie(uri) as cf:
            print('Connected!')
            print()

            # Get platform info
            print('Platform information:')
            print(f"  Protocol version: {cf.platform.get_protocol_version()}")
            print(f"  Firmware version: {cf.platform.get_firmware_version()}")
            print(f"  Device type: {cf.platform.get_device_type_name()}")
            print()

            # List some parameters
            print('Available parameters (first 10):')
            param_names = cf.param.names()[:10]
            for name in param_names:
                try:
                    value = cf.param.get(name)
                    print(f"  {name} = {value}")
                except Exception as e:
                    print(f"  {name} = <error: {e}>")
            print()

            # Send a stop command to make sure the drone is not flying
            print('Sending stop command...')
            cf.commander.send_stop_setpoint()

            # Demonstrate sending setpoints (BE CAREFUL - this can make the drone fly!)
            # Uncomment only if you know what you're doing
            # print("Sending test setpoints (thrust=0, safe)...")
            # import time
            # for i in range(10):
            #     cf.commander.send_setpoint(0.0, 0.0, 0.0, 0)
            #     time.sleep(0.01)

            print()
            print('Disconnecting...')
            # Auto-disconnects when exiting 'with' block

        print('Done!')

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
