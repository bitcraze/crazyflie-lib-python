"""
CRTP BLE driver.
"""
from __future__ import annotations

import platform
import re
import asyncio

from bleak import BleakClient as BLEClient, BleakScanner as BLEScanner
from bleak.backends.device import BLEDevice

from crtpdriver import CRTPDriver
from crtpstack import CRTPPacket

from exceptions import WrongUriType



__author__ = 'UnexDev'
__all__ = ['BLEDriver']


CRTP_SERVICE_UUID = '00000201-1C7F-4F9E-947B-43B7C00A9A08'
CRTP_UUID = '00000202-1C7F-4F9E-947B-43B7C00A9A08'
CRTPUP_UUID = '00000203-1C7F-4F9E-947B-43B7C00A9A08'
CRTPDOWN_UUID = '00000204-1C7F-4F9E-947B-43B7C00A9A08'

class BLEDriver(CRTPDriver):
    """
    Driver to interface with a CRTP-capable device over Bluetooth Low Energy (BLE).

    The BLE driver is asynchronous by nature, and is designed to be used with the `asyncio` package.
    To use the BLE driver, you must call `asyncio.run(main())`, where `main` is the name of your main function.
    This will allow you to mark the `main` function as `async`, thus allowing you to use the `await` keyword on methods in this class.
    """

    client: BLEClient

    def __init__(self):
        # self.packet_id = 0 # For use with CRTPUP/DOWN.
        pass

    @staticmethod
    def parse_uri(uri: str) -> tuple[str, int] | None:
        regex: str = r'ble:\/\/([0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2})\?connect_timeout=([0-9]+)'
        if platform.platform().startswith('macOS'):
            # MacOS uses random UUIDs instead of exposing the BT address of the device.
            regex = r'ble:\/\/([0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12})\?connect_timeout=([0-9]+)'
        print(regex)
        result = re.fullmatch(regex, uri, re.RegexFlag.I)
        if result == None: return None

        groups = result.groups()
        if len(groups) != 2: return None # If not all params were provided.

        return ((groups[0]), int(groups[1]))
    
    async def connect(self, uri: str, link_quality_callback, link_error_callback):
        _uri = BLEDriver.parse_uri(uri)
        if _uri == None: raise WrongUriType(f'Invalid BLE URI: {uri}')
        (address, timeout) = _uri

        self.client = BLEClient(address_or_ble_device=address, timeout=timeout, services=[CRTP_SERVICE_UUID]) # Used to interface with the device.
        await self.client.connect()
        if self.client.is_connected: link_quality_callback(100)
        else: link_error_callback()


    async def send_packet(self, pk: CRTPPacket):
        if (pk.size > 20):
            # TODO: Can use CRTPUP and CRTPDOWN characteristics to send larger than 20 bytes packets.
            raise OverflowError('Sending packets greater than 20 bytes is currently not supported. Try a different driver.')

        if not self.client.is_connected:
            raise RuntimeError('Not connected to Crazyflie.')

        packet = bytearray([pk.get_header()]) + pk._get_data()
        await self.client.write_gatt_char(CRTP_UUID, packet, False)
        

    async def receive_packet(self, wait=2):
        return await self.client.read_gatt_char(CRTP_UUID)
        # if wait == 0:
        #     try: return ...
        #     except: return None
        # elif wait == -1:
        #     try: return ...
        #     except: return None
        # else:
        #     try: return ...
        #     except: return None



    def get_status(self):
        raise NotImplementedError()

    def get_name(self):
        return 'Bluetooth Low Energy (BLE)'

    async def scan_interface(self, address: str=None):
        """
        Returns an async generator of devices.
        """
        async with BLEScanner() as scanner:
            async for (device, ad) in scanner.advertisement_data():
                if ad.service_uuids[0] != CRTP_SERVICE_UUID: continue
                elif address == device.address: yield device
                elif address == None: yield device


    def enum(self):
        raise NotImplementedError()

    def get_help(self):
        raise NotImplementedError()

    async def close(self):
        await self.client.disconnect()

# Control byte not needed for the CRTP characteristic; if we plan to support packets with a length > 20 bytes, 
# we need to implement the CRTPUP and CRTPDOWN characteristics, which require a control byte.
class ControlByte:
    raw: int

    def __init__(self, start: bool, pid: int, length: int) -> None: 
        self.raw = (0x80 if start else 0x00) | ((pid & 0x03) << 5) | ((length - 1) & 0x1f)
    
    @property
    def pid(self) -> int:
        return ((self.raw & 0b0110_0000) >> 5)
    
    @property
    def start(self) -> bool:
        return ((self.raw & 0x80) != 0)

    @property
    def length(self) -> int:
        return (self.raw & 0b0001_1111) + 1
