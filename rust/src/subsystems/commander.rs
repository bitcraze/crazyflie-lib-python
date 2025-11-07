//! # Commander subsystem
//!
//! This subsystem allows to send low-level setpoint. The setpoints are described as low-level in the sense that they
//! are setting the instant target state. As such they need to be sent very often to have the crazyflie
//! follow the wanted flight profile.
//!
//! The Crazyflie has a couple of safety mechanisms that one needs to be aware of in order to send setpoints:
//!  - When using the [Commander::setpoint_rpyt()] function, a setpoint with thrust=0 must be sent once to unlock the thrust
//!  - There is a priority for setpoints in the Crazyflie, this allows app and other internal subsystem like the high-level
//!    commander to set setpoints in parallel, only the higher priority setpoint is taken into account.
//!  - In no setpoint are received for 1 seconds, the Crazyflie will reset roll/pitch/yawrate to 0/0/0 and after 2 seconds
//!    will fallback fallback to a lower-priority setpoint which in most case will cut the motors.

use pyo3::prelude::*;
use pyo3_stub_gen::derive::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::error::to_pyerr;

/// Commander subsystem wrapper
#[gen_stub_pyclass]
#[pyclass]
pub struct Commander {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
}

#[gen_stub_pymethods]
#[pymethods]
impl Commander {
    /// Sends a Roll, Pitch, Yawrate, and Thrust setpoint to the Crazyflie.
    ///
    /// By default, unless modified by [parameters](crate::subsystems::param::Param), the arguments are interpreted as:
    /// * `roll` - Desired roll angle (degrees)
    /// * `pitch` - Desired pitch angle (degrees)
    /// * `yawrate` - Desired yaw rate (degrees/second)
    /// * `thrust` - Thrust as a 16-bit value (0 = 0% thrust, 65535 = 100% thrust)
    ///
    /// Note: Thrust is locked by default for safety. To unlock, send a setpoint with `thrust = 0` once before sending nonzero thrust values.
    fn send_setpoint_rpyt(&self, roll: f32, pitch: f32, yaw_rate: f32, thrust: u16) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.commander.setpoint_rpyt(roll, pitch, yaw_rate, thrust).await
        }).map_err(to_pyerr)?;
        Ok(())
    }

    /// Sends an absolute position setpoint in world coordinates, with yaw as an absolute orientation.
    ///
    /// # Arguments
    /// * `x` - Target x position (meters, world frame)
    /// * `y` - Target y position (meters, world frame)
    /// * `z` - Target z position (meters, world frame)
    /// * `yaw` - Target yaw angle (degrees, absolute)
    fn send_setpoint_position(&self, x: f32, y: f32, z: f32, yaw: f32) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.commander.setpoint_position(x, y, z, yaw).await
        }).map_err(to_pyerr)?;
        Ok(())
    }

    /// Sends a velocity setpoint in the world frame, with yaw rate control.
    ///
    /// # Arguments
    /// * `vx` - Target velocity in x (meters/second, world frame)
    /// * `vy` - Target velocity in y (meters/second, world frame)
    /// * `vz` - Target velocity in z (meters/second, world frame)
    /// * `yawrate` - Target yaw rate (degrees/second)
    fn send_setpoint_velocity_world(&self, vx: f32, vy: f32, vz: f32, yawrate: f32) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.commander.setpoint_velocity_world(vx, vy, vz, yawrate).await
        }).map_err(to_pyerr)?;
        Ok(())
    }

    /// Sends a setpoint with absolute height (distance to the surface below), roll, pitch, and yaw rate commands.
    ///
    /// # Arguments
    /// * `roll` - Desired roll angle (degrees)
    /// * `pitch` - Desired pitch angle (degrees)
    /// * `yawrate` - Desired yaw rate (degrees/second)
    /// * `zdistance` - Target height above ground (meters)
    fn send_setpoint_zdistance(&self, roll: f32, pitch: f32, yawrate: f32, zdistance: f32) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.commander.setpoint_zdistance(roll, pitch, yawrate, zdistance).await
        }).map_err(to_pyerr)?;
        Ok(())
    }

    /// Sends a setpoint with absolute height (distance to the surface below), and x/y velocity commands in the body-fixed frame.
    ///
    /// # Arguments
    /// * `vx` - Target velocity in x (meters/second, body frame)
    /// * `vy` - Target velocity in y (meters/second, body frame)
    /// * `yawrate` - Target yaw rate (degrees/second)
    /// * `zdistance` - Target height above ground (meters)
    fn send_setpoint_hover(&self, vx: f32, vy: f32, yawrate: f32, zdistance: f32) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.commander.setpoint_hover(vx, vy, yawrate, zdistance).await
        }).map_err(to_pyerr)?;
        Ok(())
    }

    /// Sends a manual control setpoint for roll, pitch, yaw rate, and thrust percentage.
    ///
    /// If `rate` is false, roll and pitch are interpreted as angles (degrees). If `rate` is true, they are interpreted as rates (degrees/second).
    ///
    /// # Arguments
    /// * `roll` - Desired roll (degrees or degrees/second, depending on `rate`)
    /// * `pitch` - Desired pitch (degrees or degrees/second, depending on `rate`)
    /// * `yawrate` - Desired yaw rate (degrees/second)
    /// * `thrust_percentage` - Thrust as a percentage (0 to 100)
    /// * `rate` - If true, use rate mode; if false, use angle mode
    fn send_setpoint_manual(&self, roll: f32, pitch: f32, yawrate: f32, thrust_percentage: f32, rate: bool) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.commander.setpoint_manual(roll, pitch, yawrate, thrust_percentage, rate).await
        }).map_err(to_pyerr)?;
        Ok(())
    }

    /// Sends a STOP setpoint, immediately stopping the motors. The Crazyflie will lose lift and may fall.
    fn send_stop_setpoint(&self) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.commander.setpoint_stop().await
        }).map_err(to_pyerr)?;
        Ok(())
    }

    /// Notify the firmware that low-level setpoints have stopped.
    ///
    /// This tells the Crazyflie to drop the current low-level setpoint priority,
    /// allowing the High-level commander (or other sources) to take control again.
    ///
    /// # Arguments
    /// * `remain_valid_milliseconds` - How long (in ms) the last low-level setpoint
    ///   should remain valid before it is considered stale. Use `0` to make the
    ///   hand-off immediate; small non-zero values can smooth transitions if needed.
    fn send_notify_setpoint_stop(&self, remain_valid_milliseconds: u32) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.commander.notify_setpoint_stop(remain_valid_milliseconds).await
        }).map_err(to_pyerr)?;
        Ok(())
    }
}
