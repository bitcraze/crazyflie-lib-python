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
from cflib.crazyflie.log import CHAN_LOGDATA
from cflib.crazyflie.log import CHAN_SETTINGS
from cflib.crazyflie.log import CMD_CREATE_BLOCK
from cflib.crazyflie.log import CMD_CREATE_BLOCK_V2
from cflib.crazyflie.log import CMD_DELETE_BLOCK
from cflib.crazyflie.log import CMD_RESET_LOGGING
from cflib.crazyflie.log import CMD_START_LOGGING
from cflib.crazyflie.log import CMD_STOP_LOGGING
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

    def _make_toc_config(self, name):
        self.log.toc = MagicMock()
        self.log.toc.get_element_by_complete_name.return_value = MagicMock()
        self.log.toc.get_element_id.return_value = 1
        config = LogConfig(name, 100)
        config.add_variable('group.value', 'uint8_t')
        return config

    def _make_multi_packet_config(self):
        self.log._useV2 = True
        self.log.toc = MagicMock()
        self.log.toc.get_element_by_complete_name.return_value = MagicMock()
        self.log.toc.get_element_id.return_value = 1
        config = LogConfig('multi-packet', 100)
        for i in range(20):
            config.add_variable('group.value{}'.format(i), 'uint8_t')
        self.log.add_config(config)
        return config

    def _add_thread_cleanup(self, thread, unblock_event):
        self.addCleanup(thread.join, 1.0)
        self.addCleanup(unblock_event.set)

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

    def test_300_create_start_stop_delete_cycles(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)

        for i in range(300):
            config = self._make_toc_config('config-{}'.format(i))
            self.log.add_config(config)
            received = []
            config.data_received_cb.add_callback(
                lambda timestamp, data, logconf: received.append(data))
            config.start()
            self._acknowledge(CMD_CREATE_BLOCK, config.id)
            self._acknowledge(CMD_START_LOGGING, config.id)

            packet = CRTPPacket()
            packet.set_header(CRTPPort.LOGGING, CHAN_LOGDATA)
            packet.data = (config.id, 0, 0, 0, i % 256)
            self.log._new_packet_cb(packet)

            config.stop()
            self._acknowledge(CMD_STOP_LOGGING, config.id)
            config.delete()
            self._acknowledge(CMD_DELETE_BLOCK, config.id)

            self.assertEqual([{'group.value': i % 256}], received)
            self.assertIsNone(config.id)
            self.assertEqual([], self.log.log_blocks)

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

    def test_refresh_during_untyped_validation_fails_cleanly(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        toc = MagicMock()
        toc_element = MagicMock()
        toc_element.ctype = 'uint8_t'
        refresh_started = False

        def get_element(name):
            nonlocal refresh_started
            if not refresh_started:
                refresh_started = True
                self.cf.platform = MagicMock()
                self.cf.platform.get_protocol_version.return_value = 4
                self.log.refresh_toc(None, None)
            return toc_element

        toc.get_element_by_complete_name.side_effect = get_element
        self.log.toc = toc
        config = LogConfig('config', 100)
        config.add_variable('group.value')

        with self.assertRaises(LogConfigError):
            self.log.add_config(config)

        self.assertIsNone(config.id)
        self.assertIsNone(config.cf)

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
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_config('config')
        self.log.add_config(config)

        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING, error_status=errno.ENOEXEC)
        self.cf.send_packet.reset_mock()

        self.assertTrue(self.log._is_current_registration(
            config, self.cf, config.id))
        other_config = self._make_config('other-config')
        self.log.add_config(other_config)
        self.assertEqual(1, other_config.id)

        self.log.reset()

        self.assertEqual(1, self.cf.send_packet.call_count)

    def test_delete_ack_during_failed_reset_releases_id(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_config('config')
        self.log.add_config(config)
        config.delete()
        block_id = config.id
        self.log.reset()

        self._acknowledge(CMD_DELETE_BLOCK, block_id)
        self._acknowledge(CMD_RESET_LOGGING, error_status=errno.ENOEXEC)

        self.assertIsNone(config.id)
        configs = [self._make_config('config-{}'.format(i))
                   for i in range(Log.MAX_CONFIG_IDS)]
        for new_config in configs:
            self.log.add_config(new_config)
        self.assertEqual(set(range(Log.MAX_CONFIG_IDS)), {
            new_config.id for new_config in configs})

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
        self._add_thread_cleanup(delete_thread, allow_delete_send)
        self.assertTrue(delete_send_started.wait(1.0))

        def reset():
            self.log.reset()
            reset_finished.set()

        reset_thread = threading.Thread(target=reset)
        reset_thread.start()
        self._add_thread_cleanup(reset_thread, allow_delete_send)

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

    def test_failed_reset_send_restores_config_id_state(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_config('config')
        self.log.add_config(config)
        self.cf.send_packet.side_effect = RuntimeError('send failed')

        with self.assertRaises(RuntimeError):
            self.log.reset()

        self.assertTrue(self.log._is_current_registration(
            config, self.cf, config.id))
        other_config = self._make_config('other-config')
        self.log.add_config(other_config)
        self.assertEqual(1, other_config.id)

    def test_reset_waits_for_in_flight_start_command(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        self.log.toc = MagicMock()
        self.log.toc.get_element_by_complete_name.return_value = MagicMock()
        self.log.toc.get_element_id.return_value = 1
        config = LogConfig('config', 100)
        config.add_variable('group.value', 'uint8_t')
        self.log.add_config(config)
        create_send_started = threading.Event()
        allow_create_send = threading.Event()
        reset_finished = threading.Event()

        def send_packet(packet, expected_reply):
            if packet.data[0] == CMD_CREATE_BLOCK:
                create_send_started.set()
                allow_create_send.wait()

        def reset():
            self.log.reset()
            reset_finished.set()

        self.cf.send_packet.side_effect = send_packet
        start_thread = threading.Thread(target=config.start)
        start_thread.start()
        self._add_thread_cleanup(start_thread, allow_create_send)
        self.assertTrue(create_send_started.wait(1.0))
        reset_thread = threading.Thread(target=reset)
        reset_thread.start()
        self._add_thread_cleanup(reset_thread, allow_create_send)

        try:
            self.assertFalse(reset_finished.wait(0.1))
        finally:
            allow_create_send.set()
            start_thread.join(1.0)
            reset_thread.join(1.0)
        self.assertFalse(start_thread.is_alive())
        self.assertFalse(reset_thread.is_alive())

    def test_reset_waits_for_create_acknowledgement_follow_up(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_toc_config('config')
        self.log.add_config(config)
        config.start()
        start_send_started = threading.Event()
        allow_start_send = threading.Event()
        reset_finished = threading.Event()

        def send_packet(packet, expected_reply):
            if packet.data[0] == CMD_START_LOGGING:
                start_send_started.set()
                allow_start_send.wait()

        def acknowledge_create():
            self._acknowledge(CMD_CREATE_BLOCK, config.id)

        def reset():
            self.log.reset()
            reset_finished.set()

        self.cf.send_packet.side_effect = send_packet
        acknowledge_thread = threading.Thread(target=acknowledge_create)
        acknowledge_thread.start()
        self._add_thread_cleanup(acknowledge_thread, allow_start_send)
        self.assertTrue(start_send_started.wait(1.0))
        reset_thread = threading.Thread(target=reset)
        reset_thread.start()
        self._add_thread_cleanup(reset_thread, allow_start_send)

        try:
            self.assertFalse(reset_finished.wait(0.1))
        finally:
            allow_start_send.set()
            acknowledge_thread.join(1.0)
            reset_thread.join(1.0)
        self.assertFalse(acknowledge_thread.is_alive())
        self.assertFalse(reset_thread.is_alive())

    def test_create_acknowledgement_is_ignored_during_reset(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_toc_config('config')
        self.log.add_config(config)
        self.cf.send_packet.reset_mock()
        config.start()
        self.log.reset()

        self._acknowledge(CMD_CREATE_BLOCK, config.id)

        self.assertEqual(
            [CMD_CREATE_BLOCK, CMD_RESET_LOGGING],
            [call.args[0].data[0]
             for call in self.cf.send_packet.call_args_list])
        self.assertFalse(config.added)

    def test_start_is_rejected_while_delete_is_pending(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_config('config')
        self.log.add_config(config)
        config.delete()

        with self.assertRaises(LogConfigError):
            config.start()

        self.assertEqual(2, self.cf.send_packet.call_count)

    def test_disconnect_waits_for_in_flight_start_command(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        self.log.toc = MagicMock()
        self.log.toc.get_element_by_complete_name.return_value = MagicMock()
        self.log.toc.get_element_id.return_value = 1
        config = LogConfig('config', 100)
        config.add_variable('group.value', 'uint8_t')
        self.log.add_config(config)
        create_send_started = threading.Event()
        allow_create_send = threading.Event()
        disconnect_finished = threading.Event()

        def send_packet(packet, expected_reply):
            if packet.data[0] == CMD_CREATE_BLOCK:
                create_send_started.set()
                allow_create_send.wait()

        def disconnect():
            self.cf.disconnected.call('radio://test')
            disconnect_finished.set()

        self.cf.send_packet.side_effect = send_packet
        start_thread = threading.Thread(target=config.start)
        start_thread.start()
        self._add_thread_cleanup(start_thread, allow_create_send)
        self.assertTrue(create_send_started.wait(1.0))
        disconnect_thread = threading.Thread(target=disconnect)
        disconnect_thread.start()
        self._add_thread_cleanup(disconnect_thread, allow_create_send)

        try:
            self.assertFalse(disconnect_finished.wait(0.1))
        finally:
            allow_create_send.set()
            start_thread.join(1.0)
            disconnect_thread.join(1.0)
        self.assertFalse(start_thread.is_alive())
        self.assertFalse(disconnect_thread.is_alive())
        self.assertIsNone(config.id)

    def test_synchronous_disconnect_during_start_does_not_deadlock(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        self.log.toc = MagicMock()
        self.log.toc.get_element_by_complete_name.return_value = MagicMock()
        self.log.toc.get_element_id.return_value = 1
        config = LogConfig('config', 100)
        config.add_variable('group.value', 'uint8_t')
        self.log.add_config(config)
        errors = []

        def send_packet(packet, expected_reply):
            self.cf.disconnected.call('radio://test')

        def start():
            try:
                config.start()
            except LogConfigError as error:
                errors.append(error)

        self.cf.send_packet.side_effect = send_packet
        start_thread = threading.Thread(target=start, daemon=True)
        start_thread.start()
        start_thread.join(1.0)

        self.assertFalse(start_thread.is_alive())
        self.assertEqual(1, len(errors))
        self.assertIsNone(config.id)

    def test_disconnect_during_create_acknowledgement_does_not_revive_config(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_toc_config('config')
        self.log.add_config(config)
        config.start()

        def send_packet(packet, expected_reply):
            if packet.data[0] == CMD_START_LOGGING:
                self.cf.disconnected.call('radio://test')

        self.cf.send_packet.side_effect = send_packet

        self._acknowledge(CMD_CREATE_BLOCK, config.id)

        self.assertIsNone(config.id)
        self.assertFalse(config.added)

    def test_added_callback_cannot_revive_disconnected_config(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_toc_config('config')
        self.log.add_config(config)
        config.start()
        added_states = []

        def added_callback(log_config, added):
            added_states.append(added)
            if added:
                self.cf.disconnected.call('radio://test')

        config.added_cb.add_callback(added_callback)

        self._acknowledge(CMD_CREATE_BLOCK, config.id)

        self.assertEqual([True, False], added_states)
        self.assertIsNone(config.id)
        self.assertFalse(config.added)

    def test_added_callbacks_are_ordered_without_holding_command_lock(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_toc_config('config')
        self.log.add_config(config)
        config.start()
        added_states = []
        states_before_callback_returns = []
        disconnect_completed = []

        def added_callback(log_config, added):
            added_states.append(added)
            if added:
                disconnect_thread = threading.Thread(
                    target=lambda: self.cf.disconnected.call('radio://test'))
                disconnect_thread.start()
                self.addCleanup(disconnect_thread.join, 1.0)
                disconnect_thread.join(1.0)
                disconnect_completed.append(
                    not disconnect_thread.is_alive())
                states_before_callback_returns.append(list(added_states))

        config.added_cb.add_callback(added_callback)

        self._acknowledge(CMD_CREATE_BLOCK, config.id)

        self.assertEqual([True], disconnect_completed)
        self.assertEqual([[True]], states_before_callback_returns)
        self.assertEqual([True, False], added_states)

    def test_callback_failure_does_not_strand_lifecycle_notifications(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_toc_config('config')
        self.log.add_config(config)
        config.start()
        added_states = []

        def added_callback(log_config, added):
            added_states.append(added)
            if added:
                disconnect_thread = threading.Thread(
                    target=lambda: self.cf.disconnected.call('radio://test'))
                disconnect_thread.start()
                self.addCleanup(disconnect_thread.join, 1.0)
                disconnect_thread.join(1.0)
                raise RuntimeError('callback failed')

        config.added_cb.add_callback(added_callback)

        with self.assertRaisesRegex(RuntimeError, 'callback failed'):
            self._acknowledge(CMD_CREATE_BLOCK, config.id)

        self.assertEqual([True, False], added_states)
        self.assertIsNone(config.id)

    def test_synchronous_reset_during_create_prevents_append(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_multi_packet_config()
        sent_commands = []

        def send_packet(packet, expected_reply):
            sent_commands.append(packet.data[0])
            if packet.data[0] == CMD_CREATE_BLOCK_V2:
                self.log.reset()

        self.cf.send_packet.side_effect = send_packet

        with self.assertRaises(LogConfigError):
            config.start()

        self.assertEqual(
            [CMD_CREATE_BLOCK_V2, CMD_RESET_LOGGING], sent_commands)

    def test_synchronous_delete_during_create_prevents_append(self):
        self.log.reset()
        self._acknowledge(CMD_RESET_LOGGING)
        config = self._make_multi_packet_config()
        sent_commands = []

        def send_packet(packet, expected_reply):
            sent_commands.append(packet.data[0])
            if packet.data[0] == CMD_CREATE_BLOCK_V2:
                config.delete()

        self.cf.send_packet.side_effect = send_packet

        with self.assertRaises(LogConfigError):
            config.start()

        self.assertEqual(
            [CMD_CREATE_BLOCK_V2, CMD_DELETE_BLOCK], sent_commands)


if __name__ == '__main__':
    unittest.main()
