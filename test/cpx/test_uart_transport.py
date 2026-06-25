# -*- coding: utf-8 -*-
import threading
import time
import types
import unittest

from cflib.cpx import CPXFunction
from cflib.cpx import CPXPacket
from cflib.cpx import CPXTarget
from cflib.cpx import transports
from cflib.cpx.transports import UARTTransport


class FakeSerial:
    def __init__(self, initial_read_data=b''):
        self._read_data = bytearray(initial_read_data)
        self._condition = threading.Condition()
        self.writes = []
        self.closed = False

    def append_read_data(self, data):
        with self._condition:
            self._read_data.extend(data)
            self._condition.notify_all()

    def read(self, size):
        with self._condition:
            end_time = time.monotonic() + 1.0
            while len(self._read_data) < size:
                remaining = end_time - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Timed out waiting for fake serial data')
                self._condition.wait(remaining)

            result = self._read_data[:size]
            del self._read_data[:size]
            return bytes(result)

    def write(self, data):
        self.writes.append(bytes(data))
        return len(data)

    def close(self):
        self.closed = True


def checksum(data):
    result = 0
    for byte in data:
        result ^= byte
    return result


def uart_frame(packet):
    data = packet.wireData
    frame = bytearray([0xFF, len(data)])
    frame.extend(data)
    frame.append(checksum(frame))
    return bytes(frame)


class UARTTransportTest(unittest.TestCase):
    def setUp(self):
        self.fake_serial = FakeSerial(b'\xff\x00')
        self.original_serial = getattr(transports, 'serial', None)
        transports.serial = types.SimpleNamespace(
            Serial=lambda device, baudrate, timeout=None: self.fake_serial
        )

    def tearDown(self):
        if self.original_serial is None:
            del transports.serial
        else:
            transports.serial = self.original_serial

    def _transport(self):
        return UARTTransport('/dev/fake', 576000)

    def _inbound_packet(self, data=b'payload'):
        return CPXPacket(
            source=CPXTarget.STM32,
            destination=CPXTarget.HOST,
            function=CPXFunction.CRTP,
            data=bytearray(data),
        )

    def test_unsolicited_cts_frames_are_ignored_until_data_packet(self):
        transport = self._transport()
        expected = self._inbound_packet(b'abc')

        self.fake_serial.append_read_data(b'\xff\x00')
        self.fake_serial.append_read_data(b'\xff\x00')
        self.fake_serial.append_read_data(uart_frame(expected))

        actual = transport.readPacket()

        self.assertEqual(expected.wireData, actual.wireData)
        self.assertEqual([b'\xff\x00', b'\xff\x00'], self.fake_serial.writes)

    def test_crc_error_is_discarded_and_next_valid_packet_is_returned(self):
        transport = self._transport()
        bad_packet = self._inbound_packet(b'bad')
        bad_frame = bytearray(uart_frame(bad_packet))
        bad_frame[-1] ^= 0x01
        expected = self._inbound_packet(b'good')

        self.fake_serial.append_read_data(bytes(bad_frame))
        self.fake_serial.append_read_data(uart_frame(expected))

        actual = transport.readPacket()

        self.assertEqual(expected.wireData, actual.wireData)
        self.assertEqual([b'\xff\x00', b'\xff\x00', b'\xff\x00'], self.fake_serial.writes)


if __name__ == '__main__':
    unittest.main()
