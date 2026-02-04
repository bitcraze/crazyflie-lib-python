//! # Memory subsystem bindings
//!
//! Provides Python bindings for trajectory memory operations.
//! Trajectory data is built in Python using [`Poly`], [`Poly4D`],
//! [`CompressedStart`], and [`CompressedSegment`], then uploaded
//! via the [`Memory`] subsystem.

use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use pyo3_stub_gen::derive::*;
use std::sync::Arc;

use crate::error::to_pyerr;
use crazyflie_lib::subsystems::memory::MemoryType;

/// A polynomial with up to 8 coefficients.
///
/// Coefficients beyond the provided values are zero-filled.
/// If more than 8 values are provided, only the first 8 are used.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Clone, Debug)]
pub struct Poly {
    /// The polynomial coefficients
    values: Vec<f32>,
}

#[gen_stub_pymethods]
#[pymethods]
impl Poly {
    #[new]
    fn new(values: Vec<f32>) -> Self {
        let mut padded = vec![0.0f32; 8];
        let len = values.len().min(8);
        padded[..len].copy_from_slice(&values[..len]);
        Self { values: padded }
    }

    /// Get the coefficient values as a list
    #[getter]
    fn values(&self) -> Vec<f32> {
        self.values.clone()
    }
}

impl Poly {
    fn to_rust(&self) -> crazyflie_lib::subsystems::memory::Poly {
        crazyflie_lib::subsystems::memory::Poly::from_slice(&self.values)
    }
}

/// An uncompressed 4D polynomial trajectory segment.
///
/// Each segment defines motion along x, y, z, and yaw axes
/// using 8th-order polynomials over a given duration.
/// Packs to 132 bytes.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Clone, Debug)]
pub struct Poly4D {
    duration: f32,
    x: Poly,
    y: Poly,
    z: Poly,
    yaw: Poly,
}

#[gen_stub_pymethods]
#[pymethods]
impl Poly4D {
    #[new]
    fn new(duration: f32, x: Poly, y: Poly, z: Poly, yaw: Poly) -> Self {
        Self { duration, x, y, z, yaw }
    }

    /// Duration of this segment in seconds
    #[getter]
    fn duration(&self) -> f32 {
        self.duration
    }

    /// X polynomial
    #[getter]
    fn x(&self) -> Poly {
        self.x.clone()
    }

    /// Y polynomial
    #[getter]
    fn y(&self) -> Poly {
        self.y.clone()
    }

    /// Z polynomial
    #[getter]
    fn z(&self) -> Poly {
        self.z.clone()
    }

    /// Yaw polynomial
    #[getter]
    fn yaw(&self) -> Poly {
        self.yaw.clone()
    }
}

impl Poly4D {
    fn to_rust(&self) -> crazyflie_lib::subsystems::memory::Poly4D {
        crazyflie_lib::subsystems::memory::Poly4D::new(
            self.duration,
            self.x.to_rust(),
            self.y.to_rust(),
            self.z.to_rust(),
            self.yaw.to_rust(),
        )
    }
}

/// Starting point for a compressed trajectory.
///
/// Defines the initial position (x, y, z in meters) and yaw (radians).
/// Spatial range: approximately ±32.767 meters.
/// Packs to 8 bytes.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Clone, Debug)]
pub struct CompressedStart {
    /// X coordinate in meters
    #[pyo3(get)]
    x: f32,
    /// Y coordinate in meters
    #[pyo3(get)]
    y: f32,
    /// Z coordinate in meters
    #[pyo3(get)]
    z: f32,
    /// Yaw angle in radians
    #[pyo3(get)]
    yaw: f32,
}

#[gen_stub_pymethods]
#[pymethods]
impl CompressedStart {
    #[new]
    fn new(x: f32, y: f32, z: f32, yaw: f32) -> Self {
        Self { x, y, z, yaw }
    }
}

impl CompressedStart {
    fn to_rust(&self) -> crazyflie_lib::subsystems::memory::CompressedStart {
        crazyflie_lib::subsystems::memory::CompressedStart::new(self.x, self.y, self.z, self.yaw)
    }
}

/// A segment in a compressed trajectory.
///
/// Each axis can have 0, 1, 3, or 7 polynomial coefficients.
/// Spatial values are encoded as millimeters (±32.767m range).
/// Yaw values are encoded as 1/10th degrees.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Clone, Debug)]
pub struct CompressedSegment {
    /// Duration of this segment in seconds
    #[pyo3(get)]
    duration: f32,
    /// X polynomial coefficients (0, 1, 3, or 7 elements)
    #[pyo3(get)]
    x: Vec<f32>,
    /// Y polynomial coefficients (0, 1, 3, or 7 elements)
    #[pyo3(get)]
    y: Vec<f32>,
    /// Z polynomial coefficients (0, 1, 3, or 7 elements)
    #[pyo3(get)]
    z: Vec<f32>,
    /// Yaw polynomial coefficients (0, 1, 3, or 7 elements)
    #[pyo3(get)]
    yaw: Vec<f32>,
}

