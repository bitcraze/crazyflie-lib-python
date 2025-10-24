//! Platform subsystem - query device information and firmware details

use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::error::to_pyerr;

/// Platform subsystem wrapper
#[pyclass]
pub struct Platform {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
}

#[pymethods]
impl Platform {
    /// Get platform protocol version
    fn get_protocol_version(&self) -> PyResult<u8> {
        self.runtime.block_on(async {
            self.cf.platform.protocol_version().await
        }).map_err(to_pyerr)
    }

    /// Get firmware version string
    fn get_firmware_version(&self) -> PyResult<String> {
        self.runtime.block_on(async {
            self.cf.platform.firmware_version().await
        }).map_err(to_pyerr)
    }

    /// Get device type name
    fn get_device_type_name(&self) -> PyResult<String> {
        self.runtime.block_on(async {
            self.cf.platform.device_type_name().await
        }).map_err(to_pyerr)
    }

    /// Set radio in continuous wave mode
    ///
    /// Args:
    ///     activate: If True, transmit continuous wave; if False, disable
    ///
    /// Warning:
    ///     - Will disconnect the radio link (use over USB)
    ///     - Will jam nearby radios including WiFi/Bluetooth
    ///     - For testing purposes only in controlled environments
    fn set_continuous_wave(&self, activate: bool) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.platform.set_cont_wave(activate).await
        }).map_err(to_pyerr)
    }

    /// Send system arm/disarm request
    ///
    /// Arms or disarms the Crazyflie's safety systems. When disarmed,
    /// motors will not spin even if thrust commands are sent.
    ///
    /// Args:
    ///     do_arm: True to arm, False to disarm
    fn send_arming_request(&self, do_arm: bool) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.platform.send_arming_request(do_arm).await
        }).map_err(to_pyerr)
    }

    /// Send crash recovery request
    ///
    /// Requests recovery from a crash state detected by the Crazyflie.
    fn send_crash_recovery_request(&self) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.platform.send_crash_recovery_request().await
        }).map_err(to_pyerr)
    }
}
