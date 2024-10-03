import collections
import time

import numpy as np


class SignalHealth:
    """
    Tracks the health of the signal by monitoring link quality and uplink RSSI
    using exponential moving averages.
    """

    def __init__(self, signal_health_callback, alpha=0.1):
        """
        Initialize the SignalHealth class.

        :param alpha: Weight for the exponential moving average (default 0.1)
        """
        self._alpha = alpha
        self._signal_health_callback = signal_health_callback

        self._retries = collections.deque()
        self._retry_sum = 0

    def update(self, ack, packet_out):
        """
        Update the signal health based on the acknowledgment data.

        :param ack: Acknowledgment object containing retry and RSSI data.
        """
        self.signal_health = {}

        self._update_link_quality(ack)
        self._update_rssi(ack)
        self._update_rate_and_congestion(ack, packet_out)

        if self.signal_health:
            self._signal_health_callback(self.signal_health)

    def _update_link_quality(self, ack):
        """
        Updates the link quality based on the number of retries.

        :param ack: Acknowledgment object with retry data.
        """
        if ack:
            retry = 10 - ack.retry
            self._retries.append(retry)
            self._retry_sum += retry
            if len(self._retries) > 100:
                self._retry_sum -= self._retries.popleft()
            self.signal_health['link_quality'] = float(self._retry_sum) / len(self._retries) * 10

    def _update_rssi(self, ack):
        """
        Updates the uplink RSSI based on the acknowledgment signal.

        :param ack: Acknowledgment object with RSSI data.
        """
        if not hasattr(self, '_rssi_timestamps'):
            self._rssi_timestamps = collections.deque(maxlen=100)
        if not hasattr(self, '_rssi_values'):
            self._rssi_values = collections.deque(maxlen=100)

        # update RSSI if the acknowledgment contains RSSI data
        if ack.ack and len(ack.data) > 2 and ack.data[0] & 0xf3 == 0xf3 and ack.data[1] == 0x01:
            instantaneous_rssi = ack.data[2]
            self._rssi_values.append(instantaneous_rssi)
            self._rssi_timestamps.append(time.time())

            # Calculate time-weighted average RSSI
            if len(self._rssi_timestamps) >= 2:  # At least 2 points are needed to calculate differences
                time_diffs = np.diff(self._rssi_timestamps, prepend=time.time())
                weights = np.exp(-time_diffs)
                weighted_average = np.sum(weights * self._rssi_values) / np.sum(weights)
                self.signal_health['uplink_rssi'] = weighted_average

    def _update_rate_and_congestion(self, ack, packet_out):
        """
        Updates the packet rate and bandwidth congestion based on the acknowledgment data.

        :param ack: Acknowledgment object with congestion data.
        """
        if not hasattr(self, '_previous_time_stamp'):
            self._previous_time_stamp = time.time()
        if not hasattr(self, '_amount_null_packets_up'):
            self._amount_null_packets_up = 0
        if not hasattr(self, '_amount_packets_up'):
            self._amount_packets_up = 0
        if not hasattr(self, '_amount_null_packets_down'):
            self._amount_null_packets_down = 0
        if not hasattr(self, '_amount_packets_down'):
            self._amount_packets_down = 0

        self._amount_packets_up += 1  # everytime this function is called, a packet is sent
        if not packet_out:  # if the packet is empty, we send a null packet
            self._amount_null_packets_up += 1

        # Find null packets in the downlink and count them
        mask = 0b11110011
        if ack.data:
            empty_ack_packet = int(ack.data[0]) & mask

            if empty_ack_packet == 0xF3:
                self._amount_null_packets_down += 1
            self._amount_packets_down += 1

            # rate and congestion stats every N seconds
            if time.time() - self._previous_time_stamp > 0.1:
                # self._uplink_rate = self._amount_packets_up / (time.time() - self._previous_time_stamp)
                self.signal_health['uplink_rate'] = self._amount_packets_up / (time.time() - self._previous_time_stamp)
                self.signal_health['downlink_rate'] = self._amount_packets_down / \
                    (time.time() - self._previous_time_stamp)
                self.signal_health['uplink_congestion'] = 1.0 - self._amount_null_packets_up / self._amount_packets_up
                self.signal_health['downlink_congestion'] = 1.0 - \
                    self._amount_null_packets_down / self._amount_packets_down

                self._amount_packets_up = 0
                self._amount_null_packets_up = 0
                self._amount_packets_down = 0
                self._amount_null_packets_down = 0
                self._previous_time_stamp = time.time()
