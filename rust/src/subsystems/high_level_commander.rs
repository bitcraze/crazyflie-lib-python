//! # High-level commander subsystem
//!
//! This subsystem is responsible for managing high-level commands and setpoints for the Crazyflie.
//! It builds on top of the (low-level) [`crate::subsystems::commander::Commander`] subsystem and provides a more user-friendly interface
//! for controlling the drone's behavior.

use pyo3::prelude::*;
use pyo3_stub_gen::derive::*;
use std::sync::Arc;

use crate::error::to_pyerr;


/// High-level commander subsystem wrapper
#[gen_stub_pyclass]
#[pyclass]
pub struct HighLevelCommander {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
}

#[gen_stub_pymethods]
#[pymethods]
impl HighLevelCommander {
    /// Set the group mask for the high-level commander.
    ///
    /// # Arguments
    /// * `group_mask` - The group mask to set. Use `ALL_GROUPS` to set the mask for all Crazyflies.
    #[gen_stub(override_return_type(type_repr = "collections.abc.Coroutine[typing.Any, typing.Any, None]"))]
    fn set_group_mask<'py>(&self, py: Python<'py>, group_mask: u8) -> PyResult<Bound<'py, PyAny>> {
        let cf = self.cf.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            cf.high_level_commander.set_group_mask(group_mask).await
                .map_err(to_pyerr)?;
            Ok(())
        })
    }

    /// Take off vertically from the current x-y position to the given target height.
    ///
    /// # Arguments
    /// * `height` - Target height (meters) above the world origin.
    /// * `yaw` - Target yaw (radians). Use `None` to maintain the current yaw.
    /// * `duration` - Time (seconds) to reach the target height.
    /// * `group_mask` - Bitmask selecting which Crazyflies to command. Use `None` for all Crazyflies.
    #[gen_stub(override_return_type(type_repr = "collections.abc.Coroutine[typing.Any, typing.Any, None]"))]
    fn take_off<'py>(&self, py: Python<'py>, height: f32, yaw: Option<f32>, duration: f32, group_mask: Option<u8>) -> PyResult<Bound<'py, PyAny>> {
        let cf = self.cf.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            cf.high_level_commander.take_off(height, yaw, duration, group_mask).await
                .map_err(to_pyerr)?;
            Ok(())
        })
    }

    /// Land vertically from the current x-y position to the given target height.
    ///
    /// # Arguments
    /// * `height` - Target height (meters) above the world origin.
    /// * `yaw` - Target yaw (radians). Use `None` to maintain the current yaw.
    /// * `duration` - Time (seconds) to reach the target height.
    /// * `group_mask` - Bitmask selecting which Crazyflies to command. Use `None` for all Crazyflies.
    #[gen_stub(override_return_type(type_repr = "collections.abc.Coroutine[typing.Any, typing.Any, None]"))]
    fn land<'py>(&self, py: Python<'py>, height: f32, yaw: Option<f32>, duration: f32, group_mask: Option<u8>) -> PyResult<Bound<'py, PyAny>> {
        let cf = self.cf.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            cf.high_level_commander.land(height, yaw, duration, group_mask).await
                .map_err(to_pyerr)?;
            Ok(())
        })
    }

    /// Stop the current high-level command and disable motors.
    ///
    /// This immediately halts any active high-level command (takeoff, land, go_to, spiral,
    /// or trajectory execution) and stops motor output.
    ///
    /// # Arguments
    /// * `group_mask` - Bitmask selecting which Crazyflies to command. Use `None` for all Crazyflies.
    #[gen_stub(override_return_type(type_repr = "collections.abc.Coroutine[typing.Any, typing.Any, None]"))]
    fn stop<'py>(&self, py: Python<'py>, group_mask: Option<u8>) -> PyResult<Bound<'py, PyAny>> {
        let cf = self.cf.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            cf.high_level_commander.stop(group_mask).await
                .map_err(to_pyerr)?;
            Ok(())
        })
    }

    /// Move to an absolute or relative position with smooth path planning.
    ///
    /// The path is designed to transition smoothly from the current state to the target
    /// position, gradually decelerating at the goal with minimal overshoot. When the
    /// system is at hover, the path will be a straight line, but if there is any initial
    /// velocity, the path will be a smooth curve.
    ///
    /// The trajectory is derived by solving for a unique 7th-degree polynomial that
    /// satisfies the initial conditions of position, velocity, and acceleration, and
    /// ends at the goal with zero velocity and acceleration. Additionally, the jerk
    /// (derivative of acceleration) is constrained to be zero at both the starting
    /// and ending points.
    ///
    /// # Arguments
    /// * `x` - Target x-position in meters
    /// * `y` - Target y-position in meters
    /// * `z` - Target z-position in meters
    /// * `yaw` - Target yaw angle in radians
    /// * `duration` - Time in seconds to reach the target position.
    /// * `relative` - If `true`, positions and yaw are relative to current position; if `false`, absolute
    /// * `linear` - If `true`, use linear interpolation; if `false`, use polynomial trajectory
    /// * `group_mask` - Bitmask selecting which Crazyflies to command. Use `None` for all Crazyflies.
    #[gen_stub(override_return_type(type_repr = "collections.abc.Coroutine[typing.Any, typing.Any, None]"))]
    fn go_to<'py>(&self, py: Python<'py>, x: f32, y: f32, z: f32, yaw: f32, duration: f32, relative: bool, linear: bool, group_mask: Option<u8>) -> PyResult<Bound<'py, PyAny>> {
        let cf = self.cf.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            cf.high_level_commander.go_to(x, y, z, yaw, duration, relative, linear, group_mask).await
                .map_err(to_pyerr)?;
            Ok(())
        })
    }

    /// Fly a spiral segment.
    ///
    /// The Crazyflie moves along an arc around a computed center point, sweeping
    /// through an angle of up to ±2π (one full turn). While sweeping, the radius
    /// changes linearly from `initial_radius` to `final_radius`. If the radii are
    /// equal, the path is a circular arc; if they differ, the path spirals inward
    /// or outward accordingly. Altitude changes linearly by `altitude_gain` over
    /// the duration.
    ///
    /// # Center placement
    /// The spiral center is placed differently depending on `sideways` and `clockwise`:
    /// * `sideways = false`
    ///   * `clockwise = true`  → center lies to the **right** of the current heading.
    ///   * `clockwise = false` → center lies to the **left** of the current heading.
    /// * `sideways = true`
    ///   * `clockwise = true`  → center lies **ahead** of the current heading.
    ///   * `clockwise = false` → center lies **behind** the current heading.
    ///
    /// # Orientation
    /// * `sideways = false`: the Crazyflie's heading follows the tangent of the
    ///   spiral (flies forward along the path).
    /// * `sideways = true`: the Crazyflie's heading points toward the spiral center
    ///   while circling around it (flies sideways along the path).
    ///
    /// # Direction conventions
    /// * `clockwise` chooses on which side the center is placed.
    /// * The **sign of `angle`** sets the travel direction along the arc:
    ///   `angle > 0` sweeps one way; `angle < 0` traverses the arc in the opposite
    ///   direction (i.e., "backwards"). This can make some combinations appear
    ///   counterintuitive—for example, `sideways = false`, `clockwise = true`,
    ///   `angle < 0` will *look* counter-clockwise from above.
    ///
    /// # Arguments
    /// * `angle` - Total spiral angle in radians (limited to ±2π).
    /// * `initial_radius` - Starting radius in meters (≥ 0).
    /// * `final_radius` - Ending radius in meters (≥ 0).
    /// * `altitude_gain` - Vertical displacement in meters (positive = climb,
    ///   negative = descent).
    /// * `duration` - Time in seconds to complete the spiral.
    /// * `sideways` - If `true`, heading points toward the spiral center;
    ///   if `false`, heading follows the spiral tangent.
    /// * `clockwise` - If `true`, fly clockwise; otherwise counter-clockwise.
    /// * `group_mask` - Bitmask selecting which Crazyflies this applies to.
    #[gen_stub(override_return_type(type_repr = "collections.abc.Coroutine[typing.Any, typing.Any, None]"))]
    fn spiral<'py>(&self, py: Python<'py>, angle: f32, initial_radius: f32, final_radius: f32, altitude_gain: f32, duration: f32, sideways: bool, clockwise: bool, group_mask: Option<u8>) -> PyResult<Bound<'py, PyAny>> {
        let cf = self.cf.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            cf.high_level_commander.spiral(angle, initial_radius, final_radius, altitude_gain, duration, sideways, clockwise, group_mask).await
                .map_err(to_pyerr)?;
            Ok(())
        })
    }

    /// Define a trajectory previously uploaded to memory.
    ///
    /// # Arguments
    /// * `trajectory_id` - Identifier used to reference this trajectory later.
    /// * `memory_offset` - Byte offset into trajectory memory where the data begins.
    /// * `num_pieces` - Number of segments (pieces) in the trajectory.
    /// * `trajectory_type` - Type of the trajectory data (e.g. Poly4D).
    #[gen_stub(override_return_type(type_repr = "collections.abc.Coroutine[typing.Any, typing.Any, None]"))]
    fn define_trajectory<'py>(&self, py: Python<'py>, trajectory_id: u8, memory_offset: u32, num_pieces: u8, trajectory_type: Option<u8>) -> PyResult<Bound<'py, PyAny>> {
        let cf = self.cf.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            cf.high_level_commander.define_trajectory(trajectory_id, memory_offset, num_pieces, trajectory_type).await
                .map_err(to_pyerr)?;
            Ok(())
        })
    }

    /// Start executing a previously defined trajectory.
    ///
    /// The trajectory is identified by `trajectory_id` and can be modified
    /// at execution time by scaling its speed, shifting its position, aligning
    /// its yaw, or running it in reverse.
    ///
    /// # Arguments
    /// * `trajectory_id` - Identifier of the trajectory (as defined with [`HighLevelCommander::define_trajectory`]).
    /// * `time_scale` - Time scaling factor; `1.0` = original speed,
    ///   values >1.0 slow down, values <1.0 speed up.
    /// * `relative_position` - If `true`, shift trajectory to the current setpoint position.
    /// * `relative_yaw` - If `true`, align trajectory yaw to the current yaw.
    /// * `reversed` - If `true`, execute the trajectory in reverse.
    /// * `group_mask` - Mask selecting which Crazyflies this applies to.
    ///   If `None`, defaults to all Crazyflies.
    #[gen_stub(override_return_type(type_repr = "collections.abc.Coroutine[typing.Any, typing.Any, None]"))]
    fn start_trajectory<'py>(&self, py: Python<'py>, trajectory_id: u8, time_scale: f32, relative_position: bool, relative_yaw: bool, reversed: bool, group_mask: Option<u8>) -> PyResult<Bound<'py, PyAny>> {
        let cf = self.cf.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            cf.high_level_commander.start_trajectory(trajectory_id, time_scale, relative_position, relative_yaw, reversed, group_mask).await
                .map_err(to_pyerr)?;
            Ok(())
        })
    }
}
