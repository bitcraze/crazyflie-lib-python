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
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper

# URI to the Crazyflie to connect to
URI = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')


class rgb:
    def __init__(self, r: int, g: int, b: int):
        self.r = r
        self.g = g
        self.b = b


class hsv:
    def __init__(self, h: int, s: int, v: int):
        self.h = h
        self.s = s
        self.v = v


def hsv_to_rgb(input: hsv) -> rgb:
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

    return rgb(int(r * 255), int(g * 255), int(b * 255))


def cycle_colors(step: int) -> rgb:
    h = step % 360
    s = 255
    v = 255
    return hsv_to_rgb(hsv(h, s, v))


def construct_uint32_color(input: rgb) -> int:
    return (input.r << 16) | (input.g << 8) | input.b


if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        cf = scf.cf

        try:
            print('Cycling through colors. Press Ctrl-C to stop.')
            while True:
                for i in range(0, 360, 1):
                    color = cycle_colors(i)
                    color_uint32 = construct_uint32_color(color)
                    cf.param.set_value('led_deck_ctrl.rgb888', str(color_uint32))
                    time.sleep(0.01)
        except KeyboardInterrupt:
            print('\nStopping and turning off LED...')
            cf.param.set_value('led_deck_ctrl.rgb888', '0')
            time.sleep(0.1)
