//! Error types for SerpentAI Core

use pyo3::create_exception;
use pyo3::exceptions::PyException;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum SerpentError {
    #[error("Token optimization error: {0}")]
    TokenOptimization(String),

    #[error("Sandbox execution error: {0}")]
    SandboxExecution(String),

    #[error("Cryptographic error: {0}")]
    Crypto(String),

    #[error("Memory index error: {0}")]
    MemoryIndex(String),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

create_exception!(serpent_ai_core, PySerpentError, PyException);

impl From<SerpentError> for pyo3::PyErr {
    fn from(err: SerpentError) -> Self {
        PySerpentError::new_err(err.to_string())
    }
}

pub type Result<T> = std::result::Result<T, SerpentError>;
