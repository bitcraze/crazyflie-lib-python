//! Localization subsystem - emergency stop, external pose, lighthouse, and loco positioning

use pyo3::prelude::*;
use pyo3_stub_gen::derive::*;
use std::sync::Arc;
use tokio::runtime::Runtime;
use futures::stream::Stream;
use std::pin::Pin;

type AngleStream = Pin<Box<dyn Stream<Item = crazyflie_lib::subsystems::localization::LighthouseAngleData> + Send>>;

/// Localization subsystem wrapper
#[gen_stub_pyclass]
#[pyclass]
pub struct Localization {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
}

#[gen_stub_pymethods]
#[pymethods]
impl Localization {
    /// Get the emergency control interface
    fn emergency(&self) -> EmergencyControl {
        EmergencyControl {
            cf: self.cf.clone(),
            runtime: self.runtime.clone(),
        }
    }

    /// Get the external pose interface
    fn external_pose(&self) -> ExternalPose {
        ExternalPose {
            cf: self.cf.clone(),
            runtime: self.runtime.clone(),
        }
    }

    /// Get the lighthouse interface
    fn lighthouse(&self) -> Lighthouse {
        Lighthouse::new(self.cf.clone(), self.runtime.clone())
    }

    /// Get the loco positioning interface
    fn loco_positioning(&self) -> LocoPositioning {
        LocoPositioning {
            cf: self.cf.clone(),
            runtime: self.runtime.clone(),
        }
    }
}

/// Emergency control interface
///
/// Provides emergency stop functionality that immediately stops all motors.
#[gen_stub_pyclass]
#[pyclass]
pub struct EmergencyControl {
    cf: Arc<crazyflie_lib::Crazyflie>,
    runtime: Arc<Runtime>,
}

#[gen_stub_pymethods]
#[pymethods]
impl EmergencyControl {
    /// Send emergency stop command
    ///
    /// Immediately stops all motors and puts the Crazyflie into a locked state.
    /// The drone will require a reboot before it can fly again.
    fn send_emergency_stop(&self) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.localization.emergency.send_emergency_stop().await
        }).map_err(crate::error::to_pyerr)
    }

    /// Send emergency stop watchdog
    ///
    /// Activates/resets a watchdog failsafe that will automatically emergency stop
    /// the drone if this message isn't sent every 1000ms. Once activated by the first
    /// call, you must continue sending this periodically forever or the drone will
    /// automatically emergency stop. Use only if you need automatic failsafe behavior.
    fn send_emergency_stop_watchdog(&self) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.localization.emergency.send_emergency_stop_watchdog().await
        }).map_err(crate::error::to_pyerr)
    }
}

/// External pose interface
///
/// Provides functionality to send external position and pose data from motion
/// capture systems or other external tracking sources to the Crazyflie's
/// onboard state estimator.
#[gen_stub_pyclass]
#[pyclass]
pub struct ExternalPose {
    cf: Arc<crazyflie_lib::Crazyflie>,
    runtime: Arc<Runtime>,
}

#[gen_stub_pymethods]
#[pymethods]
impl ExternalPose {
    /// Send external position (x, y, z) to the Crazyflie
    ///
    /// Updates the Crazyflie's position estimate with 3D position data.
    ///
    /// # Arguments
    /// * `pos` - Position array [x, y, z] in meters
    fn send_external_position(&self, pos: Vec<f32>) -> PyResult<()> {
        if pos.len() != 3 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Position must be a sequence of 3 floats [x, y, z]"
            ));
        }
        let pos_array: [f32; 3] = [pos[0], pos[1], pos[2]];

        self.runtime.block_on(async {
            self.cf.localization.external_pose.send_external_position(pos_array).await
        }).map_err(crate::error::to_pyerr)
    }

    /// Send external pose (position + quaternion) to the Crazyflie
    ///
    /// Updates the Crazyflie's position estimate with full 6DOF pose data.
    /// Includes both position and orientation.
    ///
    /// # Arguments
    /// * `pos` - Position array [x, y, z] in meters
    /// * `quat` - Quaternion array [qx, qy, qz, qw]
    fn send_external_pose(&self, pos: Vec<f32>, quat: Vec<f32>) -> PyResult<()> {
        if pos.len() != 3 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Position must be a sequence of 3 floats [x, y, z]"
            ));
        }
        if quat.len() != 4 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Quaternion must be a sequence of 4 floats [qx, qy, qz, qw]"
            ));
        }

        let pos_array: [f32; 3] = [pos[0], pos[1], pos[2]];
        let quat_array: [f32; 4] = [quat[0], quat[1], quat[2], quat[3]];

        self.runtime.block_on(async {
            self.cf.localization.external_pose.send_external_pose(pos_array, quat_array).await
        }).map_err(crate::error::to_pyerr)
    }
}

/// Lighthouse positioning system interface
///
/// Provides functionality to receive lighthouse sweep angle data and manage
/// lighthouse base station configuration persistence.
#[gen_stub_pyclass]
#[pyclass]
pub struct Lighthouse {
    cf: Arc<crazyflie_lib::Crazyflie>,
    runtime: Arc<Runtime>,
    stream: Arc<tokio::sync::Mutex<Option<AngleStream>>>,
}

impl Lighthouse {
    fn new(cf: Arc<crazyflie_lib::Crazyflie>, runtime: Arc<Runtime>) -> Self {
        Lighthouse {
            cf,
            runtime,
            stream: Arc::new(tokio::sync::Mutex::new(None)),
        }
    }
}

