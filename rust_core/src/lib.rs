//! SerpentAI Rust Core - High-performance modules
//!
//! This crate provides performance-critical components for SerpentAI:
//! - Token optimizer: Fast token counting and compression
//! - Tool sandbox: Secure execution environment
//! - Crypto module: Hardware-accelerated encryption
//! - Memory index: Efficient vector search

pub mod token_optimizer;
pub mod tool_sandbox;
pub mod crypto_module;
pub mod memory_index;
pub mod error;

use pyo3::prelude::*;
use error::SerpentError;

/// Python module definition
#[pymodule]
fn serpent_ai_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<token_optimizer::TokenOptimizer>()?;
    m.add_class::<tool_sandbox::ToolSandbox>()?;
    m.add_class::<crypto_module::CryptoModule>()?;
    m.add_class::<memory_index::MemoryIndex>()?;
    m.add("SerpentError", _py.get_type::<SerpentError>())?;
    Ok(())
}
