# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2021 Bitcraze AB
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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
import unittest

import cflib.crtp
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils import uri_helper


class TestSingleCfGrounded(unittest.TestCase):
    def setUp(self):
        cflib.crtp.init_drivers()
        self.radioUri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')
        self.usbUri = 'usb://0'

    def is_stm_connected(self):
        link = cflib.crtp.get_link_driver(self.radioUri)

        pk = CRTPPacket()
        pk.set_header(CRTPPort.LINKCTRL, 0)  # Echo channel
        pk.data = b'test'
        link.send_packet(pk)
        for _ in range(10):
            pk_ack = link.receive_packet(0.1)
            print(pk_ack)
            if pk_ack is not None and pk.data == pk_ack.data:
                link.close()
                return True
        link.close()
        return False
        # print(pk_ack)
        # return pk_ack is not None
