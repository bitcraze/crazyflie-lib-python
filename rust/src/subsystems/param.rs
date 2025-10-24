//! Parameter subsystem - read and write configuration parameters

use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::error::to_pyerr;

/// Parameter subsystem wrapper
#[pyclass]
pub struct Param {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
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
