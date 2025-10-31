//! Parameter subsystem - read and write configuration parameters

use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::error::to_pyerr;

/// Access to the Crazyflie Param Subsystem
///
/// This struct provide methods to interact with the parameter subsystem.
///
/// The Crazyflie exposes a param subsystem that allows to easily declare parameter
/// variables in the Crazyflie and to discover, read and write them from the ground.
///
/// Variables are defined in a table of content that is downloaded upon connection.
/// Each param variable have a unique name composed from a group and a variable name.
/// Functions that accesses variables, take a `name` parameter that accepts a string
/// in the format "group.variable"
///
/// During connection, the full param table of content is downloaded form the
/// Crazyflie as well as the values of all the variable. If a variable value
/// is modified by the Crazyflie during runtime, it sends a packet with the new
/// value which updates the local value cache.
#[pyclass]
pub struct Param {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
}

#[pymethods]
impl Param {
    /// Get the names of all the parameters
    ///
    /// The names contain group and name of the parameter variable formatted as
    /// "group.name".
    fn names(&self) -> Vec<String> {
        self.cf.param.names()
    }

    /// Get param value
    ///
    /// Get value of a parameter. This function takes the value from a local
    /// cache and so is quick.
    ///
    /// Args:
    ///     name: Parameter name in format "group.name"
    ///
    /// Returns:
    ///     Parameter value (int or float depending on parameter type)
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

    /// Set a parameter from a f64 potentially loosing data
    ///
    /// This function is a forgiving version of set. It allows
    /// to set any parameter of any type from a numeric value. This allows to set
    /// parameters without caring about the type and risking a type mismatch
    /// runtime error. Since there is no type or value check, loss of information
    /// can happen when using this function.
    ///
    /// Loss of information can happen in the following cases:
    ///  - When setting an integer, the value is truncated to the number of bit of the parameter
    ///    - Example: Setting `257` to a `u8` variable will set it to the value `1`
    ///  - Similarly floating point precision will be truncated to the parameter precision. Rounding is undefined.
    ///  - Setting a floating point outside the range of the parameter is undefined.
    ///  - It is not possible to represent accurately a `u64` parameter in a `f64`.
    ///
    /// Returns an error if the param does not exists.
    ///
    /// Args:
    ///     name: Parameter name in format "group.name"
    ///     value: New parameter value
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
