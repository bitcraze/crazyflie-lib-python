# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2019 Bitcraze AB
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
import time

from cflib.utils.power_switch import PowerSwitch


class RigSupport:
    def __init__(self):
        self.all_uris = [
            'radio://0/42/2M/E7E7E74201',
            'radio://0/42/2M/E7E7E74202',
            'radio://0/42/2M/E7E7E74203',
            'radio://0/42/2M/E7E7E74204',
            'radio://0/42/2M/E7E7E74205',
            'radio://0/42/2M/E7E7E74206',
            'radio://0/42/2M/E7E7E74207',
            'radio://0/42/2M/E7E7E74208',
            'radio://0/42/2M/E7E7E74209',
            'radio://0/42/2M/E7E7E7420A',
        ]

    def restart_devices(self, uris):
        print('Restarting devices')

        for uri in uris:
            PowerSwitch(uri).stm_power_down()

        time.sleep(1)

        for uri in uris:
            PowerSwitch(uri).stm_power_up()

        # Wait for devices to boot
        time.sleep(8)
