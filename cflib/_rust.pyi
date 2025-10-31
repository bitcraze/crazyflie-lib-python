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

    def send_setpoint_rpyt(
        self, roll: float, pitch: float, yaw_rate: float, thrust: int
    ) -> None:
        """
        Sends a Roll, Pitch, Yawrate, and Thrust setpoint to the Crazyflie.

        By default, unless modified by parameters, the arguments are interpreted as:

        Args:
            roll: Desired roll angle (degrees)
            pitch: Desired pitch angle (degrees)
            yaw_rate: Desired yaw rate (degrees/second)
            thrust: Thrust as a 16-bit value (0 = 0% thrust, 65535 = 100% thrust)

        Note:
            Thrust is locked by default for safety. To unlock, send a setpoint with
            thrust = 0 once before sending nonzero thrust values.
        """
        ...

    def send_setpoint_position(self, x: float, y: float, z: float, yaw: float) -> None:
        """
        Sends an absolute position setpoint in world coordinates, with yaw as an absolute orientation.

        Args:
            x: Target x position (meters, world frame)
            y: Target y position (meters, world frame)
            z: Target z position (meters, world frame)
            yaw: Target yaw angle (degrees, absolute)
        """
        ...

    def send_setpoint_velocity_world(
        self, vx: float, vy: float, vz: float, yawrate: float
    ) -> None:
        """
        Sends a velocity setpoint in the world frame, with yaw rate control.

        Args:
            vx: Target velocity in x (meters/second, world frame)
            vy: Target velocity in y (meters/second, world frame)
            vz: Target velocity in z (meters/second, world frame)
            yawrate: Target yaw rate (degrees/second)
        """
        ...

    def send_setpoint_zdistance(
        self, roll: float, pitch: float, yawrate: float, zdistance: float
    ) -> None:
        """
        Sends a setpoint with absolute height (distance to the surface below), roll, pitch, and yaw rate commands.

        Args:
            roll: Desired roll angle (degrees)
            pitch: Desired pitch angle (degrees)
            yawrate: Desired yaw rate (degrees/second)
            zdistance: Target height above ground (meters)
        """
        ...

    def send_setpoint_hover(
        self, vx: float, vy: float, yawrate: float, zdistance: float
    ) -> None:
        """
        Sends a setpoint with absolute height (distance to the surface below), and x/y velocity commands in the body-fixed frame.

        Args:
            vx: Target velocity in x (meters/second, body frame)
            vy: Target velocity in y (meters/second, body frame)
            yawrate: Target yaw rate (degrees/second)
            zdistance: Target height above ground (meters)
        """
        ...

    def send_setpoint_manual(
        self,
        roll: float,
        pitch: float,
        yawrate: float,
        thrust_percentage: float,
        rate: bool,
    ) -> None:
        """
        Sends a manual control setpoint for roll, pitch, yaw rate, and thrust percentage.

        If rate is false, roll and pitch are interpreted as angles (degrees).
        If rate is true, they are interpreted as rates (degrees/second).

        Args:
            roll: Desired roll (degrees or degrees/second, depending on rate)
            pitch: Desired pitch (degrees or degrees/second, depending on rate)
            yawrate: Desired yaw rate (degrees/second)
            thrust_percentage: Thrust as a percentage (0 to 100)
            rate: If true, use rate mode; if false, use angle mode
        """
        ...

    def send_stop_setpoint(self) -> None:
        """Sends a STOP setpoint, immediately stopping the motors. The Crazyflie will lose lift and may fall."""
        ...

    def send_notify_setpoint_stop(self, remain_valid_milliseconds: int) -> None:
        """
        Notify the firmware that low-level setpoints have stopped.

        This tells the Crazyflie to drop the current low-level setpoint priority,
        allowing the High-level commander (or other sources) to take control again.

        Args:
            remain_valid_milliseconds: How long (in ms) the last low-level setpoint
                should remain valid before it is considered stale. Use 0 to make the
                hand-off immediate; small non-zero values can smooth transitions if needed.
        """
        ...

