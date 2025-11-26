# -*- coding: utf-8 -*-
#
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
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

# URI to the Crazyflie to connect to
URI = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')


class wrgb:
    def __init__(self, w: int, r: int, g: int, b: int):
        self.w = w
        self.r = r
        self.g = g
        self.b = b


class rgb:
    def __init__(self, r: int, g: int, b: int):
        self.w = min(r, g, b)
        self.r = r - self.w
        self.g = g - self.w
        self.b = b - self.w


def pack_wrgb(input: wrgb | rgb) -> int:
    """Pack WRGB values into uint32 format: 0xWWRRGGBB"""
    return (input.w << 24) | (input.r << 16) | (input.g << 8) | input.b


if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        cf = scf.cf

        # Detect which color LED deck is present (bottom or top)
        # We check for whichever deck is attached and use the first one found
        # Check for bottom-facing deck first
        if str(cf.param.get_value('deck.bcColorLedBot')) == '1':
            deck_params = {
                'color': 'colorLedBot.wrgb8888',
                'brightness': 'colorLedBot.brightCorr',
                'throttle': 'colorLedBot.throttlePct',
                'temp': 'colorLedBot.deckTemp'
            }
            print('Detected bottom-facing color LED deck')
        # Check for top-facing deck
        elif str(cf.param.get_value('deck.bcColorLedTop')) == '1':
            deck_params = {
                'color': 'colorLedTop.wrgb8888',
                'brightness': 'colorLedTop.brightCorr',
                'throttle': 'colorLedTop.throttlePct',
                'temp': 'colorLedTop.deckTemp'
            }
            print('Detected top-facing color LED deck')
        else:
            raise RuntimeError('No color LED deck detected!')

        # Thermal status callback
        def thermal_status_callback(timestamp, data, logconf):
            throttle_pct = data[deck_params['throttle']]
            if throttle_pct > 0:
                temp = data[deck_params['temp']]
                print(f'WARNING: Thermal throttling active! Temp: {temp}°C, Throttle: {throttle_pct}%')

        # Setup log configuration for thermal monitoring
        log_conf = LogConfig(name='ThermalStatus', period_in_ms=100)
        log_conf.add_variable(deck_params['temp'], 'uint8_t')
        log_conf.add_variable(deck_params['throttle'], 'uint8_t')

        cf.log.add_config(log_conf)
        log_conf.data_received_cb.add_callback(thermal_status_callback)
        log_conf.start()

        # Brightness correction: balances luminance across R/G/B/W channels
        # Set to 1 (enabled, default) for perceptually uniform colors
        # Set to 0 (disabled) for maximum brightness per channel
        cf.param.set_value(deck_params['brightness'], 1)
        time.sleep(0.1)

        try:
            # ========================================
            # Set your desired color here:
            # ========================================
            # Examples:
            #   color = wrgb(w=0, r=255, g=0, b=0)      # Pure red
            #   color = wrgb(w=0, r=0, g=255, b=0)      # Pure green
            #   color = wrgb(w=0, r=0, g=0, b=255)      # Pure blue
            #   color = wrgb(w=255, r=0, g=0, b=0)      # Pure white LED
            #   color = wrgb(w=50, r=255, g=128, b=0)   # Orange + white
            #   color = rgb(r=255, g=255, b=255)        # White (auto W extraction)

            color = wrgb(w=0, r=255, g=0, b=100)
            # ========================================

            color_uint32 = pack_wrgb(color)
            cf.param.set_value(deck_params['color'], color_uint32)
            time.sleep(0.01)
            print(f'Setting LED to R={color.r}, G={color.g}, B={color.b}, W={color.w}')
            print('Press Ctrl-C to turn off LED and exit.')
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print('\nStopping and turning off LED...')
            cf.param.set_value(deck_params['color'], 0)
            time.sleep(0.1)
