//! Platform subsystem - query device information and firmware details

use pyo3::prelude::*;
use pyo3_stub_gen_derive::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::error::to_pyerr;

/// Access to platform services
///
/// The platform CRTP port hosts a couple of utility services. This range from fetching the version of the firmware
/// and CRTP protocol, communication with apps using the App layer to setting the continuous wave radio mode for
/// radio testing.
#[gen_stub_pyclass]
#[pyclass]
pub struct Platform {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
}

#[gen_stub_pymethods]
#[pymethods]
impl Platform {
    /// Fetch the protocol version from the Crazyflie
    ///
    /// The protocol version is updated when new message or breaking change are
    /// implemented in the protocol.
    /// Compatibility is checked at connection time.
    fn get_protocol_version(&self) -> PyResult<u8> {
        self.runtime.block_on(async {
            self.cf.platform.protocol_version().await
        }).map_err(to_pyerr)
    }

    /// Fetch the firmware version
    ///
    /// If this firmware is a stable release, the release name will be returned for example ```2021.06```.
    /// If this firmware is a git build, between releases, the number of commit since the last release will be added
    /// for example ```2021.06 +128```.
    fn get_firmware_version(&self) -> PyResult<String> {
        self.runtime.block_on(async {
            self.cf.platform.firmware_version().await
        }).map_err(to_pyerr)
    }

    /// Fetch the device type.
    ///
    /// The Crazyflie firmware can run on multiple device. This function returns the name of the device. For example
    /// ```Crazyflie 2.1``` is returned in the case of a Crazyflie 2.1.
    fn get_device_type_name(&self) -> PyResult<String> {
        self.runtime.block_on(async {
            self.cf.platform.device_type_name().await
        }).map_err(to_pyerr)
    }

    /// Set radio in continuous wave mode
    ///
    /// If activate is set to true, the Crazyflie's radio will transmit a continuous wave at the current channel
    /// frequency. This will be active until the Crazyflie is reset or this function is called with activate to false.
    ///
    /// Setting continuous wave will:
    ///  - Disconnect the radio link. So this function should practically only be used when connected over USB
    ///  - Jam any radio running on the same frequency, this includes Wifi and Bluetooth
    ///
    /// As such, this shall only be used for test purpose in a controlled environment.
    fn set_continuous_wave(&self, activate: bool) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.platform.set_cont_wave(activate).await
        }).map_err(to_pyerr)
    }

    /// Send system arm/disarm request
    ///
    /// Arms or disarms the Crazyflie's safety systems. When disarmed, the motors
    /// will not spin even if thrust commands are sent.
    ///
    /// # Arguments
    /// * `do_arm` - true to arm, false to disarm
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
