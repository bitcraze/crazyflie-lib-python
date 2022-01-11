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
import time
import unittest

from single_cf_grounded import TestSingleCfGrounded

from cflib.bootloader import Bootloader
from cflib.bootloader.boottypes import BootVersion


class TestBootloader(TestSingleCfGrounded):

    def test_boot_to_bootloader(self):
        self.assertTrue(self.is_stm_connected())
        bl = Bootloader(self.radioUri)
        started = bl.start_bootloader(warm_boot=True)
        self.assertTrue(started)

        # t = bl.get_target(TargetTypes.NRF51)
        # print(t)

        bl.reset_to_firmware()
        bl.close()
        time.sleep(1)
        self.assertTrue(self.is_stm_connected())
        self.assertTrue(BootVersion.is_cf2(bl.protocol_version))


if __name__ == '__main__':
    unittest.main()
