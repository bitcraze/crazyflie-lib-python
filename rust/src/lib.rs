//! Python bindings for the Crazyflie rust library

#![warn(missing_docs)]

use pyo3::prelude::*;

mod crazyflie;
mod error;
mod link_context;
mod subsystems;

use crazyflie::Crazyflie;
use link_context::LinkContext;
use subsystems::{Commander, Console, Param, Platform};

/// Python module definition
#[pymodule]
fn _rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Crazyflie>()?;
    m.add_class::<LinkContext>()?;
    m.add_class::<Commander>()?;
    m.add_class::<Console>()?;
    m.add_class::<Param>()?;
    m.add_class::<Platform>()?;
    Ok(())
}
