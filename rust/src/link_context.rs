//! Link context for scanning and discovering Crazyflies

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use pyo3_stub_gen_derive::*;
use std::sync::Arc;

/// Check if the Wireshark capture feature was compiled in
///
/// Returns True if the library was built with the 'wireshark' feature enabled.
/// This is a compile-time check, not a runtime check.
#[pyfunction]
pub fn is_wireshark_feature_enabled() -> bool {
    #[cfg(feature = "wireshark")]
    {
        true
    }
    #[cfg(not(feature = "wireshark"))]
    {
        false
    }
}

/// Initialize Wireshark packet capture
///
/// Attempts to connect to the Wireshark extcap Unix socket at /tmp/crazyflie-wireshark.sock.
/// If the socket is not available (extcap not running), capture is silently disabled.
///
/// Call this before connecting to any Crazyflie to capture all packets.
///
/// Note: This function is only available when the 'wireshark' feature is enabled.
/// When disabled, this function does nothing.
///
/// Example:
///     from cflib._rust import init_wireshark_capture
///     init_wireshark_capture()  # Call once at startup
#[pyfunction]
pub fn init_wireshark_capture() {
    #[cfg(feature = "wireshark")]
    crazyflie_link::capture::init();
}

/// Check if Wireshark capture is available
///
/// Returns True if the extcap socket is connected and capture is active.
/// Always returns False if the 'wireshark' feature is not enabled.
#[pyfunction]
pub fn is_wireshark_capture_available() -> bool {
    #[cfg(feature = "wireshark")]
    {
        crazyflie_link::capture::is_available()
    }
    #[cfg(not(feature = "wireshark"))]
    {
        false
    }
}

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
