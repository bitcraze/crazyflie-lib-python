import collections
import time

import numpy as np


class SignalHealth:
    """
    Tracks the health of the signal by monitoring link quality and uplink RSSI
    using exponential moving averages.
    """

    def __init__(self, alpha=0.1):
        """
        Initialize the SignalHealth class.

        :param alpha: Weight for the exponential moving average (default 0.1)
        """
        self.alpha = alpha
        self.link_quality = 0
        self.uplink_rssi = 0
        self._retries = collections.deque()
        self._retry_sum = 0

    def update(self, ack):
        """
        Update the signal health based on the acknowledgment data.

        :param ack: Acknowledgment object containing retry and RSSI data.
        """
        self._update_link_quality(ack)
        self._update_rssi(ack)

    def _update_link_quality(self, ack):
        """
        Updates the link quality based on the acknowledgment data.

        :param ack: Acknowledgment object with retry data.
        """
        retry = 10 - ack.retry
        self._retries.append(retry)
        self._retry_sum += retry
        if len(self._retries) > 100:
            self._retry_sum -= self._retries.popleft()
        self.link_quality = float(self._retry_sum) / len(self._retries) * 10

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
                self.uplink_rssi = weighted_average
            else:
                self.uplink_rssi = instantaneous_rssi  # Return the raw value if not enough data
