//! Parameter subsystem - read and write configuration parameters

use pyo3::prelude::*;
use pyo3_stub_gen_derive::*;
use std::sync::Arc;

use crate::error::to_pyerr;

/// Access to the Crazyflie Param Subsystem
///
/// This struct provides methods to interact with the parameter subsystem.
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
#[gen_stub_pyclass]
#[pyclass]
pub struct Param {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
}

#[gen_stub_pymethods]
#[pymethods]
impl Param {
    /// Get the names of all the parameters
    ///
    /// The names contain group and name of the parameter variable formatted as
    /// "group.name".
    fn names(&self) -> Vec<String> {
        self.cf.param.names()
    }

    /// Get the type of a parameter
    ///
    /// Returns the type string of the parameter (e.g., "u8", "f32", "i16").
    ///
    /// # Arguments
    /// * `name` - Parameter name in format "group.name"
    ///
    /// # Returns
    /// String representing the parameter type
    fn get_type(&self, name: &str) -> PyResult<String> {
        let param_type = self.cf.param.get_type(name).map_err(to_pyerr)?;
        Ok(format!("{:?}", param_type))
    }

    /// Get param value
    ///
    /// Get value of a parameter. This function takes the value from a local
    /// cache and so is quick.
    ///
    /// # Arguments
    /// * `name` - Parameter name in format "group.name"
    ///
    /// # Returns
    /// Parameter value (int or float depending on parameter type)
    #[gen_stub(override_return_type(type_repr = "collections.abc.Coroutine[typing.Any, typing.Any, int | float]"))]
    fn get<'py>(&self, py: Python<'py>, name: String) -> PyResult<Bound<'py, PyAny>> {
        let cf = self.cf.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let value: crazyflie_lib::Value = cf.param.get(&name).await.map_err(to_pyerr)?;

            // Convert Rust Value to Python object
            // We need to acquire the GIL to create Python objects
            Python::attach(|py| {
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
        })
    }

    /// Set a parameter value
    ///
    /// Sets a parameter to the given value. The value is automatically converted
    /// to match the parameter's type. Returns an error if the parameter does not
    /// exist or if the value cannot be converted to the parameter's type without
    /// loss of information.
    ///
    /// # Arguments
    /// * `name` - Parameter name in format "group.name"
    /// * `value` - New parameter value (int or float)
    ///
    /// # Errors
    /// Returns an error if:
    /// - The parameter does not exist
    /// - The value is out of range for the parameter type
    /// - The value cannot be represented accurately (e.g., fractional value for integer param)
    #[gen_stub(override_return_type(type_repr = "collections.abc.Coroutine[typing.Any, typing.Any, None]"))]
    fn set<'py>(&self, py: Python<'py>, name: String, #[gen_stub(override_type(type_repr = "int | float"))] value: Py<PyAny>) -> PyResult<Bound<'py, PyAny>> {
        // Get the parameter type (sync, no GIL needed for this)
        let param_type = self.cf.param.get_type(&name).map_err(to_pyerr)?;

        // Convert Python value to appropriate Rust Value based on param type
        // This must be done while we have the GIL
        use crazyflie_lib::{Value, ValueType};
        let rust_value = match param_type {
            ValueType::U8 => {
                let v = value.extract::<u8>(py)?;
                Value::U8(v)
            }
            ValueType::U16 => {
                let v = value.extract::<u16>(py)?;
                Value::U16(v)
            }
            ValueType::U32 => {
                let v = value.extract::<u32>(py)?;
                Value::U32(v)
            }
            ValueType::U64 => {
                let v = value.extract::<u64>(py)?;
                Value::U64(v)
            }
            ValueType::I8 => {
                let v = value.extract::<i8>(py)?;
                Value::I8(v)
            }
            ValueType::I16 => {
                let v = value.extract::<i16>(py)?;
                Value::I16(v)
            }
            ValueType::I32 => {
                let v = value.extract::<i32>(py)?;
                Value::I32(v)
            }
            ValueType::I64 => {
                let v = value.extract::<i64>(py)?;
                Value::I64(v)
            }
            ValueType::F16 => {
                let v = value.extract::<f32>(py)?;
                Value::F32(v) // F16 converts to F32
            }
            ValueType::F32 => {
                let v = value.extract::<f32>(py)?;
                Value::F32(v)
            }
            ValueType::F64 => {
                let v = value.extract::<f64>(py)?;
                Value::F64(v)
            }
        };

        let cf = self.cf.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            cf.param.set(&name, rust_value).await.map_err(to_pyerr)?;
            Ok(())
        })
    }
}
