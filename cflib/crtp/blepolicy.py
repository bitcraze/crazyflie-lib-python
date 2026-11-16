"""Mandatory BLE bench packet policy, separate from wire framing.

Copyright (C) 2026. Licensed under GPL-3.0-or-later, as part of cflib.
"""


def bench_allowed(packet):
    """Allow read/query/log operations; flight and persistent writes stay blocked."""
    if not 1 <= len(packet) <= 31:
        return False
    h, data = packet[0] & 0xF3, packet[1:]
    if packet == b'\xff':
        return True
    if h == 0xF0:  # Echo, no bootloader/null payloads
        return True
    if h == 0xF1:  # Firmware identification, not link-layer control
        return data == b'\x00'
    if h == 0xD1:
        return data in (b'\x00', b'\x01', b'\x02')
    if h in (0x20, 0x50):  # Param/log TOC v1/v2
        return (data in (b'\x01', b'\x03') or
                len(data) == 2 and data[0] == 0 or
                len(data) == 3 and data[0] == 2)
    if h == 0x21:
        return len(data) in (1, 2)  # Param value read
    if h == 0x23:
        return len(data) == 3 and data[0] in (2, 4, 6, 7, 8)
    if h == 0x40:  # Memory enumeration only
        return data in (b'\x00', b'\x01') or len(data) == 2 and data[0] == 2
    if h == 0x51 and data:
        if data[0] in (2, 4):  # Delete/stop an explicitly selected log block
            return len(data) == 2
        if data[0] == 3:
            return len(data) == 3 and data[2] >= 10  # >=100 ms
        if data[0] == 8:
            return len(data) == 4 and int.from_bytes(data[2:], 'little') >= 100
        if data[0] in (6, 7):  # TOC-backed logging only, never raw-memory ops
            return (len(data) >= 5 and (len(data) - 2) % 3 == 0 and
                    all(1 <= data[i] & 15 <= 8 and 1 <= data[i] >> 4 <= 8 and
                        data[i+1:i+3] != b'\xff\xff' for i in range(2, len(data), 3)))
    return False
