//! Link context for scanning and discovering Crazyflies

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use pyo3_stub_gen_derive::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

/// Link context for scanning and discovering Crazyflies
///
/// The LinkContext provides methods to scan for available Crazyflies on the network.
/// It can scan on specific addresses or use the default broadcast address.
///
/// Example:
///     context = LinkContext()
///     uris = context.scan()  # Scan on default address E7E7E7E7E7
///     for uri in uris:
///         print(f"Found: {uri}")
#[gen_stub_pyclass]
#[pyclass]
pub struct LinkContext {
    pub(crate) inner: crazyflie_link::LinkContext,
    pub(crate) runtime: Arc<Runtime>,
}

#[gen_stub_pymethods]
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

    /// Scan for Crazyflies on a specific address
    ///
    /// # Arguments
    /// * `address` - Optional 5-byte address to scan (defaults to [0xE7, 0xE7, 0xE7, 0xE7, 0xE7])
    ///
    /// # Returns
    /// List of URIs found
    #[pyo3(signature = (address=None))]
    fn scan(&self, address: Option<Vec<u8>>) -> PyResult<Vec<String>> {
        // Default to E7E7E7E7E7 if no address provided
        let addr = if let Some(addr_vec) = address {
            if addr_vec.len() != 5 {
                return Err(PyRuntimeError::new_err(
                    "Address must be exactly 5 bytes"
                ));
            }
            let mut addr_array = [0u8; 5];
            addr_array.copy_from_slice(&addr_vec);
            addr_array
        } else {
            [0xE7; 5]
        };

        let uris = self.runtime.block_on(async {
            self.inner.scan(addr).await
        }).map_err(|e| PyRuntimeError::new_err(format!("Scan failed: {:?}", e)))?;

        Ok(uris.into_iter().map(|uri| uri.to_string()).collect())
    }
}