class Console:
    """
    Access to the console subsystem

    The Crazyflie has a text console that is used to communicate various information
    and debug message to the ground.
    """

    def get_lines(self) -> list[str]:
        """
        Get console lines as they arrive

        This function returns console lines line-by-line. It buffers lines internally
        and returns up to 100 lines per call with a 10ms timeout per line.

        The lib keeps track of the console history since connection, so the first
        call to this function will return all lines received since connection.

        Returns:
            List of console output lines (up to 100 with 10ms timeout)
        """
        ...

class Param:
    """
    Access to the Crazyflie Param Subsystem

    This struct provide methods to interact with the parameter subsystem.

    The Crazyflie exposes a param subsystem that allows to easily declare parameter
    variables in the Crazyflie and to discover, read and write them from the ground.

    Variables are defined in a table of content that is downloaded upon connection.
    Each param variable have a unique name composed from a group and a variable name.
    Functions that accesses variables, take a `name` parameter that accepts a string
    in the format "group.variable"

    During connection, the full param table of content is downloaded form the
    Crazyflie as well as the values of all the variable. If a variable value
    is modified by the Crazyflie during runtime, it sends a packet with the new
    value which updates the local value cache.
    """

    def names(self) -> list[str]:
        """
        Get the names of all the parameters

        The names contain group and name of the parameter variable formatted as
        "group.name".
        """
        ...

    def get(self, name: str) -> int | float:
        """
        Get param value

        Get value of a parameter. This function takes the value from a local
        cache and so is quick.

        Args:
            name: Parameter name in format "group.name"

        Returns:
            Parameter value (int or float depending on parameter type)
        """
        ...

    def set(self, name: str, value: float) -> None:
        """
        Set a parameter from a f64 potentially loosing data

        This function is a forgiving version of set. It allows
        to set any parameter of any type from a numeric value. This allows to set
        parameters without caring about the type and risking a type mismatch
        runtime error. Since there is no type or value check, loss of information
        can happen when using this function.

        Loss of information can happen in the following cases:
         - When setting an integer, the value is truncated to the number of bit of the parameter
           - Example: Setting `257` to a `u8` variable will set it to the value `1`
         - Similarly floating point precision will be truncated to the parameter precision. Rounding is undefined.
         - Setting a floating point outside the range of the parameter is undefined.
         - It is not possible to represent accurately a `u64` parameter in a `f64`.

        Returns an error if the param does not exists.

        Args:
            name: Parameter name in format "group.name"
            value: New parameter value
        """
        ...

