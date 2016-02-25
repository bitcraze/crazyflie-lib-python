import sys

from cflib import crtp


def get_available_crazyflies():
    # Initialize the low-level drivers (don't list the debug drivers)
    crtp.init_drivers(enable_debug_driver=False)

    print('Scanning for Crazyflies...')
    available = crtp.scan_interfaces()

    if not available:
        sys.exit(
            'No Crazyflies found, cannot run example. Have you turned it on?'
        )

    print('Crazyflies found:')
    for crazyflie in available:
        print(crazyflie[0])

    return available


def get_first_crazyflie():
    return get_available_crazyflies()[0][0]
