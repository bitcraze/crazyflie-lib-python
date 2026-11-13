"""Crazyflie BLE CRTP framing, independent of an IO backend.

Copyright (C) 2026. Licensed under GPL-3.0-or-later, as part of cflib.
"""


class FrameError(ValueError):
    """A BLE fragment does not follow the documented CRTP wire format."""


class DownDecoder:
    """Reassemble one packet at a time; malformed input discards partial state."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Discard any incomplete packet at a connection or error boundary."""
        self.pid = None
        self.expected = 0
        self.data = bytearray()

    def feed(self, value):
        """Return a complete packet, None for a partial one, or raise FrameError."""
        try:
            if not 2 <= len(value) <= 20:
                raise FrameError('Invalid BLE notification size')
            control = value[0]
            pid = (control >> 5) & 3
            if control & 0x80:
                if self.pid is not None:
                    raise FrameError('New start before previous packet completed')
                self.pid, self.expected = pid, (control & 31) + 1
            elif self.pid is None or pid != self.pid or control & 31:
                raise FrameError('Missing start, wrong PID, or invalid continuation')
            self.data.extend(value[1:])
            if len(self.data) > self.expected:
                raise FrameError('Notification exceeds declared packet length')
            if len(self.data) == self.expected:
                packet = bytes(self.data)
                self.reset()
                return packet
            return None
        except FrameError:
            self.reset()
            raise


def fragment_up(packet, pid):
    """Encode a 1-31 byte CRTP packet into 20-byte ATT fragments using a 2-bit PID."""
    if not 1 <= len(packet) <= 31:
        raise FrameError('CRTP packet must contain 1..31 bytes')
    first = bytes([0x80 | ((pid & 3) << 5) | (len(packet) - 1)]) + packet[:19]
    return [first] + ([bytes([(pid & 3) << 5]) + packet[19:]] if len(packet) > 19 else [])
