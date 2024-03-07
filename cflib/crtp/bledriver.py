"""
CRTP BLE driver.
"""

from .crtpdriver import CRTPDriver
from .crtpstack import CRTPPacket

__author__ = 'UnexDev'
__all__ = ['CRTPDriver']


class BLEDriver:
    def __init__(self):
        pass

    def connect(self, uri: str, link_quality_callback, link_error_callback):
        pass

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