#[gen_stub_pymethods]
#[pymethods]
impl Lighthouse {
    /// Get lighthouse angle measurements as they arrive
    ///
    /// This function returns lighthouse angle data for base stations. It buffers data internally
    /// and returns up to 100 angle measurements per call with a 10ms timeout per measurement.
    ///
    /// To receive angle data, you must first enable the angle stream by setting the parameter
    /// `locSrv.enLhAngleStream` to 1.
    ///
    /// The lib keeps track of angle data since the stream was enabled, so the first
    /// call to this function will return all measurements received since the stream was enabled.
    ///
    /// Returns:
    ///     List of LighthouseAngleData (up to 100 with 10ms timeout)
    fn get_angle_data(&self) -> PyResult<Vec<LighthouseAngleData>> {
        self.runtime.block_on(async {
            use futures::StreamExt;

            let mut stream_guard = self.stream.lock().await;

            // Initialize stream if not already created
            if stream_guard.is_none() {
                let new_stream = self.cf.localization.lighthouse.angle_stream().await;
                *stream_guard = Some(Box::pin(new_stream));
            }

            let stream = stream_guard.as_mut().unwrap();
            let mut angle_data_list = Vec::new();

            // Get up to 100 angle measurements or timeout
            for _ in 0..100 {
                if let Ok(Some(angle_data)) = tokio::time::timeout(
                    std::time::Duration::from_millis(10),
                    stream.next()
                ).await {
                    angle_data_list.push(LighthouseAngleData::from(angle_data));
                } else {
                    break;
                }
            }
            Ok(angle_data_list)
        })
    }

    /// Persist lighthouse geometry and calibration data to permanent storage
    ///
    /// Sends a command to persist lighthouse geometry and/or calibration data
    /// to permanent storage in the Crazyflie, then waits for confirmation.
    /// The geometry and calibration data must have been previously written to
    /// RAM via the memory subsystem.
    ///
    /// # Arguments
    /// * `geo_list` - List of base station IDs (0-15) for which to persist geometry data
    /// * `calib_list` - List of base station IDs (0-15) for which to persist calibration data
    ///
    /// # Returns
    /// * `True` if data was successfully persisted
    /// * `False` if persistence failed
    fn persist_lighthouse_data(&self, geo_list: Vec<u8>, calib_list: Vec<u8>) -> PyResult<bool> {
        self.runtime.block_on(async {
            self.cf.localization.lighthouse.persist_lighthouse_data(&geo_list, &calib_list).await
        }).map_err(crate::error::to_pyerr)
    }
}

/// Lighthouse angle sweep data
#[gen_stub_pyclass]
#[pyclass]
#[derive(Clone)]
pub struct LighthouseAngleData {
    base_station: u8,
    angles: LighthouseAngles,
}

impl From<crazyflie_lib::subsystems::localization::LighthouseAngleData> for LighthouseAngleData {
    fn from(data: crazyflie_lib::subsystems::localization::LighthouseAngleData) -> Self {
        LighthouseAngleData {
            base_station: data.base_station,
            angles: LighthouseAngles::from(data.angles),
        }
    }
}

#[gen_stub_pymethods]
#[pymethods]
impl LighthouseAngleData {
    /// Base station ID
    #[getter]
    fn base_station(&self) -> u8 {
        self.base_station
    }

    /// Angle measurements
    #[getter]
    fn angles(&self) -> LighthouseAngles {
        self.angles.clone()
    }
}

/// Lighthouse sweep angles for all 4 sensors
#[gen_stub_pyclass]
#[pyclass]
#[derive(Clone)]
pub struct LighthouseAngles {
    x: [f32; 4],
    y: [f32; 4],
}

impl From<crazyflie_lib::subsystems::localization::LighthouseAngles> for LighthouseAngles {
    fn from(angles: crazyflie_lib::subsystems::localization::LighthouseAngles) -> Self {
        LighthouseAngles {
            x: angles.x,
            y: angles.y,
        }
    }
}

#[gen_stub_pymethods]
#[pymethods]
impl LighthouseAngles {
    /// Horizontal angles for 4 sensors [rad]
    #[getter]
    fn x(&self) -> Vec<f32> {
        self.x.to_vec()
    }

    /// Vertical angles for 4 sensors [rad]
    #[getter]
    fn y(&self) -> Vec<f32> {
        self.y.to_vec()
    }
}

/// Loco Positioning System (UWB) interface
///
/// Provides functionality to send Loco Positioning Protocol (LPP) packets
/// to ultra-wide-band positioning nodes.
#[gen_stub_pyclass]
#[pyclass]
pub struct LocoPositioning {
    cf: Arc<crazyflie_lib::Crazyflie>,
    runtime: Arc<Runtime>,
}

#[gen_stub_pymethods]
#[pymethods]
impl LocoPositioning {
    /// Send Loco Positioning Protocol (LPP) packet to a specific destination
    ///
    /// # Arguments
    /// * `dest_id` - Destination node ID
    /// * `data` - LPP packet payload
    fn send_short_lpp_packet(&self, dest_id: u8, data: Vec<u8>) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.localization.loco_positioning.send_short_lpp_packet(dest_id, &data).await
        }).map_err(crate::error::to_pyerr)
    }
}
