//! Console subsystem - read text output from the Crazyflie

use pyo3::prelude::*;
use std::sync::Arc;
use tokio::runtime::Runtime;
use tokio::sync::Mutex;
use futures::stream::Stream;
use std::pin::Pin;

type LineStream = Pin<Box<dyn Stream<Item = String> + Send>>;

/// Console subsystem wrapper
#[pyclass]
pub struct Console {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
    stream: Arc<Mutex<Option<LineStream>>>,
}

impl Console {
    /// Create a new Console instance
    pub fn new(cf: Arc<crazyflie_lib::Crazyflie>, runtime: Arc<Runtime>) -> Self {
        Console {
            cf,
            runtime,
            stream: Arc::new(Mutex::new(None)),
        }
    }
}

#[pymethods]
impl Console {
    /// Get console lines as they arrive
    ///
    /// Returns:
    ///     List of console output lines (up to 100 with 10ms timeout)
    fn get_lines(&self) -> PyResult<Vec<String>> {
        self.runtime.block_on(async {
            use futures::StreamExt;

            let mut stream_guard = self.stream.lock().await;

            // Initialize stream if not already created
            if stream_guard.is_none() {
                let new_stream = self.cf.console.line_stream().await;
                *stream_guard = Some(Box::pin(new_stream));
            }

            let stream = stream_guard.as_mut().unwrap();
            let mut lines = Vec::new();

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
