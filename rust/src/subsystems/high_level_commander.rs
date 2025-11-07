//! # High-level commander subsystem
//!
//! This subsystem is responsible for managing high-level commands and setpoints for the Crazyflie.
//! It builds on top of the (low-level) [`crate::subsystems::commander::Commander`] subsystem and provides a more user-friendly interface
//! for controlling the drone's behavior.

use pyo3::prelude::*;
use pyo3_stub_gen::derive::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::error::to_pyerr;


#[gen_stub_pyclass]
#[pyclass]
pub struct HighLevelCommander {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
}

#[gen_stub_pymethods]
#[pymethods]
impl HighLevelCommander {
    /// Set the group mask for the high-level commander.
    ///
    /// # Arguments
    /// * `group_mask` - The group mask to set. Use `ALL_GROUPS` to set the mask for all Crazyflies.
    fn set_group_mask(&self, group_mask: u8) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.high_level_commander.set_group_mask(group_mask).await
        }).map_err(to_pyerr)?;
        Ok(())
    }

    /// Take off vertically from the current x-y position to the given target height.
    ///
    /// # Arguments
    /// * `height` - Target height (meters) above the world origin.
    /// * `yaw` - Target yaw (radians). Use `None` to maintain the current yaw.
    /// * `duration` - Time (seconds) to reach the target height. This method blocks for this duration.
    /// * `group_mask` - Bitmask selecting which Crazyflies to command. Use `None` for all Crazyflies.
    fn take_off(&self, height: f32, yaw: Option<f32>, duration: f32, group_mask: Option<u8>) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.high_level_commander.take_off(height, yaw, duration, group_mask).await
        }).map_err(to_pyerr)?;
        Ok(())
    }
}