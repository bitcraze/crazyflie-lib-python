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

from cflib.crtp import RadioDriver
from cflib.drivers.crazyradio import Crazyradio


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
        def send_packets(uris, value, description):
            for uri in uris:
                devid, channel, datarate, address = RadioDriver.parse_uri(uri)
                radio.set_channel(channel)
                radio.set_data_rate(datarate)
                radio.set_address(address)

                received_packet = False
                for i in range(10):
                    result = radio.send_packet((0xf3, 0xfe, value))
                    if result.ack is True:
                        received_packet = True
                        # if i > 0:
                        #     print('Lost packets', i, uri)
                        break

                if not received_packet:
                    raise Exception('Failed to turn device {}, for {}'.
                                    format(description, uri))

        print('Restarting devices')

        BOOTLOADER_CMD_SYSOFF = 0x02
        BOOTLOADER_CMD_SYSON = 0x03

        radio = Crazyradio()
        send_packets(uris, BOOTLOADER_CMD_SYSOFF, 'off')
        send_packets(uris, BOOTLOADER_CMD_SYSON, 'on')

        # Wait for devices to boot
        time.sleep(8)
        radio.close()
