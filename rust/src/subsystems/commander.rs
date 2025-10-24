//! Commander subsystem - send control setpoints to the Crazyflie

use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::error::to_pyerr;

/// Commander subsystem wrapper
#[pyclass]
pub struct Commander {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
}

#[pymethods]
impl Commander {
    /// Send a setpoint with roll, pitch, yaw rate, and thrust
    ///
    /// Args:
    ///     roll: Roll in degrees
    ///     pitch: Pitch in degrees
    ///     yaw_rate: Yaw rate in degrees/second
    ///     thrust: Thrust (0-65535)
    fn send_setpoint(&self, roll: f32, pitch: f32, yaw_rate: f32, thrust: u16) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.commander.setpoint_rpyt(roll, pitch, yaw_rate, thrust).await
        }).map_err(to_pyerr)?;
        Ok(())
    }

    /// Send a stop command (sets all values to 0)
    fn send_stop_setpoint(&self) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.commander.setpoint_stop().await
        }).map_err(to_pyerr)?;
        Ok(())
    }
}
