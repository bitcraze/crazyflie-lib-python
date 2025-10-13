"""
Wrapper module for Rust implementations.

This module provides Python-friendly wrappers around the Rust core implementations.
It maintains API compatibility with the existing cflib while using Rust under the hood.
"""

try:
    from cflib._rust import (
        Crazyflie as RustCrazyflie,
        LinkContext as RustLinkContext,
    )
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    RustCrazyflie = None
    RustLinkContext = None


class CrazyflieRust:
    """
    Python wrapper for the Rust Crazyflie implementation.

    This class provides a more Pythonic interface while delegating
    to the Rust implementation for performance.

    Example:
        >>> from cflib._rust_wrapper import CrazyflieRust
        >>> cf = CrazyflieRust.connect_from_uri("radio://0/80/2M/E7E7E7E7E7")
        >>> print(cf.platform.get_firmware_version())
        >>> cf.disconnect()
    """

    def __init__(self, rust_cf):
        """Initialize with a Rust Crazyflie instance."""
        self._cf = rust_cf
        self._console = None
        self._param = None
        self._commander = None
        self._platform = None

    @classmethod
    def connect_from_uri(cls, uri: str):
        """
        Connect to a Crazyflie from URI.

        Args:
            uri: Connection URI string (e.g., "radio://0/80/2M/E7E7E7E7E7")

        Returns:
            CrazyflieRust: Connected Crazyflie instance

        Raises:
            RuntimeError: If connection fails
        """
        if not RUST_AVAILABLE:
            raise RuntimeError('Rust implementation not available. Build with: pip install -e .')

        rust_cf = RustCrazyflie.connect_from_uri(uri)
        return cls(rust_cf)

    def disconnect(self):
        """Disconnect from the Crazyflie."""
        self._cf.disconnect()

    @property
    def console(self):
        """Get the console subsystem."""
        if self._console is None:
            self._console = self._cf.console()
        return self._console

    @property
    def param(self):
        """Get the parameter subsystem."""
        if self._param is None:
            self._param = self._cf.param()
        return self._param

    @property
    def commander(self):
        """Get the commander subsystem."""
        if self._commander is None:
            self._commander = self._cf.commander()
        return self._commander

    @property
    def platform(self):
        """Get the platform subsystem."""
        if self._platform is None:
            self._platform = self._cf.platform()
        return self._platform


class LinkContextRust:
    """
    Python wrapper for Rust LinkContext.

    Used for scanning and connecting to Crazyflies.

    Example:
        >>> from cflib._rust_wrapper import LinkContextRust
        >>> ctx = LinkContextRust()
        >>> uris = ctx.scan()
        >>> print(f"Found {len(uris)} Crazyflies")
    """

    def __init__(self):
        """Initialize the link context."""
        if not RUST_AVAILABLE:
            raise RuntimeError('Rust implementation not available. Build with: pip install -e .')

        self._ctx = RustLinkContext()

    def scan(self):
        """
        Scan for Crazyflies on the default address.

        Returns:
            list[str]: List of URIs found
        """
        return self._ctx.scan()


# Convenience function
def scan_interfaces():
    """
    Scan for available Crazyflies.

    Returns:
        list[str]: List of URIs found
    """
    if not RUST_AVAILABLE:
        raise RuntimeError('Rust implementation not available. Build with: pip install -e .')

    ctx = LinkContextRust()
    return ctx.scan()
