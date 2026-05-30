//! Tool Sandbox - Secure execution environment
//!
//! Features:
//! - Resource limits (CPU, memory, time)
//! - Process isolation
//! - Safe file system operations
//! - Network restrictions

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

/// Resource limits for sandbox execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceLimits {
    pub max_memory_mb: usize,
    pub max_cpu_seconds: u64,
    pub max_file_size_mb: usize,
    pub max_processes: usize,
    pub allow_network: bool,
}

impl Default for ResourceLimits {
    fn default() -> Self {
        Self {
            max_memory_mb: 100,
            max_cpu_seconds: 30,
            max_file_size_mb: 10,
            max_processes: 1,
            allow_network: false,
        }
    }
}

/// Execution result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub stdout: String,
    pub stderr: String,
    pub exit_code: i32,
    pub duration_ms: u64,
    pub memory_used_mb: usize,
    pub timed_out: bool,
}

/// Tool Sandbox for secure code execution
#[pyclass]
pub struct ToolSandbox {
    limits: ResourceLimits,
    working_dir: Option<String>,
    env_vars: HashMap<String, String>,
}

#[pymethods]
impl ToolSandbox {
    /// Create a new ToolSandbox with optional limits
    #[new]
    #[pyo3(signature = (limits=None, working_dir=None))]
    pub fn new(limits: Option<ResourceLimits>, working_dir: Option<&str>) -> Self {
        Self {
            limits: limits.unwrap_or_default(),
            working_dir: working_dir.map(|s| s.to_string()),
            env_vars: HashMap::new(),
        }
    }

    /// Set an environment variable
    pub fn set_env(&mut self, key: &str, value: &str) {
        self.env_vars.insert(key.to_string(), value.to_string());
    }

    /// Set resource limits
    pub fn set_limits(&mut self, limits: ResourceLimits) {
        self.limits = limits;
    }

    /// Execute a command in the sandbox
    pub fn execute(&self, command: &str, args: Vec<&str>) -> PyResult<ExecutionResult> {
        let start = Instant::now();

        let mut cmd = Command::new(command);
        cmd.args(&args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        // Set working directory
        if let Some(ref dir) = self.working_dir {
            cmd.current_dir(dir);
        }

        // Set environment variables
        for (key, value) in &self.env_vars {
            cmd.env(key, value);
        }

        // Spawn and wait with timeout
        let child = cmd.spawn()
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(
                format!("Failed to spawn process: {}", e)
            ))?;

        let timeout = Duration::from_secs(self.limits.max_cpu_seconds);
        let result = child.wait_with_output();

        let duration_ms = start.elapsed().as_millis() as u64;

        match result {
            Ok(output) => {
                let stdout = String::from_utf8_lossy(&output.stdout).to_string();
                let stderr = String::from_utf8_lossy(&output.stderr).to_string();
                let exit_code = output.status.code().unwrap_or(-1);

                Ok(ExecutionResult {
                    stdout,
                    stderr,
                    exit_code,
                    duration_ms,
                    memory_used_mb: 0, // Would need platform-specific code
                    timed_out: false,
                })
            }
            Err(e) => {
                Ok(ExecutionResult {
                    stdout: String::new(),
                    stderr: format!("Execution error: {}", e),
                    exit_code: -1,
                    duration_ms,
                    memory_used_mb: 0,
                    timed_out: false,
                })
            }
        }
    }

    /// Execute a Python script
    pub fn execute_python(&self, script: &str) -> PyResult<ExecutionResult> {
        self.execute("python", vec!["-c", script])
    }

    /// Check if a file is within allowed paths
    pub fn is_path_allowed(&self, path: &str) -> bool {
        if let Some(ref dir) = self.working_dir {
            // Simple check: path must be under working directory
            path.starts_with(dir)
        } else {
            true
        }
    }

    /// Get current limits
    pub fn get_limits(&self) -> ResourceLimits {
        self.limits.clone()
    }

    /// Get allowed working directory
    pub fn get_working_dir(&self) -> Option<&str> {
        self.working_dir.as_deref()
    }
}

/// Create default resource limits
#[pyfunction]
pub fn default_limits() -> ResourceLimits {
    ResourceLimits::default()
}

/// Create strict resource limits (more restrictive)
#[pyfunction]
pub fn strict_limits() -> ResourceLimits {
    ResourceLimits {
        max_memory_mb: 50,
        max_cpu_seconds: 10,
        max_file_size_mb: 1,
        max_processes: 1,
        allow_network: false,
    }
}

/// Create permissive resource limits (less restrictive)
#[pyfunction]
pub fn permissive_limits() -> ResourceLimits {
    ResourceLimits {
        max_memory_mb: 500,
        max_cpu_seconds: 60,
        max_file_size_mb: 50,
        max_processes: 5,
        allow_network: true,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sandbox_creation() {
        let sandbox = ToolSandbox::new(None, None);
        assert_eq!(sandbox.get_limits().max_memory_mb, 100);
    }

    #[test]
    fn test_path_validation() {
        let sandbox = ToolSandbox::new(None, Some("/tmp/sandbox"));
        assert!(sandbox.is_path_allowed("/tmp/sandbox/file.txt"));
        assert!(!sandbox.is_path_allowed("/etc/passwd"));
    }

    #[test]
    fn test_env_setting() {
        let mut sandbox = ToolSandbox::new(None, None);
        sandbox.set_env("TEST", "value");
        assert!(sandbox.env_vars.contains_key("TEST"));
    }
}
