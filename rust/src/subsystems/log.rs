use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::error::to_pyerr;

/// Log subsystem wrapper
#[pyclass]
pub struct Log {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
}

#[pymethods]
impl Log {
    /// Get list of all log variable names
    fn names(&self) -> Vec<String> {
        self.cf.log.names()
    }

    /// Get the type of a log variable by name
    ///
    /// Args:
    ///     name: Log variable name
    ///
    /// Returns:
    ///     Type as string (e.g., "u8", "i16", "f32")
    fn get_type(&self, name: &str) -> PyResult<String> {
        let value_type = self.cf.log.get_type(name).map_err(to_pyerr)?;

        // Convert ValueType to string
        let type_str = match value_type {
            crazyflie_lib::ValueType::U8 => "u8",
            crazyflie_lib::ValueType::U16 => "u16",
            crazyflie_lib::ValueType::U32 => "u32",
            crazyflie_lib::ValueType::U64 => "u64",
            crazyflie_lib::ValueType::I8 => "i8",
            crazyflie_lib::ValueType::I16 => "i16",
            crazyflie_lib::ValueType::I32 => "i32",
            crazyflie_lib::ValueType::I64 => "i64",
            crazyflie_lib::ValueType::F16 => "f16",
            crazyflie_lib::ValueType::F32 => "f32",
            crazyflie_lib::ValueType::F64 => "f64",
        };

        Ok(type_str.to_string())
    }

    /// Create a new log block for streaming telemetry data
    ///
    /// Returns:
    ///     A new LogBlock instance that can have variables added to it
    fn create_block(&self) -> PyResult<LogBlock> {
        let log_block = self.runtime.block_on(async {
            self.cf.log.create_block().await
        }).map_err(to_pyerr)?;

        Ok(LogBlock {
            runtime: self.runtime.clone(),
            inner: Some(log_block),
        })
    }
}

/// Log block for collecting telemetry data
#[pyclass]
pub struct LogBlock {
    runtime: Arc<Runtime>,
    inner: Option<crazyflie_lib::subsystems::log::LogBlock>,
}

#[pymethods]
impl LogBlock {
    /// Add a variable to the log block
    ///
    /// Args:
    ///     name: Variable name (e.g., "stateEstimate.roll")
    fn add_variable(&mut self, name: &str) -> PyResult<()> {
        let inner = self.inner.as_mut()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("LogBlock has been consumed"))?;

        self.runtime.block_on(async {
            inner.add_variable(name).await
        }).map_err(to_pyerr)?;

        Ok(())
    }

    /// Start streaming data from this log block
    ///
    /// Args:
    ///     period_ms: Sampling period in milliseconds (10-2550)
    ///
    /// Returns:
    ///     A LogStream for reading data
    fn start(&mut self, period_ms: u64) -> PyResult<LogStream> {
        let inner = self.inner.take()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("LogBlock already started"))?;

        let period = crazyflie_lib::subsystems::log::LogPeriod::from_millis(period_ms).map_err(to_pyerr)?;

        let log_stream = self.runtime.block_on(async {
            inner.start(period).await
        }).map_err(to_pyerr)?;

        Ok(LogStream {
            runtime: self.runtime.clone(),
            inner: Some(log_stream),
        })
    }
}

/// Active log stream returning telemetry data
#[pyclass]
pub struct LogStream {
    runtime: Arc<Runtime>,
    inner: Option<crazyflie_lib::subsystems::log::LogStream>,
}

#[pymethods]
impl LogStream {
    /// Get the next data sample from the stream
    ///
    /// Returns:
    ///     Dictionary with timestamp and variable values
    fn next(&self) -> PyResult<Py<PyDict>> {
        let inner = self.inner.as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("LogStream has been stopped"))?;

        let log_data = self.runtime.block_on(async {
            inner.next().await
        }).map_err(to_pyerr)?;

        Python::attach(|py| {
            let dict = PyDict::new(py);
            dict.set_item("timestamp", log_data.timestamp)?;

            let data = PyDict::new(py);
            for (name, value) in log_data.data {
                let py_value = match value {
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
                };
                data.set_item(name, py_value)?;
            }

            dict.set_item("data", data)?;
            Ok(dict.unbind())
        })
    }

    /// Stop the log stream and return the log block
    ///
    /// Returns:
    ///     The original LogBlock that can be restarted
    fn stop(&mut self) -> PyResult<LogBlock> {
        let inner = self.inner.take()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("LogStream already stopped"))?;

        let log_block = self.runtime.block_on(async {
            inner.stop().await
        }).map_err(to_pyerr)?;

        Ok(LogBlock {
            runtime: self.runtime.clone(),
            inner: Some(log_block),
        })
    }
}