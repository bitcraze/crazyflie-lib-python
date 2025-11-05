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


class hsv:
    def __init__(self, h: int, s: int, v: int):
        self.h = h
        self.s = s
        self.v = v


def hsv_to_wrgb(input: hsv) -> wrgb:
    h, s, v = input.h, input.s / 255.0, input.v / 255.0

    if s == 0:
        r = g = b = v
    else:
        h = h / 60.0
        i = int(h)
        f = h - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))

        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q

    return wrgb(0, int(r * 255), int(g * 255), int(b * 255))


def cycle_colors(step: int) -> wrgb:
    h = step % 360
    s = 255
    v = 255
    return hsv_to_wrgb(hsv(h, s, v))


def pack_wrgb(input: wrgb) -> int:
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

        # Brightness correction: balances luminance across W/R/G/B channels
        # Set to 1 (enabled, default) for perceptually uniform colors
        # Set to 0 (disabled) for maximum brightness per channel
        cf.param.set_value(deck_params['brightness'], 1)
        time.sleep(0.1)

        try:
            print('Cycling through colors. Press Ctrl-C to stop.')
            while True:
                for i in range(0, 360, 1):
                    color: wrgb = cycle_colors(i)
                    # print(color.r, color.g, color.b)
                    color_uint32 = pack_wrgb(color)
                    cf.param.set_value(deck_params['color'], str(color_uint32))
                    time.sleep(0.01)
        except KeyboardInterrupt:
            print('\nStopping and turning off LED...')
            cf.param.set_value(deck_params['color'], '0')
            time.sleep(0.1)
