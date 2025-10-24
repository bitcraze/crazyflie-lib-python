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
}
