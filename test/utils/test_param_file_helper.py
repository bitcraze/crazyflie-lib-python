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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
import unittest
from threading import Event
from unittest.mock import MagicMock
from unittest.mock import patch

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils.param_file_helper import ParamFileHelper


class ParamFileHelperTests(unittest.TestCase):

    def setUp(self):
        self.cf_mock = MagicMock(spec=Crazyflie)
        self.helper = ParamFileHelper(self.cf_mock)

    def test_ParamFileHelper_SyncCrazyflieAsParam_ThrowsException(self):
        cf_mock = MagicMock(spec=SyncCrazyflie)
        helper = None
        try:
            helper = ParamFileHelper(cf_mock)
        except Exception:
            self.assertIsNone(helper)
        else:
            self.fail('Expect exception')

    def test_ParamFileHelper_Crazyflie_Object(self):
        helper = ParamFileHelper(self.cf_mock)
        self.assertIsNotNone(helper)

    @patch('cflib.crazyflie.Param')
    def test_ParamFileHelper_writesAndStoresParamFromFileToCrazyflie(self, mock_Param):
        # Setup
        cf_mock = MagicMock(spec=Crazyflie)
        cf_mock.param = mock_Param
        helper = ParamFileHelper(cf_mock)
        # Mock blocking wait and call callback instead. This lets the flow work as it would in the asynch world

        def mock_wait(self, timeout=None):
            helper._persistent_stored_callback('activeMarker.back', True)
            return

        with patch.object(Event, 'wait', new=mock_wait):
            self.assertTrue(helper.store_params_from_file('test/utils/fixtures/single_param.yaml'))
            mock_Param.set_value.assert_called_once_with('activeMarker.back', 10)
            mock_Param.persistent_store.assert_called_once_with('activeMarker.back', helper._persistent_stored_callback)

    @patch('cflib.crazyflie.Param')
    def test_ParamFileHelper_writesParamAndFailsToSetPersistantShouldReturnFalse(self, mock_Param):
        # Setup
        cf_mock = MagicMock(spec=Crazyflie)
        cf_mock.param = mock_Param
        helper = ParamFileHelper(cf_mock)
        # Mock blocking wait and call callback instead. This lets the flow work as it would in the asynch world

        def mock_wait(self, timeout=None):
            helper._persistent_stored_callback('activeMarker.back', False)
            return

        with patch.object(Event, 'wait', new=mock_wait):
            self.assertFalse(helper.store_params_from_file('test/utils/fixtures/single_param.yaml'))
            mock_Param.set_value.assert_called_once_with('activeMarker.back', 10)
            mock_Param.persistent_store.assert_called_once_with('activeMarker.back', helper._persistent_stored_callback)

    @patch('cflib.crazyflie.Param')
    def test_ParamFileHelper_TryWriteSeveralParamsPersistantShouldBreakAndReturnFalse(self, mock_Param):
        # Setup
        cf_mock = MagicMock(spec=Crazyflie)
        cf_mock.param = mock_Param
        helper = ParamFileHelper(cf_mock)
        # Mock blocking wait and call callback instead. This lets the flow work as it would in the asynch world

        def mock_wait(self, timeout=None):
            helper._persistent_stored_callback('activeMarker.back', False)
            return

        with patch.object(Event, 'wait', new=mock_wait):
            # Test and assert
            self.assertFalse(helper.store_params_from_file('test/utils/fixtures/five_params.yaml'))
            # Assert it breaks directly by checking number of calls
            mock_Param.set_value.assert_called_once_with('activeMarker.back', 10)
            mock_Param.persistent_store.assert_called_once_with('activeMarker.back', helper._persistent_stored_callback)

    @patch('cflib.crazyflie.Param')
    def test_ParamFileHelper_writesAndStoresAllParamsFromFileToCrazyflie(self, mock_Param):
        # Setup
        cf_mock = MagicMock(spec=Crazyflie)
        cf_mock.param = mock_Param
        helper = ParamFileHelper(cf_mock)
        # Mock blocking wait and call callback instead. This lets the flow work as it would in the asynch world

        def mock_wait(self, timeout=None):
            helper._persistent_stored_callback('something', True)
            return
        with patch.object(Event, 'wait', new=mock_wait):
            # Test and  Assert
            self.assertTrue(helper.store_params_from_file('test/utils/fixtures/five_params.yaml'))
            self.assertEquals(5, len(mock_Param.set_value.mock_calls))
            self.assertEquals(5, len(mock_Param.persistent_store.mock_calls))
