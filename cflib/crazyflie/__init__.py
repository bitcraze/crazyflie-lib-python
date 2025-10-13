#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2025 Bitcraze AB
#
#  Crazyflie Nano Quadcopter Client
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
The Crazyflie module - Rust-powered implementation with backwards compatible API.

This maintains the same API as the old Python implementation but uses Rust under the hood
for performance and reliability.
"""
import logging

from cflib._rust import Crazyflie as RustCrazyflie
from cflib.utils.callbacks import Caller

__author__ = 'Bitcraze AB'
__all__ = ['Crazyflie']

logger = logging.getLogger(__name__)


class State:
    """State of the connection procedure"""
    DISCONNECTED = 0
    INITIALIZED = 1
    CONNECTED = 2
    SETUP_FINISHED = 3


class Crazyflie:
    """
    The Crazyflie class - backwards compatible API with Rust implementation.

    This maintains API compatibility with the old Python implementation while
    using Rust for all the heavy lifting (link, subsystems, protocol).

    Supports both old and new connection styles:

    Old style:
        >>> cf = Crazyflie()
        >>> cf.open_link("radio://0/80/2M/E7E7E7E7E7")
        >>> # ... use cf ...
        >>> cf.close_link()

    New style:
        >>> with Crazyflie(link_uri="radio://0/80/2M/E7E7E7E7E7") as cf:
        ...     # ... use cf ...
    """

    def __init__(self, link=None, ro_cache=None, rw_cache=None, link_uri=None):
        """
        Create a Crazyflie object.

        Args:
            link: Deprecated, not used (Rust handles links)
            ro_cache: Deprecated, not used (Rust handles TOC caching)
            rw_cache: Deprecated, not used (Rust handles TOC caching)
            link_uri: Optional URI to connect immediately (new style)
        """
        # Callbacks for backwards compatibility
        # assert(0)
        self.disconnected = Caller()
        self.connection_lost = Caller()
        self.link_established = Caller()
        self.connection_requested = Caller()
        self.connected = Caller()
        self.fully_connected = Caller()
        self.connection_failed = Caller()

        # State management
        self.state = State.DISCONNECTED
        self.link_uri = ''
        self.connected_ts = None

        # Rust backend
        self._rust_cf = None
        self._commander = None
        self._param = None
        self._console = None
        self._platform = None

        # New style: connect immediately if URI provided
        if link_uri:
            self.open_link(link_uri)

    def open_link(self, link_uri):
        """
        Open the communication link to a Crazyflie at the given URI.

        This connects to the Crazyflie and initializes all subsystems.

        Args:
            link_uri: URI string (e.g., "radio://0/80/2M/E7E7E7E7E7")
        """
        self.connection_requested.call(link_uri)
        self.state = State.INITIALIZED
        self.link_uri = link_uri

        logger.info('Connecting to %s', link_uri)

        try:
            # Connect via Rust
            self._rust_cf = RustCrazyflie.connect_from_uri(link_uri)

            # Update state
            self.state = State.CONNECTED
            self.link_established.call(link_uri)

            # Import datetime here to avoid issues if not available
            import datetime
            self.connected_ts = datetime.datetime.now()

            # Call callbacks
            self.connected.call(link_uri)
            self.fully_connected.call(link_uri)

            logger.info('Connected to %s', link_uri)

        except Exception as ex:
            logger.error('Connection failed: %s', ex)
            self._rust_cf = None
            self.state = State.DISCONNECTED
            self.connection_failed.call(link_uri, str(ex))
            raise

    def close_link(self):
        """Close the communication link."""
        logger.info('Closing link to %s', self.link_uri)

        if self._rust_cf is not None:
            try:
                # Send stop setpoint for safety
                self.commander.send_stop_setpoint()
            except Exception:
                pass  # Ignore errors during shutdown

            self._rust_cf.disconnect()
            self._rust_cf = None

        self.disconnected.call(self.link_uri)
        self.state = State.DISCONNECTED
        self.connected_ts = None

    def disconnect(self):
        """Alias for close_link() for new-style API."""
        self.close_link()

    def is_connected(self):
        """Check if connected to a Crazyflie."""
        return self.connected_ts is not None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatically disconnect."""
        if self.is_connected():
            self.close_link()
        return False

    # Subsystem properties with lazy initialization

    @property
    def commander(self):
        """Get the commander subsystem."""
        if self._rust_cf is None:
            raise RuntimeError('Not connected. Call open_link() first.')
        if self._commander is None:
            self._commander = self._rust_cf.commander()
        return self._commander

    @property
    def param(self):
        """Get the parameter subsystem."""
        if self._rust_cf is None:
            raise RuntimeError('Not connected. Call open_link() first.')
        if self._param is None:
            self._param = self._rust_cf.param()
        return self._param

    @property
    def console(self):
        """Get the console subsystem."""
        if self._rust_cf is None:
            raise RuntimeError('Not connected. Call open_link() first.')
        if self._console is None:
            self._console = self._rust_cf.console()
        return self._console

    @property
    def platform(self):
        """Get the platform subsystem."""
        if self._rust_cf is None:
            raise RuntimeError('Not connected. Call open_link() first.')
        if self._platform is None:
            self._platform = self._rust_cf.platform()
        return self._platform

    # Subsystems not yet implemented in Rust

    @property
    def log(self):
        """Get the log subsystem (not yet implemented in Rust)."""
        raise NotImplementedError(
            'Log subsystem not yet implemented in Rust. '
            'Coming soon!'
        )

    @property
    def mem(self):
        """Get the memory subsystem (not yet implemented in Rust)."""
        raise NotImplementedError(
            'Memory subsystem not yet implemented in Rust. '
            'Coming soon!'
        )

    @property
    def high_level_commander(self):
        """Get the high-level commander (not yet implemented in Rust)."""
        raise NotImplementedError(
            'High-level commander not yet implemented in Rust. '
            'Coming soon!'
        )

    @property
    def loc(self):
        """Get the localization subsystem (not yet implemented in Rust)."""
        raise NotImplementedError(
            'Localization subsystem not yet implemented in Rust. '
            'Coming soon!'
        )

    @property
    def extpos(self):
        """Get the external position subsystem (not yet implemented in Rust)."""
        raise NotImplementedError(
            'External position subsystem not yet implemented in Rust. '
            'Coming soon!'
        )

    @property
    def appchannel(self):
        """Get the app channel subsystem (not yet implemented in Rust)."""
        raise NotImplementedError(
            'App channel subsystem not yet implemented in Rust. '
            'Coming soon!'
        )

    # Deprecated methods that don't make sense with Rust backend
    # But kept for API compatibility

    def send_packet(self, pk, expected_reply=(), resend=False, timeout=0.2):
        """
        Deprecated: Direct packet sending not supported with Rust backend.

        Use the subsystem methods instead (commander, param, etc.)
        """
        raise NotImplementedError(
            'Direct packet sending not supported with Rust backend. '
            'Use subsystem methods instead: cf.commander.send_setpoint(), etc.'
        )

    def add_port_callback(self, port, cb):
        """Deprecated: Port callbacks not supported with Rust backend."""
        raise NotImplementedError(
            'Port callbacks not supported with Rust backend.'
        )

    def remove_port_callback(self, port, cb):
        """Deprecated: Port callbacks not supported with Rust backend."""
        raise NotImplementedError(
            'Port callbacks not supported with Rust backend.'
        )
