use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use std::sync::Arc;
use tokio::runtime::Runtime;

// Helper function to convert Rust errors to Python exceptions
fn to_pyerr(err: crazyflie_lib::Error) -> PyErr {
    PyRuntimeError::new_err(format!("Crazyflie error: {:?}", err))
}

/// Wrapper for the Crazyflie struct
///
/// This provides a Python interface to the Rust Crazyflie implementation.
/// Since the Rust library is async, we wrap it with a Tokio runtime.
#[pyclass]
struct Crazyflie {
    inner: Arc<crazyflie_lib::Crazyflie>,
    runtime: Arc<Runtime>,
}

#[pymethods]
impl Crazyflie {
    /// Connect to a Crazyflie from a URI string
    ///
    /// Args:
    ///     uri: Connection URI (e.g., "radio://0/80/2M/E7E7E7E7E7")
    ///
    /// Returns:
    ///     Connected Crazyflie instance
    #[staticmethod]
    fn connect_from_uri(uri: String) -> PyResult<Self> {
        let runtime = Arc::new(Runtime::new().map_err(|e| {
            PyRuntimeError::new_err(format!("Failed to create Tokio runtime: {}", e))
        })?);

        let inner = runtime.block_on(async {
            let link_context = crazyflie_link::LinkContext::new();
            crazyflie_lib::Crazyflie::connect_from_uri(&link_context, &uri).await
        }).map_err(to_pyerr)?;

        Ok(Crazyflie {
            inner: Arc::new(inner),
            runtime,
        })
    }

    /// Disconnect from the Crazyflie
    fn disconnect(&self) -> PyResult<()> {
        self.runtime.block_on(async {
            self.inner.disconnect().await;
            Ok(())
        })
    }

    /// Get the console subsystem
    fn console(&self) -> Console {
        Console {
            cf: self.inner.clone(),
            runtime: self.runtime.clone(),
        }
    }

    /// Get the param subsystem
    fn param(&self) -> Param {
        Param {
            cf: self.inner.clone(),
            runtime: self.runtime.clone(),
        }
    }

    /// Get the commander subsystem
    fn commander(&self) -> Commander {
        Commander {
            cf: self.inner.clone(),
            runtime: self.runtime.clone(),
        }
    }

    /// Get the platform subsystem
    fn platform(&self) -> Platform {
        Platform {
            cf: self.inner.clone(),
            runtime: self.runtime.clone(),
        }
    }
}

/// Console subsystem wrapper
#[pyclass]
struct Console {
    cf: Arc<crazyflie_lib::Crazyflie>,
    runtime: Arc<Runtime>,
}

#[pymethods]
impl Console {
    /// Get console lines as they arrive
    ///
    /// Returns:
    ///     List of console output lines (up to 100 with 10ms timeout)
    fn get_lines(&self) -> PyResult<Vec<String>> {
        // Simplified synchronous version - collects available lines
        self.runtime.block_on(async {
            use futures::StreamExt;
            let mut lines = Vec::new();
            let mut stream = self.cf.console.line_stream().await;

            // Get up to 100 lines or timeout
            for _ in 0..100 {
                if let Ok(Some(line)) = tokio::time::timeout(
                    std::time::Duration::from_millis(10),
                    stream.next()
                ).await {
                    lines.push(line);
                } else {
                    break;
                }
            }
            Ok(lines)
        })
    }
}

/// Parameter subsystem wrapper
#[pyclass]
struct Param {
    cf: Arc<crazyflie_lib::Crazyflie>,
    runtime: Arc<Runtime>,
}

#[pymethods]
impl Param {
    /// Get list of all parameter names
    fn names(&self) -> Vec<String> {
        self.cf.param.names()
    }

    /// Get a parameter value by name
    fn get(&self, name: &str) -> PyResult<Py<PyAny>> {
        Python::attach(|py| {
            let value: crazyflie_lib::Value = self.runtime.block_on(async {
                self.cf.param.get(name).await
            }).map_err(to_pyerr)?;

            // Convert Rust Value to Python object
            Ok(match value {
                crazyflie_lib::Value::U8(v) => v.into_pyobject(py)?.into_any().unbind(),
                crazyflie_lib::Value::U16(v) => v.into_pyobject(py)?.into_any().unbind(),
                crazyflie_lib::Value::U32(v) => v.into_pyobject(py)?.into_any().unbind(),
                crazyflie_lib::Value::U64(v) => v.into_pyobject(py)?.into_any().unbind(),
                crazyflie_lib::Value::I8(v) => v.into_pyobject(py)?.into_any().unbind(),
                crazyflie_lib::Value::I16(v) => v.into_pyobject(py)?.into_any().unbind(),
                crazyflie_lib::Value::I32(v) => v.into_pyobject(py)?.into_any().unbind(),
                crazyflie_lib::Value::I64(v) => v.into_pyobject(py)?.into_any().unbind(),
                crazyflie_lib::Value::F16(v) => v.to_f32().into_pyobject(py)?.into_any().unbind(),
                crazyflie_lib::Value::F32(v) => v.into_pyobject(py)?.into_any().unbind(),
                crazyflie_lib::Value::F64(v) => v.into_pyobject(py)?.into_any().unbind(),
            })
        })
    }

    /// Set a parameter value by name using lossy conversion from f64
    fn set(&self, name: &str, value: Py<PyAny>) -> PyResult<()> {
        Python::attach(|py| {
            // Extract as f64 and use lossy conversion
            let float_value = value.extract::<f64>(py)?;

            self.runtime.block_on(async {
                self.cf.param.set_lossy(name, float_value).await
            }).map_err(to_pyerr)?;

            Ok(())
        })
    }
}

/// Commander subsystem wrapper
#[pyclass]
struct Commander {
    cf: Arc<crazyflie_lib::Crazyflie>,
    runtime: Arc<Runtime>,
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

/// Platform subsystem wrapper
#[pyclass]
struct Platform {
    cf: Arc<crazyflie_lib::Crazyflie>,
    runtime: Arc<Runtime>,
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

/// Link context for scanning
#[pyclass]
struct LinkContext {
    inner: crazyflie_link::LinkContext,
    runtime: Arc<Runtime>,
}

#[pymethods]
impl LinkContext {
    #[new]
    fn new() -> PyResult<Self> {
        let runtime = Arc::new(Runtime::new().map_err(|e| {
            PyRuntimeError::new_err(format!("Failed to create Tokio runtime: {}", e))
        })?);

        Ok(LinkContext {
            inner: crazyflie_link::LinkContext::new(),
            runtime,
        })
    }

    /// Scan for Crazyflies on the default address
    ///
    /// Returns:
    ///     List of URIs found
    fn scan(&self) -> PyResult<Vec<String>> {
        let uris = self.runtime.block_on(async {
            self.inner.scan([0xE7; 5]).await
        }).map_err(|e| PyRuntimeError::new_err(format!("Scan failed: {:?}", e)))?;

        Ok(uris.into_iter().map(|uri| uri.to_string()).collect())
    }
}

/// Python module definition
#[pymodule]
fn _rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Crazyflie>()?;
    m.add_class::<Console>()?;
    m.add_class::<Param>()?;
    m.add_class::<Commander>()?;
    m.add_class::<Platform>()?;
    m.add_class::<LinkContext>()?;
    Ok(())
}
