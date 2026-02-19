//! TOC Cache implementations for Python bindings

use pyo3::prelude::*;
use pyo3::exceptions::PyIOError;
use pyo3_stub_gen_derive::*;
use crazyflie_lib::TocCache;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::path::PathBuf;
use std::fs;

/// No-op TOC cache that doesn't store anything
///
/// This is the default cache used when no cache is provided to connect_from_uri.
/// It provides no caching functionality, meaning TOCs will be downloaded on every connection.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Clone)]
pub struct NoTocCache;

#[gen_stub_pymethods]
#[pymethods]
impl NoTocCache {
    /// Create a new NoTocCache instance
    #[new]
    fn new() -> Self {
        NoTocCache
    }
}

impl TocCache for NoTocCache {
    fn get_toc(&self, _key: &[u8]) -> Option<String> {
        None
    }

    fn store_toc(&self, _key: &[u8], _toc: &str) {
        // No-op: doesn't store anything
    }
}

/// In-memory TOC cache using a HashMap
///
/// This cache stores TOCs in memory for fast access. The cache is lost when the
/// Python process exits. Multiple Crazyflie connections can share the same cache
/// instance for improved performance.
///
/// Example:
///     context = LinkContext()
///     cache = InMemoryTocCache()
///     cf1 = Crazyflie.connect_from_uri(context, "radio://0/80/2M/E7E7E7E7E7", toc_cache=cache)
///     cf2 = Crazyflie.connect_from_uri(context, "radio://0/80/2M/E7E7E7E7E8", toc_cache=cache)
#[gen_stub_pyclass]
#[pyclass]
#[derive(Clone)]
pub struct InMemoryTocCache {
    cache: Arc<RwLock<HashMap<Vec<u8>, String>>>,
}

#[gen_stub_pymethods]
#[pymethods]
impl InMemoryTocCache {
    /// Create a new InMemoryTocCache instance
    #[new]
    fn new() -> Self {
        InMemoryTocCache {
            cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Clear all cached TOCs
    fn clear(&self) {
        if let Ok(mut cache) = self.cache.write() {
            cache.clear();
        }
    }

    /// Get the number of cached TOCs
    fn size(&self) -> usize {
        self.cache.read().map(|c| c.len()).unwrap_or(0)
    }
}

impl TocCache for InMemoryTocCache {
    fn get_toc(&self, key: &[u8]) -> Option<String> {
        self.cache.read().ok()?.get(key).cloned()
    }

    fn store_toc(&self, key: &[u8], toc: &str) {
        if let Ok(mut cache) = self.cache.write() {
            cache.insert(key.to_vec(), toc.to_string());
        }
    }
}

/// File-based TOC cache that persists to disk
///
/// This cache stores TOCs as individual JSON files in a specified directory.
/// Each TOC is stored as {key-hex}.json. The cache persists across Python process
/// restarts, making it ideal for production use.
///
/// The cache directory is created automatically if it doesn't exist.
///
/// Example:
///     context = LinkContext()
///     cache = FileTocCache("/tmp/cf_toc_cache")
///     cf = Crazyflie.connect_from_uri(context, "radio://0/80/2M/E7E7E7E7E7", toc_cache=cache)
#[gen_stub_pyclass]
#[pyclass]
#[derive(Clone)]
pub struct FileTocCache {
    cache_dir: Arc<PathBuf>,
    // In-memory cache for faster access
    memory_cache: Arc<RwLock<HashMap<Vec<u8>, String>>>,
}

#[gen_stub_pymethods]
#[pymethods]
impl FileTocCache {
    /// Create a new FileTocCache instance
    ///
    /// Args:
    ///     cache_dir: Directory path where TOC files will be stored
    #[new]
    fn new(cache_dir: String) -> PyResult<Self> {
        let path = PathBuf::from(cache_dir);

        // Create directory if it doesn't exist
        if !path.exists() {
            fs::create_dir_all(&path).map_err(|e| {
                PyIOError::new_err(format!("Failed to create cache directory: {}", e))
            })?;
        }

        Ok(FileTocCache {
            cache_dir: Arc::new(path),
            memory_cache: Arc::new(RwLock::new(HashMap::new())),
        })
    }

    /// Clear all cached TOC files
    fn clear(&self) -> PyResult<()> {
        // Clear memory cache
        if let Ok(mut cache) = self.memory_cache.write() {
            cache.clear();
        }

        // Remove all .json files from cache directory
        if let Ok(entries) = fs::read_dir(&*self.cache_dir) {
            for entry in entries.flatten() {
                if let Some(ext) = entry.path().extension() {
                    if ext == "json" {
                        let _ = fs::remove_file(entry.path());
                    }
                }
            }
        }

        Ok(())
    }

    /// Get the number of cached TOCs (from memory cache)
    fn size(&self) -> usize {
        self.memory_cache.read().map(|c| c.len()).unwrap_or(0)
    }

    /// Get the cache directory path
    fn get_cache_dir(&self) -> String {
        self.cache_dir.to_string_lossy().to_string()
    }
}

impl TocCache for FileTocCache {
    fn get_toc(&self, key: &[u8]) -> Option<String> {
        // First check memory cache
        if let Ok(cache) = self.memory_cache.read() {
            if let Some(toc) = cache.get(key) {
                return Some(toc.clone());
            }
        }

        // If not in memory, try to load from file
        let filename = format!("{}.json", key.iter().map(|b| format!("{:02x}", b)).collect::<String>());
        let file_path = self.cache_dir.join(filename);
        if let Ok(contents) = fs::read_to_string(&file_path) {
            // Cache in memory for next time
            if let Ok(mut cache) = self.memory_cache.write() {
                cache.insert(key.to_vec(), contents.clone());
            }
            Some(contents)
        } else {
            None
        }
    }

    fn store_toc(&self, key: &[u8], toc: &str) {
        // Store in memory cache
        if let Ok(mut cache) = self.memory_cache.write() {
            cache.insert(key.to_vec(), toc.to_string());
        }

        // Write to file (ignore errors - cache is best-effort)
        let filename = format!("{}.json", key.iter().map(|b| format!("{:02x}", b)).collect::<String>());
        let file_path = self.cache_dir.join(filename);
        let _ = fs::write(file_path, toc);
    }
}
