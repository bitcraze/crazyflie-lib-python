use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::error::to_pyerr;

/// Access to the Crazyflie Log Subsystem
///
/// This struct provides functions to interact with the Crazyflie Log subsystem.
#[pyclass]
pub struct Log {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
}

#[pymethods]
impl Log {
    /// Get the names of all the log variables
    ///
    /// The names contain group and name of the log variable formatted as
    /// "group.name".
    fn names(&self) -> Vec<String> {
        self.cf.log.names()
    }

    /// Return the type of a log variable or an Error if the parameter does not exist.
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

    /// Create a Log block
    ///
    /// This will create a log block in the Crazyflie firmware and return a
    /// LogBlock object that can be used to add variable to the block and start
    /// logging
    ///
    /// This function can fail if there is no more log block ID available: each
    /// log block is assigned a 8 bit ID by the lib and so far they are not
    /// re-used. So during a Crazyflie connection lifetime, up to 256 log
    /// blocks can be created. If this becomes a problem for any use-case, it
    /// can be solved by a more clever ID generation algorithm.
    ///
    /// The Crazyflie firmware also has a limit in number of active log block,
    /// this function will fail if this limit is reached. Unlike for the ID, the
    /// active log blocks in the Crazyflie are cleaned-up when the LogBlock
    /// object is dropped.
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

/// Log Block
///
/// This object represents an IDLE LogBlock in the Crazyflie.
///
/// If the LogBlock object is dropped or its associated LogStream, the
/// Log Block will be deleted in the Crazyflie freeing resources.
#[pyclass]
pub struct LogBlock {
    runtime: Arc<Runtime>,
    inner: Option<crazyflie_lib::subsystems::log::LogBlock>,
}

#[pymethods]
impl LogBlock {
    /// Add a variable to the log block
    ///
    /// A packet will be sent to the Crazyflie to add the variable. The variable is logged in the same format as
    /// it is stored in the Crazyflie (ie. there is no conversion done)
    ///
    /// This function can fail if the variable is not found in the toc or of the Crazyflie returns an error
    /// The most common error reported by the Crazyflie would be if the log block is already too full.
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

    /// Start log block and return a stream to read the value
    ///
    /// Since a log-block cannot be modified after being started, this function
    /// consumes the LogBlock object and return a LogStream. The function
    /// LogStream.stop() can be called on the LogStream to get back the LogBlock object.
    ///
    /// This function can fail if there is a protocol error or an error
    /// reported by the Crazyflie. In such case, the LogBlock object will be
    /// dropped and the block will be deleted in the Crazyflie
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

/// Log Stream
///
/// This object represents a started log block that is currently returning data
/// at regular intervals.
///
/// Dropping this object or the associated LogBlock will delete the log block
/// in the Crazyflie.
#[pyclass]
pub struct LogStream {
    runtime: Arc<Runtime>,
    inner: Option<crazyflie_lib::subsystems::log::LogStream>,
}

#[pymethods]
impl LogStream {
    /// Get the next log data from the log block stream
    ///
    /// This function will wait for the data and only return a value when the
    /// next data is available.
    ///
    /// This function will return an error if the Crazyflie gets disconnected.
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

    /// Stops the log block from streaming
    ///
    /// This method consumes the stream and returns back the log block object so that it can be started again later
    /// with a different period.
    ///
    /// This function can only fail on unexpected protocol error. If it does, the log block is dropped and will be
    /// cleaned-up next time a log block is created.
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