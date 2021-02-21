# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2021 Bitcraze AB
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
import unittest

from cflib.crazyflie.mem import LighthouseBsCalibration
from cflib.crazyflie.mem.lighthouse_memory import LighthouseBsGeometry


class TestLighthouseMemory(unittest.TestCase):
    def test_bs_calibration_file_format(self):
        # Fixture
        calib = LighthouseBsCalibration()
        calib.uid = 1234

        calib.sweeps[0].curve = 1.0
        calib.sweeps[0].phase = 2.0
        calib.sweeps[0].tilt = 3.0
        calib.sweeps[0].gibmag = 4.0
        calib.sweeps[0].gibphase = 5.0
        calib.sweeps[0].ogeemag = 6.0
        calib.sweeps[0].ogeephase = 7.0

        calib.sweeps[1].curve = 8.0

        # Test
        actual = calib.as_file_object()

        # Assert
        self.assertEqual(1234, actual['uid'])
        self.assertEqual(1.0, actual['sweeps'][0]['curve'])
        self.assertEqual(2.0, actual['sweeps'][0]['phase'])
        self.assertEqual(3.0, actual['sweeps'][0]['tilt'])
        self.assertEqual(4.0, actual['sweeps'][0]['gibmag'])
        self.assertEqual(5.0, actual['sweeps'][0]['gibphase'])
        self.assertEqual(6.0, actual['sweeps'][0]['ogeemag'])
        self.assertEqual(7.0, actual['sweeps'][0]['ogeephase'])
        self.assertEqual(8.0, actual['sweeps'][1]['curve'])

    def test_bs_calibration_file_write_read(self):
        # Fixture
        calib = LighthouseBsCalibration()
        calib.uid = 1234

        calib.sweeps[0].curve = 1.0
        calib.sweeps[0].phase = 2.0
        calib.sweeps[0].tilt = 3.0
        calib.sweeps[0].gibmag = 4.0
        calib.sweeps[0].gibphase = 5.0
        calib.sweeps[0].ogeemag = 6.0
        calib.sweeps[0].ogeephase = 7.0

        calib.sweeps[1].curve = 8.0

        file_object = calib.as_file_object()

        # Test
        actual = LighthouseBsCalibration.from_file_object(file_object)

        # Assert
        actual_file_object = actual.as_file_object()
        self.assertEqual(file_object, actual_file_object)
        self.assertTrue(actual.valid)

    def test_bs_geometry_file_format(self):
        # Fixture
        geo = LighthouseBsGeometry()
        geo.origin = [1.0, 2.0, 3.0]
        geo.rotation_matrix = [[1.0, 2.0, 3.0], [1.1, 2.1, 3.1], [1.2, 2.2, 3.2]]

        # Test
        actual = geo.as_file_object()

        # Assert
        self.assertEqual([1.0, 2.0, 3.0], actual['origin'])
        self.assertEqual([[1.0, 2.0, 3.0], [1.1, 2.1, 3.1], [1.2, 2.2, 3.2]], actual['rotation'])

    def test_bs_geometry_file_write_read(self):
        # Fixture
        geo = LighthouseBsGeometry()
        geo.origin = [1.0, 2.0, 3.0]
        geo.rotation_matrix = [[1.0, 2.0, 3.0], [1.1, 2.1, 3.1], [1.2, 2.2, 3.2]]

        file_object = geo.as_file_object()

        # Test
        actual = LighthouseBsGeometry.from_file_object(file_object)

        # Assert
        actual_file_object = actual.as_file_object()
        self.assertEqual(file_object, actual_file_object)
        self.assertTrue(actual.valid)
