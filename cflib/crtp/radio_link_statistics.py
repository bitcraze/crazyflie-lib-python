import collections
import time

import numpy as np


class RadioLinkStatistics:
    """
    Tracks the health of the signal by monitoring link quality, uplink RSSI,
    packet rates, and congestion.
    """

    def __init__(self, radio_link_statistics_callback, alpha=0.1):
        """
        Initialize the RadioLinkStatistics class.

        :param alpha: Weight for the exponential moving average (default 0.1)
        """
        self._alpha = alpha
        self._radio_link_statistics_callback = radio_link_statistics_callback

        self._retries = collections.deque()
        self._retry_sum = 0

    def update(self, ack, packet_out):
        """
        Update the radio link statistics based on the acknowledgment data.

        :param ack: Acknowledgment object containing retry and RSSI data.
        """
        self.radio_link_statistics = {}

        self._update_link_quality(ack)
        self._update_rssi(ack)
        self._update_rate_and_congestion(ack, packet_out)

        if self.radio_link_statistics and self._radio_link_statistics_callback:
            self._radio_link_statistics_callback(self.radio_link_statistics)

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
            self.radio_link_statistics['link_quality'] = float(self._retry_sum) / len(self._retries) * 10

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
                self.radio_link_statistics['uplink_rssi'] = weighted_average

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
                self.radio_link_statistics['uplink_rate'] = self._amount_packets_up / \
                    (time.time() - self._previous_time_stamp)
                self.radio_link_statistics['downlink_rate'] = self._amount_packets_down / \
                    (time.time() - self._previous_time_stamp)
                self.radio_link_statistics['uplink_congestion'] = 1.0 - \
                    self._amount_null_packets_up / self._amount_packets_up
                self.radio_link_statistics['downlink_congestion'] = 1.0 - \
                    self._amount_null_packets_down / self._amount_packets_down

                self._amount_packets_up = 0
                self._amount_null_packets_up = 0
                self._amount_packets_down = 0
                self._amount_null_packets_down = 0
                self._previous_time_stamp = time.time()
