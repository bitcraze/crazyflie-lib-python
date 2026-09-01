# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/\___/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2026 Bitcraze AB
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
import errno
import struct
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import CHAN_SETTINGS
from cflib.crazyflie.log import CMD_DELETE_BLOCK
from cflib.crazyflie.log import CMD_RESET_LOGGING
from cflib.crazyflie.log import Log
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.log import LogConfigError
from cflib.crazyflie.toc import Toc
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.callbacks import Caller


class LogTest(unittest.TestCase):

    def setUp(self):
        self.cf = MagicMock(spec=Crazyflie)
        self.cf.link = object()
        self.cf.disconnected = Caller()
        self.log = Log(self.cf)
        self.cf.log = self.log
        self.log.toc = Toc()

    def _acknowledge(self, command, block_id=0, error_status=0):
        packet = CRTPPacket()
        packet.set_header(CRTPPort.LOGGING, CHAN_SETTINGS)
        packet.data = (command, block_id, error_status)
        self.log._new_packet_cb(packet)

    def _make_config(self, name):
        config = LogConfig(name, 100)
        config.add_memory('value', 'uint8_t', 'uint8_t', 0x1000)
        return config

    def test_all_byte_values_are_available_as_log_config_ids(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)

        configs = [self._make_config('config-{}'.format(i)) for i in range(256)]
        for config in configs:
            self.log.add_config(config)

        self.assertEqual(list(range(256)), [config.id for config in configs])
        with self.assertRaises(LogConfigError):
            self.log.add_config(self._make_config('one-too-many'))

    def test_deleted_id_is_released_after_acknowledgement(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        deleted_config = self._make_config('deleted')
        self.log.add_config(deleted_config)
        deleted_config.delete()
        for i in range(1, 256):
            self.log.add_config(self._make_config('config-{}'.format(i)))

        with self.assertRaises(LogConfigError):
            self.log.add_config(self._make_config('before-ack'))

        self._acknowledge(CMD_DELETE_BLOCK, deleted_config.id)

        self.assertIsNone(deleted_config.id)
        self.assertIsNone(deleted_config.cf)
        self.assertNotIn(deleted_config, self.log.log_blocks)
        self.log.add_config(deleted_config)
        self.assertEqual(0, deleted_config.id)

    def test_delete_is_idempotent_until_a_failed_acknowledgement(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_config('config')
        self.log.add_config(config)
        self.cf.send_packet.reset_mock()

        config.delete()
        config.delete()

        self.assertEqual(1, self.cf.send_packet.call_count)
        self._acknowledge(CMD_DELETE_BLOCK, config.id, errno.ENOMEM)
        self.assertEqual(0, config.id)
        self.assertIn(config, self.log.log_blocks)

        config.delete()
        self.assertEqual(2, self.cf.send_packet.call_count)

    def test_reset_acknowledgement_detaches_configs_and_restores_ids(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_config('old-config')
        self.log.add_config(config)

        self.log.reset()

        self.assertEqual(0, config.id)
        with self.assertRaises(LogConfigError):
            self.log.add_config(self._make_config('during-reset'))

        self._acknowledge(CMD_RESET_LOGGING)

        self.assertIsNone(config.id)
        self.assertIsNone(config.cf)
        self.assertEqual([], self.log.log_blocks)
        new_config = self._make_config('new-config')
        self.log.add_config(new_config)
        self.assertEqual(0, new_config.id)

    def test_disconnect_detaches_configs_without_restoring_ids(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_config('config')
        self.log.add_config(config)

        self.cf.disconnected.call('radio://test')

        self.assertIsNone(config.id)
        self.assertIsNone(config.cf)
        self.assertEqual([], self.log.log_blocks)
        self.cf.link = None
        with self.assertRaises(LogConfigError):
            self.log.add_config(self._make_config('after-disconnect'))

    def test_detached_config_requires_registration_before_start(self):
        config = self._make_config('config')

        config.stop()
        config.delete()
        with self.assertRaises(LogConfigError):
            config.start()

    def test_config_cannot_be_registered_twice(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_config('config')
        self.log.add_config(config)

        with self.assertRaises(LogConfigError):
            self.log.add_config(config)

        other_config = self._make_config('other-config')
        self.log.add_config(other_config)
        self.assertEqual(1, other_config.id)

    def test_untyped_variables_are_resolved_fresh_when_reregistered(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        toc_element = MagicMock()
        toc_element.ctype = 'uint8_t'
        self.log.toc = MagicMock()
        self.log.toc.get_element_by_complete_name.return_value = toc_element
        config = LogConfig('config', 100)
        config.add_variable('group.value')
        self.log.add_config(config)
        config.delete()
        self._acknowledge(CMD_DELETE_BLOCK, config.id)

        toc_element.ctype = 'uint16_t'
        self.log.add_config(config)
        received = []
        config.data_received_cb.add_callback(
            lambda timestamp, data, logconf: received.append(data))

        config.unpack_log_data(struct.pack('<H', 513), 0)

        self.assertEqual([{'group.value': 513}], received)

    def test_delete_of_missing_firmware_block_releases_id(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_config('config')
        self.log.add_config(config)
        config.delete()

        self._acknowledge(CMD_DELETE_BLOCK, config.id, errno.ENOENT)

        self.assertIsNone(config.id)

    def test_duplicate_reset_ack_does_not_detach_new_config(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_config('config')
        self.log.add_config(config)

        self._acknowledge(CMD_RESET_LOGGING)

        self.assertEqual(0, config.id)
        self.assertIn(config, self.log.log_blocks)

    def test_delete_can_be_retried_when_sending_fails(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_config('config')
        self.log.add_config(config)
        self.cf.send_packet.reset_mock()
        self.cf.send_packet.side_effect = [RuntimeError('send failed'), None]

        with self.assertRaises(RuntimeError):
            config.delete()
        config.delete()

        self.assertEqual(2, self.cf.send_packet.call_count)

    def test_reset_can_be_retried_after_failed_acknowledgement(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING, error_status=errno.ENOEXEC)
        self.cf.send_packet.reset_mock()

        self.log.reset()

        self.assertEqual(1, self.cf.send_packet.call_count)

    def test_ids_are_unique_when_configs_are_registered_concurrently(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        configs = [self._make_config('config-{}'.format(i))
                   for i in range(256)]

        with ThreadPoolExecutor(max_workers=16) as executor:
            list(executor.map(self.log.add_config, configs))

        self.assertEqual(list(range(256)), sorted(
            config.id for config in configs))

    def test_reset_waits_for_in_flight_delete_command(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_config('config')
        self.log.add_config(config)
        delete_send_started = threading.Event()
        allow_delete_send = threading.Event()
        reset_finished = threading.Event()

        def send_packet(packet, expected_reply):
            if packet.data[0] == CMD_DELETE_BLOCK:
                delete_send_started.set()
                allow_delete_send.wait()

        self.cf.send_packet.side_effect = send_packet
        delete_thread = threading.Thread(target=config.delete)
        delete_thread.start()
        self.assertTrue(delete_send_started.wait(1.0))

        def reset():
            self.log.reset()
            reset_finished.set()

        reset_thread = threading.Thread(target=reset)
        reset_thread.start()

        try:
            self.assertFalse(reset_finished.wait(0.1))
        finally:
            allow_delete_send.set()
            delete_thread.join(1.0)
            reset_thread.join(1.0)
        self.assertFalse(delete_thread.is_alive())
        self.assertFalse(reset_thread.is_alive())

    def test_reset_can_be_retried_when_sending_fails(self):
        self.cf.send_packet.side_effect = [RuntimeError('send failed'), None]

        with self.assertRaises(RuntimeError):
            self.log.reset()
        self.log.reset()

        self.assertEqual(2, self.cf.send_packet.call_count)


if __name__ == '__main__':
    unittest.main()
