# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2024 Bitcraze AB
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
This module provides tools for tracking statistics related to the communication
link between the Crazyflie and the lib. Currently, it focuses on tracking latency
but is designed to be extended with additional link statistics in the future.
"""
import struct
import time
from threading import Event
from threading import Thread

import numpy as np

from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort
from cflib.utils.callbacks import Caller

__author__ = 'Bitcraze AB'
__all__ = ['LinkStatistics']

PING_HEADER = 0x0
ECHO_CHANNEL = 0


class LinkStatistics:
    """
    LinkStatistics class manages the collection of various statistics related to the
    communication link between the Crazyflie and the lib.

    This class serves as a high-level manager, initializing and coordinating multiple
    statistics trackers, such as Latency. It allows starting and stopping all
    statistics trackers simultaneously. Future statistics can be added to extend
    the class's functionality.

    Attributes:
        _cf (Crazyflie): A reference to the Crazyflie instance.
        latency (Latency): An instance of the Latency class that tracks latency statistics.
    """

    def __init__(self, crazyflie):
        self._cf = crazyflie

        # Flag to track if the statistics are active
        self._is_active = False

        # Universal statistics
        self.latency = Latency(self._cf)

        # Proxy for latency callback
        self.latency_updated = self.latency.latency_updated

        # Callers for radio link statistics
        self.link_quality_updated = Caller()
        self.uplink_rssi_updated = Caller()
        self.uplink_rate_updated = Caller()
        self.downlink_rate_updated = Caller()
        self.uplink_congestion_updated = Caller()
        self.downlink_congestion_updated = Caller()

    def start(self):
        """
        Start collecting all statistics.
        """
        self._is_active = True
        self.latency.start()

    def stop(self):
        """
        Stop collecting all statistics.
        """
        self._is_active = False
        self.latency.stop()

    def radio_link_statistics_callback(self, radio_link_statistics):
        """
        This callback is called by the RadioLinkStatistics class after it
        processes the data provided by the radio driver.
        """
        if not self._is_active:
            return  # Skip processing if link statistics are stopped

        if 'link_quality' in radio_link_statistics:
            self.link_quality_updated.call(radio_link_statistics['link_quality'])
        if 'uplink_rssi' in radio_link_statistics:
            self.uplink_rssi_updated.call(radio_link_statistics['uplink_rssi'])
        if 'uplink_rate' in radio_link_statistics:
            self.uplink_rate_updated.call(radio_link_statistics['uplink_rate'])
        if 'downlink_rate' in radio_link_statistics:
            self.downlink_rate_updated.call(radio_link_statistics['downlink_rate'])
        if 'uplink_congestion' in radio_link_statistics:
            self.uplink_congestion_updated.call(radio_link_statistics['uplink_congestion'])
        if 'downlink_congestion' in radio_link_statistics:
            self.downlink_congestion_updated.call(radio_link_statistics['downlink_congestion'])


class Latency:
    """
    The Latency class measures and tracks the latency of the communication link
    between the Crazyflie and the lib.

    This class periodically sends ping requests to the Crazyflie and tracks
    the round-trip time (latency). It calculates and stores the 95th percentile
    latency over a rolling window of recent latency measurements.

    Attributes:
        _cf (Crazyflie): A reference to the Crazyflie instance.
        latency (float): The current calculated 95th percentile latency in milliseconds.
        _stop_event (Event): An event object to control the stopping of the ping thread.
        _ping_thread_instance (Thread): Thread instance for sending ping requests at intervals.
    """

    def __init__(self, crazyflie):
        self._cf = crazyflie
        self._cf.add_header_callback(self._ping_response, CRTPPort.LINKCTRL, 0)
        self._stop_event = Event()
        self._ping_thread_instance = None
        self.latency = 0
        self.latency_updated = Caller()

    def start(self):
        """
        Start the latency tracking process.

        This method initiates a background thread that sends ping requests
        at regular intervals to measure and track latency statistics.
        """
        if self._ping_thread_instance is None or not self._ping_thread_instance.is_alive():
            self._stop_event.clear()
            self._ping_thread_instance = Thread(target=self._ping_thread, name='ping_thread')
            self._ping_thread_instance.start()

    def stop(self):
        """
        Stop the latency tracking process.

        This method stops the background thread and ceases sending further
        ping requests, halting latency measurement.
        """
        self._stop_event.set()
        if self._ping_thread_instance is not None:
            self._ping_thread_instance.join()
            self._ping_thread_instance = None

    def _ping_thread(self, interval: float = 0.1) -> None:
        """
        Background thread method that sends a ping to the Crazyflie at regular intervals.

        This method runs in a separate thread and continues to send ping requests
        until the stop event is set.

        Args:
            interval (float): The time (in seconds) to wait between ping requests. Default is 0.1 seconds.
        """
        while not self._stop_event.is_set():
            self.ping()
            time.sleep(interval)

    def ping(self) -> None:
        """
        Send a ping request to the Crazyflie to measure latency.

        A ping packet is sent to the Crazyflie with the current timestamp and a
        header identifier to differentiate it from other echo responses. The latency
        is calculated upon receiving the response.
        """
        ping_packet = CRTPPacket()
        ping_packet.set_header(CRTPPort.LINKCTRL, ECHO_CHANNEL)

        # Pack the current time as the ping timestamp
        current_time = time.time()
        ping_packet.data = struct.pack('<Bd', PING_HEADER, current_time)
        self._cf.send_packet(ping_packet)

    def _ping_response(self, packet):
        """
        Callback method for processing the echo response received from the Crazyflie.

        This method is called when a ping response is received. It checks the header
        to verify that it matches the sent ping header before calculating the latency
        based on the timestamp included in the ping request.

        Args:
            packet (CRTPPacket): The packet received from the Crazyflie containing
            the echo response data.
        """
        received_header, received_timestamp = struct.unpack('<Bd', packet.data)
        if received_header != PING_HEADER:
            return
        self.latency = self._calculate_p95_latency(received_timestamp)
        self.latency_updated.call(self.latency)

    def _calculate_p95_latency(self, timestamp):
        """
        Calculate the 95th percentile latency based on recent ping measurements.

        This method records the round-trip time for a ping response and maintains
        a rolling window of latency values to compute the 95th percentile.

        Args:
            timestamp (float): The timestamp from the sent ping packet to calculate
            the round-trip time.

        Returns:
            float: The updated 95th percentile latency in milliseconds.
        """
        if not hasattr(self, '_latencies'):
            self._latencies = []

        instantaneous_latency = (time.time() - timestamp) * 1000
        self._latencies.append(instantaneous_latency)
        if len(self._latencies) > 100:
            self._latencies.pop(0)
        p95_latency = np.percentile(self._latencies, 95)
        return p95_latency
