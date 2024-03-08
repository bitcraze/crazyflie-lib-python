"""
CRTP BLE driver.
"""

import platform
import re
import asyncio

from bleak import BleakClient as BLEClient, BleakScanner as BLEScanner

from crtpdriver import CRTPDriver
from crtpstack import CRTPPacket
from exceptions import WrongUriType
__author__ = 'UnexDev'
__all__ = ['CRTPDriver']


SERVICE_UUID = '00000201-1C7F-4F9E-947B-43B7C00A9A08'
CRTPUP_UUID = '00000203-1C7F-4F9E-947B-43B7C00A9A08'
CRTPDOWN_UUID = '00000204-1C7F-4F9E-947B-43B7C00A9A08'

class BLEDriver:
    """
    Driver to interface with a CRTP-capable device over Bluetooth Low Energy (BLE).
    The BLE driver is asynchronous by nature, and is designed to be used with the `asyncio` package.
    To use the BLE driver, you must call `asyncio.run(main())`, where `main` is the name of your main function.
    This will allow you to mark the `main` function as `async`, thus allowing you to use the `await` keyword on methods in this class.
    """
    address: str
    client: BLEClient
    packet_id: int

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.address = ''
        self.packet_id = 0,
    
    async def connect(self, uri: str, link_quality_callback, link_error_callback):
        if not uri.startswith('ble://'):
            raise WrongUriType('Not a BLE URI')
        
        address = uri.removeprefix('ble://')

        is_valid_address = False
        if platform.platform() == 'Darwin' and re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', address):
                is_valid_address = True
        else:
            if re.fullmatch(r'([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2})', address):
                is_valid_address = True
        
        if not is_valid_address:
            raise WrongUriType('Not a BLE address')
        
        self.address = address

        self.client = BLEClient(address=self.address)
        await self.client.connect()


    async def send_packet(self, pk: CRTPPacket):
        data1: bytearray
        data2: bytearray | None  = None


        if (pk.size > 19):
   
            if len(pk._get_data()[19:]) > 19:
                raise ValueError('Packet too large to send. Only packets up to 48 bytes in length are supported')
        else:
            data1 = pk._get_data()


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

    @staticmethod
    def _split_data(pk_data: bytearray) -> list[bytearray]:
        datas: list[bytearray] = []

        if len(pk_data > 19):
            datas.append(pk_data[:19])
            datas = datas + BLEDriver._split_data(pk_data[19:])
        else:
            datas.append(pk_data)
        
        return datas
    

def dec_to_bin(n): 
    return int(bin(n).replace("0b", ""))