#[gen_stub_pymethods]
#[pymethods]
impl CompressedSegment {
    /// Create a new compressed segment.
    ///
    /// Each element list must have 0, 1, 3, or 7 values.
    #[new]
    fn new(duration: f32, x: Vec<f32>, y: Vec<f32>, z: Vec<f32>, yaw: Vec<f32>) -> PyResult<Self> {
        // Validate lengths eagerly so errors are clear
        for (name, v) in [("x", &x), ("y", &y), ("z", &z), ("yaw", &yaw)] {
            let len = v.len();
            if len != 0 && len != 1 && len != 3 && len != 7 {
                return Err(PyValueError::new_err(
                    format!("{} element length must be 0, 1, 3, or 7 (got {})", name, len)
                ));
            }
        }
        Ok(Self { duration, x, y, z, yaw })
    }
}

impl CompressedSegment {
    fn to_rust(&self) -> crazyflie_lib::Result<crazyflie_lib::subsystems::memory::CompressedSegment> {
        crazyflie_lib::subsystems::memory::CompressedSegment::new(
            self.duration,
            self.x.clone(),
            self.y.clone(),
            self.z.clone(),
            self.yaw.clone(),
        )
    }
}

/// Memory subsystem wrapper.
///
/// Provides methods to upload trajectory data to the Crazyflie.
/// Access via `cf.memory()`.
#[gen_stub_pyclass]
#[pyclass]
pub struct Memory {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
}

#[gen_stub_pymethods]
#[pymethods]
impl Memory {
    /// Write an uncompressed (Poly4D) trajectory to the Crazyflie.
    ///
    /// Opens the trajectory memory, writes all segments, and closes
    /// the memory. Returns the number of bytes written.
    ///
    /// # Arguments
    /// * `trajectory` - List of Poly4D segments to upload
    /// * `start_addr` - Address in trajectory memory (default 0)
    #[pyo3(signature = (trajectory, start_addr=0))]
    #[gen_stub(override_return_type(type_repr = "collections.abc.Coroutine[typing.Any, typing.Any, int]"))]
    fn write_trajectory<'py>(
        &self,
        py: Python<'py>,
        trajectory: Vec<Poly4D>,
        start_addr: usize,
    ) -> PyResult<Bound<'py, PyAny>> {
        let cf = self.cf.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            // Convert Python types to Rust types
            let rust_segments: Vec<crazyflie_lib::subsystems::memory::Poly4D> =
                trajectory.iter().map(|s| s.to_rust()).collect();

            // Find trajectory memory
            let memories = cf.memory.get_memories(Some(MemoryType::Trajectory));
            let mem_device = (*memories.first()
                .ok_or_else(|| to_pyerr(crazyflie_lib::Error::MemoryError(
                    "No trajectory memory found on Crazyflie".to_owned()
                )))?)
                .clone();

            // Open, write, close
            let traj_mem: crazyflie_lib::subsystems::memory::TrajectoryMemory =
                cf.memory.open_memory(mem_device).await
                    .ok_or_else(|| to_pyerr(crazyflie_lib::Error::MemoryError(
                        "Failed to open trajectory memory".to_owned()
                    )))?
                    .map_err(to_pyerr)?;

            let bytes_written = traj_mem.write_uncompressed(&rust_segments, start_addr).await
                .map_err(to_pyerr)?;

            cf.memory.close_memory(traj_mem).await.map_err(to_pyerr)?;

            Ok(bytes_written)
        })
    }

    /// Write a compressed trajectory to the Crazyflie.
    ///
    /// Opens the trajectory memory, writes the start point followed
    /// by all compressed segments, and closes the memory.
    /// Returns the number of bytes written.
    ///
    /// # Arguments
    /// * `start` - CompressedStart defining the initial position
    /// * `segments` - List of CompressedSegment instances
    /// * `start_addr` - Address in trajectory memory (default 0)
    #[pyo3(signature = (start, segments, start_addr=0))]
    #[gen_stub(override_return_type(type_repr = "collections.abc.Coroutine[typing.Any, typing.Any, int]"))]
    fn write_compressed_trajectory<'py>(
        &self,
        py: Python<'py>,
        start: CompressedStart,
        segments: Vec<CompressedSegment>,
        start_addr: usize,
    ) -> PyResult<Bound<'py, PyAny>> {
        let cf = self.cf.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            // Convert Python types to Rust types
            let rust_start = start.to_rust();
            let rust_segments: Vec<crazyflie_lib::subsystems::memory::CompressedSegment> =
                segments.iter()
                    .map(|s| s.to_rust())
                    .collect::<crazyflie_lib::Result<Vec<_>>>()
                    .map_err(to_pyerr)?;

            // Find trajectory memory
            let memories = cf.memory.get_memories(Some(MemoryType::Trajectory));
            let mem_device = (*memories.first()
                .ok_or_else(|| to_pyerr(crazyflie_lib::Error::MemoryError(
                    "No trajectory memory found on Crazyflie".to_owned()
                )))?)
                .clone();

            // Open memory
            let traj_mem: crazyflie_lib::subsystems::memory::TrajectoryMemory =
                cf.memory.open_memory(mem_device).await
                    .ok_or_else(|| to_pyerr(crazyflie_lib::Error::MemoryError(
                        "Failed to open trajectory memory".to_owned()
                    )))?
                    .map_err(to_pyerr)?;

            // Write compressed trajectory (start point + segments)
            let bytes_written = traj_mem.write_compressed(
                &rust_start,
                &rust_segments,
                start_addr,
            ).await.map_err(to_pyerr)?;

            cf.memory.close_memory(traj_mem).await.map_err(to_pyerr)?;

            Ok(bytes_written)
        })
    }
}
