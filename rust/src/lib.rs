//! Python bindings for the Crazyflie rust library

#![warn(missing_docs)]

use pyo3::prelude::*;

mod crazyflie;
mod error;
mod link_context;
pub mod subsystems;

use crazyflie::Crazyflie;
use link_context::LinkContext;
use subsystems::{Commander, Console, Log, LogBlock, LogStream, Param, Platform};

/// Python module definition
#[pymodule]
fn _rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Crazyflie>()?;
    m.add_class::<LinkContext>()?;
    m.add_class::<Commander>()?;
    m.add_class::<Console>()?;
    m.add_class::<Log>()?;
    m.add_class::<LogBlock>()?;
    m.add_class::<LogStream>()?;
    m.add_class::<Param>()?;
    m.add_class::<Platform>()?;
    Ok(())
}

// Custom stub info gatherer that looks for pyproject.toml in the parent directory
pub fn stub_info() -> pyo3_stub_gen::Result<pyo3_stub_gen::StubInfo> {
    use std::path::PathBuf;

    // CARGO_MANIFEST_DIR is rust/, so go up one level to find pyproject.toml
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let pyproject_path = manifest_dir.parent().unwrap().join("pyproject.toml");

    pyo3_stub_gen::StubInfo::from_pyproject_toml(pyproject_path)
}
