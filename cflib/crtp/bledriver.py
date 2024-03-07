"""
CRTP BLE driver.
"""

import platform
import re
import asyncio

from bleak import BleakClient as BLEClient, BleakScanner as BLEScanner

from .crtpdriver import CRTPDriver
from .crtpstack import CRTPPacket
from .exceptions import WrongUriType
__author__ = 'UnexDev'
__all__ = ['CRTPDriver']


class BLEDriver:
    """
    Driver to interface with a CRTP-capable device over Bluetooth Low Energy (BLE).
    """
    address: str
    client: BLEClient
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.address = ''

    async def connect(self, uri: str, link_quality_callback, link_error_callback):
        if not uri.startswith('ble://'):
            raise WrongUriType('Not a BLE URI')
        
        address = uri.removeprefix('ble://')

        is_valid_address = False
        if platform.platform() == 'Darwin' and re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', address):
                is_valid_address = True
        else:
            if re.fullmatch(r'([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2})'):
                is_valid_address = True
        
        if not is_valid_address:
            raise WrongUriType('Not a BLE address')
        
        self.address = address

    def send_packet(self, pk: CRTPPacket):
        pass

    def receive_packet(self, wait=0):
        pass

    def get_status(self):
        pass

    def get_name(self):
        pass

    def scan_interface(self, address: str=None):
        pass

    def enum(self):
        pass

    def get_help(self):
        pass

    def close(self):
        pass
