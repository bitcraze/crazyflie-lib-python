//! Crazyflie connection and subsystem access

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use pyo3_stub_gen_derive::*;
use std::sync::Arc;
use tokio::runtime::Runtime;

use crate::error::to_pyerr;
use crate::link_context::LinkContext;
use crate::subsystems::{Commander, Console, HighLevelCommander, Localization, Param, Platform, Log};
use crate::toc_cache::{NoTocCache, InMemoryTocCache, FileTocCache};

/// Internal enum to hold any of the cache types
#[derive(Clone)]
enum AnyCacheWrapper {
    NoCache(NoTocCache),
    InMemory(InMemoryTocCache),
    File(FileTocCache),
}

impl crazyflie_lib::TocCache for AnyCacheWrapper {
    fn get_toc(&self, crc32: u32) -> Option<String> {
        match self {
            AnyCacheWrapper::NoCache(c) => crazyflie_lib::TocCache::get_toc(c, crc32),
            AnyCacheWrapper::InMemory(c) => crazyflie_lib::TocCache::get_toc(c, crc32),
            AnyCacheWrapper::File(c) => crazyflie_lib::TocCache::get_toc(c, crc32),
        }
    }

    fn store_toc(&self, crc32: u32, toc: &str) {
        match self {
            AnyCacheWrapper::NoCache(c) => crazyflie_lib::TocCache::store_toc(c, crc32, toc),
            AnyCacheWrapper::InMemory(c) => crazyflie_lib::TocCache::store_toc(c, crc32, toc),
            AnyCacheWrapper::File(c) => crazyflie_lib::TocCache::store_toc(c, crc32, toc),
        }
    }
}

/// Wrapper for the Crazyflie struct
///
/// This provides a Python interface to the Rust Crazyflie implementation.
/// Since the Rust library is async, we wrap it with a Tokio runtime.
#[gen_stub_pyclass]
#[pyclass]
pub struct Crazyflie {
    pub(crate) inner: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
}

#[gen_stub_pymethods]
#[pymethods]
impl Crazyflie {
    /// Connect to a Crazyflie from a URI string
    ///
    /// Args:
    ///     link_context: LinkContext instance for connection management
    ///     uri: Connection URI (e.g., "radio://0/80/2M/E7E7E7E7E7")
    ///     toc_cache: Optional TOC cache instance (NoTocCache, InMemoryTocCache, or FileTocCache)
    ///                If not provided, defaults to NoTocCache (no caching)
    ///
    /// Returns:
    ///     Connected Crazyflie instance
    #[staticmethod]
    #[pyo3(signature = (link_context, uri, toc_cache=None))]
    fn connect_from_uri(link_context: &LinkContext, uri: String, #[gen_stub(override_type(type_repr = "typing.Optional[typing.Union[NoTocCache, InMemoryTocCache, FileTocCache]]"))] toc_cache: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let runtime = link_context.runtime.clone();

        // Extract cache from Python object
        let cache = if let Some(cache_obj) = toc_cache {
            // Try to extract each cache type
            if let Ok(no_cache) = cache_obj.extract::<NoTocCache>() {
                AnyCacheWrapper::NoCache(no_cache)
            } else if let Ok(mem_cache) = cache_obj.extract::<InMemoryTocCache>() {
                AnyCacheWrapper::InMemory(mem_cache)
            } else if let Ok(file_cache) = cache_obj.extract::<FileTocCache>() {
                AnyCacheWrapper::File(file_cache)
            } else {
                return Err(PyRuntimeError::new_err(
                    "toc_cache must be NoTocCache, InMemoryTocCache, or FileTocCache"
                ));
            }
        } else {
            // Default to NoTocCache
            AnyCacheWrapper::NoCache(NoTocCache)
        };

        let inner = runtime.block_on(async {
            crazyflie_lib::Crazyflie::connect_from_uri(&link_context.inner, &uri, cache).await
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

    /// Get the commander subsystem
    fn commander(&self) -> Commander {
        Commander {
            cf: self.inner.clone(),
            runtime: self.runtime.clone(),
        }
    }

    /// Get the console subsystem
    fn console(&self) -> Console {
        Console::new(self.inner.clone(), self.runtime.clone())
    }

    fn high_level_commander(&self) -> HighLevelCommander {
        HighLevelCommander {
            cf: self.inner.clone(),
            runtime: self.runtime.clone(),
        }
    }

    /// Get the localization subsystem
    fn localization(&self) -> Localization {
        Localization {
            cf: self.inner.clone(),
            runtime: self.runtime.clone(),
        }
    }

    /// Get the log subsystem
    fn log(&self) -> Log {
        Log {
            cf: self.inner.clone(),
            runtime: self.runtime.clone(),
        }
    }

    /// Get the param subsystem
    fn param(&self) -> Param {
        Param {
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
