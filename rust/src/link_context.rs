//! Link context for scanning and discovering Crazyflies

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use pyo3_stub_gen_derive::*;
use std::sync::Arc;

/// Link context for scanning and discovering Crazyflies
///
/// The LinkContext provides methods to scan for available Crazyflies on the network.
/// It can scan on specific addresses or use the default broadcast address.
///
/// Example:
///     context = LinkContext()
///     uris = await context.scan()  # Scan on default address E7E7E7E7E7
///     for uri in uris:
///         print(f"Found: {uri}")
#[gen_stub_pyclass]
#[pyclass]
pub struct LinkContext {
    pub(crate) inner: Arc<crazyflie_link::LinkContext>,
}

#[gen_stub_pymethods]
#[pymethods]
impl LinkContext {
    #[new]
    fn new() -> PyResult<Self> {
        Ok(LinkContext {
            inner: Arc::new(crazyflie_link::LinkContext::new()),
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
    #[gen_stub(override_return_type(type_repr = "collections.abc.Coroutine[typing.Any, typing.Any, builtins.list[builtins.str]]"))]
    fn scan<'py>(&self, py: Python<'py>, address: Option<Vec<u8>>) -> PyResult<Bound<'py, PyAny>> {
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

        let inner = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let uris = inner.scan(addr).await
                .map_err(|e| PyRuntimeError::new_err(format!("Scan failed: {:?}", e)))?;
            Ok(uris.into_iter().map(|uri| uri.to_string()).collect::<Vec<_>>())
        })
    }
}
