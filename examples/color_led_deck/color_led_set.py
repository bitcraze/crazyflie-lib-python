import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

# URI to the Crazyflie to connect to
URI = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')


class rgbw:
    def __init__(self, r: int, g: int, b: int, w: int = 0):
        self.r = r
        self.g = g
        self.b = b
        self.w = w


class rgb:
    def __init__(self, r: int, g: int, b: int):
        self.w = min(r, g, b)
        self.r = r - self.w
        self.g = g - self.w
        self.b = b - self.w


def pack_rgbw(input: rgbw | rgb) -> int:
    """Pack RGBW values into uint32 format: 0xWWRRGGBB"""
    return (input.w << 24) | (input.r << 16) | (input.g << 8) | input.b


if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        cf = scf.cf

        # Thermal status callback
        def thermal_status_callback(timestamp, data, logconf):
            throttle_pct = data['colorled.throttlePct']
            if throttle_pct > 0:
                temp = data['colorled.deckTemp']
                print(f'WARNING: Thermal throttling active! Temp: {temp}°C, Throttle: {throttle_pct}%')

        # Setup log configuration for thermal monitoring
        log_conf = LogConfig(name='ThermalStatus', period_in_ms=100)
        log_conf.add_variable('colorled.deckTemp', 'uint8_t')
        log_conf.add_variable('colorled.throttlePct', 'uint8_t')

        cf.log.add_config(log_conf)
        log_conf.data_received_cb.add_callback(thermal_status_callback)
        log_conf.start()

        # Brightness correction: balances luminance across R/G/B/W channels
        # Set to 1 (enabled, default) for perceptually uniform colors
        # Set to 0 (disabled) for maximum brightness per channel
        cf.param.set_value('colorled.brightnessCorr', 1)
        time.sleep(0.1)

        try:
            # ========================================
            # Set your desired color here:
            # ========================================
            # Examples:
            #   color = rgbw(r=255, g=0, b=0, w=0)      # Pure red
            #   color = rgbw(r=0, g=255, b=0, w=0)      # Pure green
            #   color = rgbw(r=0, g=0, b=255, w=0)      # Pure blue
            #   color = rgbw(r=0, g=0, b=0, w=255)      # Pure white LED
            #   color = rgbw(r=255, g=128, b=0, w=50)   # Orange + white
            #   color = rgb(r=255, g=255, b=255)        # White (auto W extraction)

            color = rgbw(r=255, g=0, b=100, w=0)
            # ========================================

            color_uint32 = pack_rgbw(color)
            cf.param.set_value('colorled.rgbw8888', color_uint32)
            time.sleep(0.01)
            print(f'Setting LED to R={color.r}, G={color.g}, B={color.b}, W={color.w}')
            print('Press Ctrl-C to turn off LED and exit.')
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print('\nStopping and turning off LED...')
            cf.param.set_value('colorled.rgbw8888', 0)
            time.sleep(0.1)
