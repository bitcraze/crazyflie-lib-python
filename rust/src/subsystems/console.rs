//! Console subsystem - read text output from the Crazyflie

use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

/// Console subsystem wrapper
#[pyclass]
pub struct Console {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
}

#[pymethods]
impl Console {
    /// Get console lines as they arrive
    ///
    /// Returns:
    ///     List of console output lines (up to 100 with 10ms timeout)
    fn get_lines(&self) -> PyResult<Vec<String>> {
        // Simplified synchronous version - collects available lines
        self.runtime.block_on(async {
            use futures::StreamExt;
            let mut lines = Vec::new();
            let mut stream = self.cf.console.line_stream().await;

            // Get up to 100 lines or timeout
            for _ in 0..100 {
                if let Ok(Some(line)) = tokio::time::timeout(
                    std::time::Duration::from_millis(10),
                    stream.next()
                ).await {
                    lines.push(line);
                } else {
                    break;
                }
            }
            Ok(lines)
        })
    }
}