class Platform:
    """
    Access to platform services

    The platform CRTP port hosts a couple of utility services. This range from fetching the version of the firmware
    and CRTP protocol, communication with apps using the App layer to setting the continuous wave radio mode for
    radio testing.
    """

    def get_protocol_version(self) -> int:
        """
        Fetch the protocol version from Crazyflie

        The protocol version is updated when new message or breaking change are
        implemented in the protocol.
        Compatibility is checked at connection time.
        """
        ...

    def get_firmware_version(self) -> str:
        """
        Fetch the firmware version

        If this firmware is a stable release, the release name will be returned for example ```2021.06```.
        If this firmware is a git build, between releases, the number of commit since the last release will be added
        for example ```2021.06 +128```.
        """
        ...

    def get_device_type_name(self) -> str:
        """
        Fetch the device type.

        The Crazyflie firmware can run on multiple device. This function returns the name of the device. For example
        ```Crazyflie 2.1``` is returned in the case of a Crazyflie 2.1.
        """
        ...

    def set_continuous_wave(self, activate: bool) -> None:
        """
        Set radio in continious wave mode

        If activate is set to true, the Crazyflie's radio will transmit a continious wave at the current channel
        frequency. This will be active until the Crazyflie is reset or this function is called with activate to false.

        Setting continious wave will:
         - Disconnect the radio link. So this function should practically only be used when connected over USB
         - Jam any radio running on the same frequency, this includes Wifi and Bluetooth

        As such, this shall only be used for test purpose in a controlled environment.

        Args:
            activate: If True, transmit continuous wave; if False, disable
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
    """
    Access to the Crazyflie Log Subsystem

    This struct provide functions to interact with the Crazyflie Log subsystem.
    """

    def names(self) -> list[str]:
        """
        Get the names of all the log variables

        The names contain group and name of the log variable formatted as
        "group.name".
        """
        ...

    def get_type(self, name: str) -> str:
        """
        Return the type of a log variable or an Error if the parameter does not exist.

        Args:
            name: Log variable name

        Returns:
            Type as string (e.g., "u8", "i16", "f32")
        """
        ...

    def create_block(self) -> LogBlock:
        """
        Create a Log block

        This will create a log block in the Crazyflie firmware and return a
        LogBlock object that can be used to add variable to the block and start
        logging

        This function can fail if there is no more log block ID available: each
        log block is assigned a 8 bit ID by the lib and so far they are not
        re-used. So during a Crazyflie connection lifetime, up to 256 log
        blocks can be created. If this becomes a problem for any use-case, it
        can be solved by a more clever ID generation algorithm.

        The Crazyflie firmware also has a limit in number of active log block,
        this function will fail if this limit is reached. Unlike for the ID, the
        active log blocks in the Crazyflie are cleaned-up when the LogBlock
        object is dropped.

        Returns:
            A new LogBlock instance that can have variables added to it
        """
        ...

class LogBlock:
    """
    Log Block

    This object represent an IDLE LogBlock in the Crazyflie.

    If the LogBlock object is dropped or its associated LogStream, the
    Log Block will be deleted in the Crazyflie freeing resources.
    """

    def add_variable(self, name: str) -> None:
        """
        Add a variable to the log block

        A packet will be sent to the Crazyflie to add the variable. The variable is logged in the same format as
        it is stored in the Crazyflie (ie. there is no conversion done)

        This function can fail if the variable is not found in the toc or of the Crazyflie returns an error
        The most common error reported by the Crazyflie would be if the log block is already too full.

        Args:
            name: Variable name (e.g., "stateEstimate.roll")
        """
        ...

    def start(self, period_ms: int) -> LogStream:
        """
        Start log block and return a stream to read the value

        Since a log-block cannot be modified after being started, this function
        consumes the LogBlock object and return a LogStream. The function
        LogStream.stop() can be called on the LogStream to get back the LogBlock object.

        This function can fail if there is a protocol error or an error
        reported by the Crazyflie. In such case, the LogBlock object will be
        dropped and the block will be deleted in the Crazyflie

        Args:
            period_ms: Sampling period in milliseconds (10-2550)

        Returns:
            A LogStream for reading data
        """
        ...

class LogStream:
    """
    Log Stream

    This object represents a started log block that is currently returning data
    at regular intervals.

    Dropping this object or the associated LogBlock will delete the log block
    in the Crazyflie.
    """

    def next(self) -> dict:
        """
        Get the next log data from the log block stream

        This function will wait for the data and only return a value when the
        next data is available.

        This function will return an error if the Crazyflie gets disconnected.

        Returns:
            Dictionary with two keys:
            - 'timestamp' (int): Sample timestamp in milliseconds
            - 'data' (dict[str, int | float]): Variable names mapped to their values
        """
        ...

    def stop(self) -> LogBlock:
        """
        Stops the log block from streaming

        This method consumes the stream and returns back the log block object so that it can be started again later
        with a different period.

        This function can only fail on unexpected protocol error. If it does, the log block is dropped and will be
        cleaned-up next time a log block is created.

        Returns:
            The original LogBlock that can be restarted
        """
        ...
