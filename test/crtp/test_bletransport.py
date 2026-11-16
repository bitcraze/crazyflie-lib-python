"""BLE codec tests: no Bleak import, platform backend or hardware."""
import unittest

from cflib.crtp.bletransport import DownDecoder
from cflib.crtp.bletransport import fragment_up
from cflib.crtp.bletransport import FrameError


class CodecTests(unittest.TestCase):
    def test_all_lengths_and_pids_roundtrip(self):
        for size in range(1, 32):
            for pid in range(4):
                packet = bytes(range(size))
                decoder = DownDecoder()
                result = None
                for frame in fragment_up(packet, pid):
                    result = decoder.feed(frame)
                self.assertEqual(result, packet)

    def test_corruption_rejected(self):
        decoder = DownDecoder()
        decoder.feed(fragment_up(bytes(31), 1)[0])
        with self.assertRaises(FrameError):
            decoder.feed(b'\x00\x01')
        with self.assertRaises(FrameError):
            decoder.feed(b'\x80\0\0')

    def test_rejects_invalid_packet_and_fragment_sizes(self):
        for packet in (b'', bytes(32)):
            with self.assertRaises(FrameError):
                fragment_up(packet, 0)
        for fragment in (b'', b'\x80', bytes(21)):
            with self.assertRaises(FrameError):
                DownDecoder().feed(fragment)

    def test_rejects_orphan_continuation_and_recovers(self):
        decoder = DownDecoder()
        with self.assertRaises(FrameError):
            decoder.feed(b'\x00\x01')
        packet = b'\xfcdata'
        self.assertEqual(decoder.feed(fragment_up(packet, 2)[0]), packet)

    def test_new_start_during_partial_packet_rejects_and_resets(self):
        decoder = DownDecoder()
        first = fragment_up(bytes(range(31)), 1)[0]
        self.assertIsNone(decoder.feed(first))
        with self.assertRaises(FrameError):
            decoder.feed(first)
        packet = b'\xfcrecovered'
        self.assertEqual(decoder.feed(fragment_up(packet, 3)[0]), packet)

    def test_reset_discards_incomplete_packet(self):
        decoder = DownDecoder()
        fragments = fragment_up(bytes(range(31)), 0)
        self.assertIsNone(decoder.feed(fragments[0]))
        decoder.reset()
        with self.assertRaises(FrameError):
            decoder.feed(fragments[1])
