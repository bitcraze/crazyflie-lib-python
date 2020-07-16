# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2018 Bitcraze AB
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
"""
This script implements a simple matrix light printer to be used with a
camera with open shutter in a dark room.

It requires a Crazyflie capable of controlling its position and with
a Led ring attached to it. A piece of sticky paper can be attached on
the led ring to orient the ring light toward the front.

To control it position, Crazyflie requires an absolute positioning
system such as the Lighthouse.
"""
import time

import matplotlib.pyplot as plt

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.position_hl_commander import PositionHlCommander

# URI to the Crazyflie to connect to
uri = 'radio://0/80'


class ImageDef:
    def __init__(self, file_name):
        self._image = plt.imread(file_name)

        self.x_pixels = self._image.shape[1]
        self.y_pixels = self._image.shape[0]

        width = 1.0
        height = self.y_pixels * width / self.x_pixels

        self.x_start = -width / 2.0 + 0.5
        self.y_start = 0.7

        self.x_step = width / self.x_pixels
        self.y_step = height / self.y_pixels

    def get_color(self, x_index, y_index):
        rgba = self._image[self.y_pixels - y_index - 1, x_index]
        rgb = [int(rgba[0] * 90), int(rgba[1] * 90), int(rgba[2] * 90)]
        return rgb


BLACK = [0, 0, 0]


def set_led_ring_solid(cf, rgb):
    cf.param.set_value('ring.effect', 7)
    print(rgb[0], rgb[1], rgb[2])
    cf.param.set_value('ring.solidRed', rgb[0])
    cf.param.set_value('ring.solidGreen', rgb[1])
    cf.param.set_value('ring.solidBlue', rgb[2])


def matrix_print(cf, pc, image_def):
    set_led_ring_solid(cf, BLACK)
    time.sleep(3)

    for y_index in range(image_def.y_pixels):
        y = image_def.y_start + image_def.y_step * y_index

        pc.go_to(0, image_def.x_start - 0.1, y)
        time.sleep(1.0)

        scan_range = range(image_def.x_pixels)

        for x_index in scan_range:
            x = image_def.x_start + image_def.x_step * x_index

            color = image_def.get_color(x_index, y_index)

            print(x, y, color)

            pc.go_to(0, x, y)
            set_led_ring_solid(cf, color)

        set_led_ring_solid(cf, BLACK)

        print('---')


if __name__ == '__main__':
    cflib.crtp.init_drivers(enable_debug_driver=False)

    image_def = ImageDef('monalisa.png')

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        with PositionHlCommander(scf, default_height=0.5) as pc:
            matrix_print(scf.cf, pc, image_def)
