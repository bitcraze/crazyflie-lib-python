# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2025 Bitcraze AB
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
Provides access to the supervisor module of the Crazyflie platform.
"""
import logging
import time

from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort

__author__ = 'Bitcraze AB'
__all__ = ['Supervisor']

logger = logging.getLogger(__name__)

SUPERVISOR_CH_INFO = 0
SUPERVISOR_CH_COMMAND = 1

# Bit positions
BIT_CAN_BE_ARMED = 0
BIT_IS_ARMED = 1
BIT_IS_AUTO_ARMED = 2
BIT_CAN_FLY = 3
BIT_IS_FLYING = 4
BIT_IS_TUMBLED = 5
BIT_IS_LOCKED = 6
BIT_IS_CRASHED = 7
BIT_HL_CONTROL_ACTIVE = 8
BIT_HL_TRAJ_FINISHED = 9
BIT_HL_CONTROL_DISABLED = 10

CMD_GET_STATE_BITFIELD = 0x0C

CMD_ARM_SYSTEM = 0x01
CMD_RECOVER_SYSTEM = 0x02


class Supervisor:
    """
    This class provides two main functionalities:

    1. **Reading the system state**
       Accesses the Crazyflie's supervisor bitfield to determine the current state,
       such as whether it can be armed, is flying or crashed.

    2. **Sending system commands**
       Sends arming/disarming requests and crash recovery commands to the Crazyflie.
    """
    STATES = [
        'Can be armed',
        'Is armed',
        'Is auto armed',
        'Can fly',
        'Is flying',
        'Is tumbled',
        'Is locked',
        'Is crashed',
        'HL control is active',
        'Finished HL trajectory',
        'HL control is disabled'
    ]

    def __init__(self, crazyflie):
        self._cf = crazyflie

        self._cache_timeout = 0.1   # seconds
        self._last_fetch_time = 0
        self._bitfield = None
        self._cf.add_port_callback(CRTPPort.SUPERVISOR, self._supervisor_callback)
        self._bitfield_response_received = False

    def _supervisor_callback(self, pk: CRTPPacket):
        """
        Called when a packet is received.
        """
        if len(pk.data) < 1:
            return

        cmd = pk.data[0]
        if cmd & 0x80:  # high bit = response
            orig_cmd = cmd & 0x7F
            if orig_cmd == CMD_GET_STATE_BITFIELD:
                self._bitfield = int.from_bytes(pk.data[1:], byteorder='little')
                self._bitfield_response_received = True
                logger.info(f'Supervisor bitfield received: 0x{self._bitfield:04X}')

            elif orig_cmd == CMD_ARM_SYSTEM:
                success = bool(pk.data[1])
                is_armed = bool(pk.data[2])
                logger.info(f'Arm response: success={success}, is_armed={is_armed}')

            elif orig_cmd == CMD_RECOVER_SYSTEM:
                success = bool(pk.data[1])
                recovered = bool(pk.data[2])
                logger.info(f'Recovery response: success={success}, recovered={recovered}')

    def _fetch_bitfield(self, timeout=0.2):
        """
        Request the bitfield and wait for response (blocking).
        Uses time-based cache to avoid sending packages too frequently.
        """
        now = time.time()

        # Return cached value if it's recent enough
        if self._bitfield is not None and (now - self._last_fetch_time) < self._cache_timeout:
            return self._bitfield

        # Send a new request
        self._bitfield_response_received = False
        pk = CRTPPacket()
        pk.set_header(CRTPPort.SUPERVISOR, SUPERVISOR_CH_INFO)
        pk.data = [CMD_GET_STATE_BITFIELD]
        self._cf.send_packet(pk)

        # Wait for response
        start_time = now
        while not self._bitfield_response_received:
            if time.time() - start_time > timeout:
                logger.warning('Timeout waiting for supervisor bitfield response')
                return self._bitfield or 0  # still return last known value
            time.sleep(0.01)

        # Update timestamp
        self._last_fetch_time = time.time()
        return self._bitfield or 0

    def _bit(self, position):
        bitfield = self._fetch_bitfield()
        return bool((bitfield >> position) & 0x01)

    def read_bitfield(self):
        """
        Directly get the full bitfield value.
        """
        return self._fetch_bitfield()

    def read_state_list(self):
        """
        Reads the bitfield and returns the list of all active states.
        """
        bitfield = self.read_bitfield()
        list = self.decode_bitfield(bitfield)
        return list

    def decode_bitfield(self, value):
        """
        Given a bitfield integer `value` and a list of `self.STATES`,
        returns the names of all states whose bits are set.
        Bit 0 corresponds to states[0], Bit 1 to states[1], etc.
        * Bit 0 = Can be armed - the system can be armed and will accept an arming command.
        * Bit 1 = Is armed - the system is armed.
        * Bit 2 = Is auto armed - the system is configured to automatically arm.
        * Bit 3 = Can fly - the Crazyflie is ready to fly.
        * Bit 4 = Is flying - the Crazyflie is flying.
        * Bit 5 = Is tumbled - the Crazyflie is up side down.
        * Bit 6 = Is locked - the Crazyflie is in the locked state and must be restarted.
        * Bit 7 = Is crashed - the Crazyflie has crashed.
        * Bit 8 = High level control is actively flying the drone.
        * Bit 9 = High level trajectory has finished.
        * Bit 10 = High level control is disabled and not producing setpoints.
        """
        if value < 0:
            raise ValueError('value must be >= 0')

        result = []
        for bit_index, name in enumerate(self.STATES):
            if value & (1 << bit_index):
                result.append(name)

        return result

    @property
    def can_be_armed(self):
        return self._bit(BIT_CAN_BE_ARMED)

    @property
    def is_armed(self):
        return self._bit(BIT_IS_ARMED)

    @property
    def is_auto_armed(self):
        return self._bit(BIT_IS_AUTO_ARMED)

    @property
    def can_fly(self):
        return self._bit(BIT_CAN_FLY)

    @property
    def is_flying(self):
        return self._bit(BIT_IS_FLYING)

    @property
    def is_tumbled(self):
        return self._bit(BIT_IS_TUMBLED)

    @property
    def is_locked(self):
        return self._bit(BIT_IS_LOCKED)

    @property
    def is_crashed(self):
        return self._bit(BIT_IS_CRASHED)

    @property
    def hl_control_active(self):
        return self._bit(BIT_HL_CONTROL_ACTIVE)

    @property
    def hl_traj_finished(self):
        return self._bit(BIT_HL_TRAJ_FINISHED)

    @property
    def hl_control_disabled(self):
        return self._bit(BIT_HL_CONTROL_DISABLED)

    def send_arming_request(self, do_arm: bool):
        """
        Send system arm/disarm request.

        Args:
            do_arm (bool): True = arm the system, False = disarm the system
        """
        pk = CRTPPacket()
        pk.set_header(CRTPPort.SUPERVISOR, SUPERVISOR_CH_COMMAND)
        pk.data = (CMD_ARM_SYSTEM, do_arm)
        self._cf.send_packet(pk)
        logger.debug(f"Sent arming request: do_arm={do_arm}")

    def send_crash_recovery_request(self):
        """
        Send crash recovery request.
        """
        pk = CRTPPacket()
        pk.set_header(CRTPPort.SUPERVISOR, SUPERVISOR_CH_COMMAND)
        pk.data = (CMD_RECOVER_SYSTEM,)
        self._cf.send_packet(pk)
        logger.debug('Sent crash recovery request')
