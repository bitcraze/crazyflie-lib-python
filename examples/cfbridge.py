#!/usr/bin/env python
"""
Bridge a Crazyflie connected to a Crazyradio to a local MAVLink port
Requires 'pip install cflib'

As the ESB protocol works using PTX and PRX (Primary Transmitter/Receiver)
modes. Thus, data is only received as a response to a sent packet.
So, we need to constantly poll the receivers for bidirectional communication.

@author: Dennis Shtatnov (densht@gmail.com)

Based off example code from crazyflie-lib-python/examples/read-eeprom.py
"""
# import struct
import logging
import socket
import sys
import threading
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crtp.crtpstack import CRTPPacket
# from cflib.crtp.crtpstack import CRTPPort

CRTP_PORT_MAVLINK = 8


# Only output errors from the logging framework
logging.basicConfig(level=logging.DEBUG)


class RadioBridge:
    def __init__(self, link_uri):
        """ Initialize and run the example with the specified link_uri """

        # UDP socket for interfacing with GCS
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(('127.0.0.1', 14551))

        # Create a Crazyflie object without specifying any cache dirs
        self._cf = Crazyflie()

        # Connect some callbacks from the Crazyflie API
        self._cf.link_established.add_callback(self._connected)
        self._cf.disconnected.add_callback(self._disconnected)
        self._cf.connection_failed.add_callback(self._connection_failed)
        self._cf.connection_lost.add_callback(self._connection_lost)

        print('Connecting to %s' % link_uri)

        # Try to connect to the Crazyflie
        self._cf.open_link(link_uri)

        # Variable used to keep main loop occupied until disconnect
        self.is_connected = True

        threading.Thread(target=self._server).start()

    def _connected(self, link_uri):
        """ This callback is called form the Crazyflie API when a Crazyflie
        has been connected and the TOCs have been downloaded."""
        print('Connected to %s' % link_uri)

        self._cf.packet_received.add_callback(self._got_packet)

    def _got_packet(self, pk):
        if pk.port == CRTP_PORT_MAVLINK:
            self._sock.sendto(pk.data, ('127.0.0.1', 14550))

    def _forward(self, data):
        pk = CRTPPacket()
        pk.port = CRTP_PORT_MAVLINK  # CRTPPort.COMMANDER
        pk.data = data  # struct.pack('<fffH', roll, -pitch, yaw, thrust)
        self._cf.send_packet(pk)

    def _server(self):
        while True:
            print('\nwaiting to receive message')

            # Only receive what can be sent in one message
            data, address = self._sock.recvfrom(256)

            print('received %s bytes from %s' % (len(data), address))

            for i in range(0, len(data), 30):
                self._forward(data[i:(i+30)])

    def _stab_log_error(self, logconf, msg):
        """Callback from the log API when an error occurs"""
        print('Error when logging %s: %s' % (logconf.name, msg))

    def _stab_log_data(self, timestamp, data, logconf):
        """Callback from a the log API when data arrives"""
        print('[%d][%s]: %s' % (timestamp, logconf.name, data))

    def _connection_failed(self, link_uri, msg):
        """Callback when connection initial connection fails (i.e no Crazyflie
        at the specified address)"""
        print('Connection to %s failed: %s' % (link_uri, msg))
        self.is_connected = False

    def _connection_lost(self, link_uri, msg):
        """Callback when disconnected after a connection has been made (i.e
        Crazyflie moves out of range)"""
        print('Connection to %s lost: %s' % (link_uri, msg))

    def _disconnected(self, link_uri):
        """Callback when the Crazyflie is disconnected (called in all cases)"""
        print('Disconnected from %s' % link_uri)
        self.is_connected = False


if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.radiodriver.set_retries_before_disconnect(1500)
    cflib.crtp.radiodriver.set_retries(3)
    cflib.crtp.init_drivers()

    if len(sys.argv) > 1:
        channel = str(sys.argv[1])
    else:
        channel = 80

    link_uri = 'radio://0/' + str(channel) + '/2M'
    le = RadioBridge(link_uri)

    # The Crazyflie lib doesn't contain anything to keep the application alive,
    # so this is where your application should do something. In our case we
    # are just waiting until we are disconnected.
    try:
        while le.is_connected:
            time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(1)
