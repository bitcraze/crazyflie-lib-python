import threading

from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie


class SupervisorState:
    STATES = [
        'Can be armed',
        'Is armed',
        'Auto armed',
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
        if isinstance(crazyflie, SyncCrazyflie):
            self.cf = crazyflie.cf
        else:
            self.cf = crazyflie

    def read_supervisor_state_bitfield(self):
        """
        Reads 'supervisor.info' once from the Crazyflie.
        Returns the value or None if timed out.
        """
        value_holder = {'val': None}
        event = threading.Event()

        def log_callback(timestamp, data, logconf):
            value_holder['val'] = data['supervisor.info']
            event.set()

        def log_error(logconf, msg):
            print(f'Error when logging {logconf.name}: {msg}')
            event.set()

        logconf = LogConfig(name='SupervisorInfo', period_in_ms=100)
        logconf.add_variable('supervisor.info', 'uint16_t')

        try:
            self.cf.log.add_config(logconf)
        except KeyError as e:
            print('Could not add log config:', e)
            return None

        logconf.data_received_cb.add_callback(log_callback)
        logconf.error_cb.add_callback(log_error)
        logconf.start()

        if event.wait(2.0):
            bitfield = value_holder['val']
        else:
            print('Timeout waiting for supervisor.info')
            bitfield = None

        logconf.stop()
        return bitfield

    def read_supervisor_state_list(self):
        """
        Reads 'supervisor.info' once from the Crazyflie.
        Returns the list of all active states.
        """
        bitfield = self.read_supervisor_state_bitfield()
        list = self.decode_bitfield(bitfield)
        return list

    def decode_bitfield(self, value):
        """
        Given a bitfield integer `value` and a list of `self.STATES`,
        returns the names of all states whose bits are set.
        Bit 0 corresponds to states[0], Bit 1 to states[1], etc.

        * Bit 0 = Can be armed - the system can be armed and will accept an arming command
        * Bit 1 = is armed - the system is armed
        * Bit 2 = auto arm - the system is configured to automatically arm
        * Bit 3 = can fly - the Crazyflie is ready to fly
        * Bit 4 = is flying - the Crazyflie is flying.
        * Bit 5 = is tumbled - the Crazyflie is up side down.
        * Bit 6 = is locked - the Crazyflie is in the locked state and must be restarted.
        * Bit 7 = is crashed - the Crazyflie has crashed.
        * Bit 8 = high level control is actively flying the drone
        * Bit 9 = high level trajectory has finished
        * Bit 10 = high level control is disabled and not producing setpoints
        """
        if value < 0:
            raise ValueError('value must be >= 0')

        result = []
        for bit_index, name in enumerate(self.STATES):
            if value & (1 << bit_index):
                result.append(name)
        return result

    # Individual state checks
    def can_be_armed(self):
        # Bit 0
        return bool(self.read_supervisor_state_bitfield() & (1 << 0))

    def is_armed(self):
        # Bit 1
        return bool(self.read_supervisor_state_bitfield() & (1 << 1))

    def is_auto_armed(self):
        # Bit 2
        return bool(self.read_supervisor_state_bitfield() & (1 << 2))

    def can_fly(self):
        # Bit 3
        return bool(self.read_supervisor_state_bitfield() & (1 << 3))

    def is_flying(self):
        # Bit 4
        return bool(self.read_supervisor_state_bitfield() & (1 << 4))

    def is_tumbled(self):
        # Bit 5
        return bool(self.read_supervisor_state_bitfield() & (1 << 5))

    def is_locked(self):
        # Bit 6
        return bool(self.read_supervisor_state_bitfield() & (1 << 6))

    def is_crashed(self):
        # Bit 7
        return bool(self.read_supervisor_state_bitfield() & (1 << 7))

    def active_hl_control(self):
        # Bit 8
        return bool(self.read_supervisor_state_bitfield() & (1 << 8))

    def finished_hl_traj(self):
        # Bit 9
        return bool(self.read_supervisor_state_bitfield() & (1 << 9))

    def disabled_hl_control(self):
        # Bit 10
        return bool(self.read_supervisor_state_bitfield() & (1 << 10))
