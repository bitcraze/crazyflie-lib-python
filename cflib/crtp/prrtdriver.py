#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import logging
import re

from .crtpstack import CRTPPacket
from .exceptions import WrongUriType
from cflib.crtp.crtpdriver import CRTPDriver

prrt_installed = True
try:
    import prrt
except ImportError:
    prrt_installed = False

__author__ = 'Bitcraze AB'
__all__ = ['PrrtDriver']

logger = logging.getLogger(__name__)

MAX_PAYLOAD = 32
DEFAULT_TARGET_DELAY = 0.05  # unit: s
PRRT_LOCAL_PORT = 5000


class PrrtDriver(CRTPDriver):

    def __init__(self):
        CRTPDriver.__init__(self)
        self.prrt_socket = None
        self.uri = ''
        self.link_error_callback = None
        self.packet_log = None
        self.log_index = 0
        logger.info('Initialized PRRT driver.')

    def connect(self, uri, linkQualityCallback, linkErrorCallback):
        # check if the URI is a PRRT URI
        if not re.search('^prrt://', uri):
            raise WrongUriType('Not a prrt URI')

        # Check if it is a valid PRRT URI
        uri_match = re.search(r'^prrt://((?:[\d]{1,3})\.(?:[\d]{1,3})\.'
                              r'(?:[\d]{1,3})\.(?:[\d]{1,3})):([\d]{1,5})'
                              r'(?:/([\d]{1,6}))?$', uri)
        if not uri_match:
            raise Exception('Invalid PRRT URI')

        if not prrt_installed:
            raise Exception('PRRT is missing')

        self.uri = uri

        self.link_error_callback = linkErrorCallback

        address = uri_match.group(1)
        port = int(uri_match.group(2))
        target_delay_s = DEFAULT_TARGET_DELAY
        if uri_match.group(3):
            target_delay_s = int(uri_match.group(3)) / 1000

        self.prrt_socket = prrt.PrrtSocket(('0.0.0.0', PRRT_LOCAL_PORT),
                                           maximum_payload_size=MAX_PAYLOAD,
                                           target_delay=target_delay_s)
        self.prrt_socket.connect((address, port))

    def send_packet(self, pk):
        pk_bytes = bytearray([pk.get_header()]) + pk.data
        self.prrt_socket.send(pk_bytes)

    def receive_packet(self, wait=0):
        try:
            if wait == 0:
                pk_bytes, _ = self.prrt_socket.receive_asap()
            elif wait < 0:
                pk_bytes, _ = self.prrt_socket.receive_asap_wait()
            else:
                deadline = datetime.datetime.utcnow() + datetime.timedelta(
                    seconds=wait)
                pk_bytes, _ = self.prrt_socket.receive_asap_timedwait(deadline)
        except prrt.TimeoutException:
            return None

        if len(pk_bytes) <= 0:
            return None

        pk = CRTPPacket(pk_bytes[0], pk_bytes[1:])
        return pk

    def get_status(self):
        return 'No information available'

    def get_name(self):
        return 'prrt'

    def scan_interface(self, address):
        default_uri = 'prrt://10.8.0.208:5000'
        if prrt_installed:
            return [[default_uri, ''], ]
        return []

    def close(self):
        return
