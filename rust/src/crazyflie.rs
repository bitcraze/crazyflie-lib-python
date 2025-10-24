//! Crazyflie connection and subsystem access

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::error::to_pyerr;
use crate::subsystems::{Commander, Console, Param, Platform};

/// Wrapper for the Crazyflie struct
///
/// This provides a Python interface to the Rust Crazyflie implementation.
/// Since the Rust library is async, we wrap it with a Tokio runtime.
#[pyclass]
pub struct Crazyflie {
    pub(crate) inner: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
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
        Console::new(self.inner.clone(), self.runtime.clone())
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
