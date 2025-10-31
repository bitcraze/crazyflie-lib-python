"""Type stubs for cflib._rust"""

from __future__ import annotations

class LinkContext:
    """Link context for scanning and discovering Crazyflies"""

    def __init__(self) -> None:
        """Create a new link context"""
        ...

    def scan(self, address: list[int] | None = None) -> list[str]:
        """
        Scan for Crazyflies on a specific address.

        Args:
            address: Optional 5-byte address to scan (defaults to [0xE7, 0xE7, 0xE7, 0xE7, 0xE7])

        Returns:
            List of URIs found
        """
        ...

class Crazyflie:
    """
    Wrapper for the Crazyflie struct.

    Provides a Python interface to the Rust Crazyflie implementation.
    Since the Rust library is async, it's wrapped with a Tokio runtime.
    """

    @staticmethod
    def connect_from_uri(uri: str) -> Crazyflie:
        """
        Connect to a Crazyflie from a URI string.

        Args:
            uri: Connection URI (e.g., "radio://0/80/2M/E7E7E7E7E7")

        Returns:
            Connected Crazyflie instance
        """
        ...

    def disconnect(self) -> None:
        """Disconnect from the Crazyflie"""
        ...

    def console(self) -> Console:
        """Get the console subsystem"""
        ...

    def param(self) -> Param:
        """Get the param subsystem"""
        ...

    def commander(self) -> Commander:
        """Get the commander subsystem"""
        ...

    def platform(self) -> Platform:
        """Get the platform subsystem"""
        ...

    def log(self) -> Log:
        """Get the log subsystem"""
        ...

class Commander:
    """Commander subsystem - send control setpoints to the Crazyflie"""

    def send_setpoint(
        self, roll: float, pitch: float, yaw_rate: float, thrust: int
    ) -> None:
        """
        Send a setpoint with roll, pitch, yaw rate, and thrust.

        Args:
            roll: Roll in degrees
            pitch: Pitch in degrees
            yaw_rate: Yaw rate in degrees/second
            thrust: Thrust (0-65535)
        """
        ...

    def send_stop_setpoint(self) -> None:
        """Send a stop command (sets all values to 0)"""
        ...

class Console:
    """Console subsystem - read text output from the Crazyflie"""

    def get_lines(self) -> list[str]:
        """
        Get console lines as they arrive.

        Returns:
            List of console output lines (up to 100 with 10ms timeout)
        """
        ...

class Param:
    """Parameter subsystem - read and write configuration parameters"""

    def names(self) -> list[str]:
        """Get list of all parameter names"""
        ...

    def get(self, name: str) -> int | float:
        """
        Get a parameter value by name.

        Args:
            name: Parameter name

        Returns:
            Parameter value (int or float depending on parameter type)
        """
        ...

    def set(self, name: str, value: float) -> None:
        """
        Set a parameter value by name using lossy conversion from float.

        Args:
            name: Parameter name
            value: New parameter value
        """
        ...

class Platform:
    """Platform subsystem - query device information and firmware details"""

    def get_protocol_version(self) -> int:
        """Get platform protocol version"""
        ...

    def get_firmware_version(self) -> str:
        """Get firmware version string"""
        ...

    def get_device_type_name(self) -> str:
        """Get device type name"""
        ...

    def set_continuous_wave(self, activate: bool) -> None:
        """
        Set radio in continuous wave mode.

        Args:
            activate: If True, transmit continuous wave; if False, disable

        Warning:
            - Will disconnect the radio link (use over USB)
            - Will jam nearby radios including WiFi/Bluetooth
            - For testing purposes only in controlled environments
        """
        ...

    def send_arming_request(self, do_arm: bool) -> None:
        """
        Send system arm/disarm request.

        Arms or disarms the Crazyflie's safety systems. When disarmed,
        motors will not spin even if thrust commands are sent.

        Args:
            do_arm: True to arm, False to disarm
        """
        ...

    def send_crash_recovery_request(self) -> None:
        """
        Send crash recovery request.

        Requests recovery from a crash state detected by the Crazyflie.
        """
        ...

class Log:
    """Log subsystem"""

    def names(self) -> list[str]:
        """Get list of all log variable names"""
        ...

    def get_type(self, name: str) -> str:
        """
        Get the type of a log variable by name.

        Args:
            name: Log variable name

        Returns:
            Type as string (e.g., "u8", "i16", "f32")
        """
        ...

    def create_block(self) -> LogBlock:
        """
        Create a new log block for streaming telemetry data.

        Returns:
            A new LogBlock instance that can have variables added to it
        """
        ...

class LogBlock:
    """Log block for collecting telemetry data"""

    def add_variable(self, name: str) -> None:
        """
        Add a variable to the log block.

        Args:
            name: Variable name (e.g., "stateEstimate.roll")
        """
        ...

    def start(self, period_ms: int) -> LogStream:
        """
        Start streaming data from this log block.

        Args:
            period_ms: Sampling period in milliseconds (10-2550)

        Returns:
            A LogStream for reading data
        """
        ...

class LogStream:
    """Active log stream returning telemetry data"""

    def next(self) -> dict:
        """
        Get the next data sample from the stream.

        Returns:
            Dictionary with two keys:
            - 'timestamp' (int): Sample timestamp in milliseconds
            - 'data' (dict[str, int | float]): Variable names mapped to their values
        """
        ...

    def stop(self) -> LogBlock:
        """
        Stop the log stream and return the log block.

        Returns:
            The original LogBlock that can be restarted
        """
        ...
