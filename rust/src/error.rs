//! Error conversion utilities for Python bindings

use pyo3::exceptions::PyRuntimeError;
use pyo3::PyErr;

/// Convert Rust crazyflie_lib errors to Python exceptions
pub fn to_pyerr(err: crazyflie_lib::Error) -> PyErr {
    PyRuntimeError::new_err(format!("Crazyflie error: {:?}", err))
}
