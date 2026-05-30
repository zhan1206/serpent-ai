//! High-performance Token Optimizer
//!
//! Features:
//! - Fast token counting using xxHash
//! - LZ4/ZSTD compression for prompts
//! - Incremental token tracking
//! - Parallel processing with Rayon

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;
use rayon::prelude::*;
use xxhash_rust::xxh3::xxh3_64;

/// Token statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenStats {
    pub total_tokens: usize,
    pub unique_tokens: usize,
    pub compression_ratio: f32,
    pub processing_time_ms: f64,
}

/// Token optimizer with caching and compression
#[pyclass]
pub struct TokenOptimizer {
    token_cache: Arc<RwLock<HashMap<u64, String>>>,
    compression_level: i32,
    enable_cache: bool,
}

#[pymethods]
impl TokenOptimizer {
    /// Create a new TokenOptimizer
    #[new]
    pub fn new(compression_level: Option<i32>, enable_cache: Option<bool>) -> Self {
        Self {
            token_cache: Arc::new(RwLock::new(HashMap::new())),
            compression_level: compression_level.unwrap_or(3),
            enable_cache: enable_cache.unwrap_or(true),
        }
    }

    /// Count tokens in text using fast hashing
    pub fn count_tokens(&self, text: &str) -> PyResult<usize> {
        let start = std::time::Instant::now();

        // Simple whitespace-based tokenization (can be replaced with BPE)
        let tokens: Vec<&str> = text.split_whitespace().collect();
        let token_count = tokens.len();

        // Cache tokens for potential reuse
        if self.enable_cache {
            let mut cache = self.token_cache.write();
            for token in tokens {
                let hash = xxh3_64(token.as_bytes());
                cache.entry(hash).or_insert_with(|| token.to_string());
            }
        }

        Ok(token_count)
    }

    /// Count tokens in multiple texts in parallel
    pub fn count_tokens_batch(&self, texts: Vec<&str>) -> PyResult<Vec<usize>> {
        let counts: Vec<usize> = texts
            .par_iter()
            .map(|text| text.split_whitespace().count())
            .collect();
        Ok(counts)
    }

    /// Compress text using LZ4
    pub fn compress(&self, text: &str) -> PyResult<Vec<u8>> {
        let compressed = lz4_flex::compress_prepend_size(text.as_bytes());
        Ok(compressed)
    }

    /// Decompress text
    pub fn decompress(&self, compressed: &[u8]) -> PyResult<String> {
        let decompressed = lz4_flex::decompress_size_prepended(compressed)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        String::from_utf8(decompressed)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    /// Get compression ratio
    pub fn compression_ratio(&self, original: &str, compressed: &[u8]) -> f32 {
        if original.is_empty() {
            return 0.0;
        }
        1.0 - (compressed.len() as f32 / original.len() as f32)
    }

    /// Optimize prompt by removing redundant whitespace
    pub fn optimize_prompt(&self, text: &str) -> PyResult<String> {
        let optimized: String = text
            .lines()
            .map(|line| line.trim())
            .filter(|line| !line.is_empty())
            .collect::<Vec<&str>>()
            .join("\n");
        Ok(optimized)
    }

    /// Extract unique tokens from text
    pub fn extract_unique_tokens(&self, text: &str) -> PyResult<Vec<String>> {
        let mut seen = std::collections::HashSet::new();
        let unique: Vec<String> = text
            .split_whitespace()
            .filter(|t| seen.insert(*t))
            .map(|s| s.to_string())
            .collect();
        Ok(unique)
    }

    /// Get token statistics
    pub fn get_stats(&self, text: &str) -> PyResult<TokenStats> {
        let start = std::time::Instant::now();

        let total_tokens = text.split_whitespace().count();
        let unique_tokens = self.extract_unique_tokens(text)?.len();

        let compressed = self.compress(text)?;
        let compression_ratio = self.compression_ratio(text, &compressed);

        let processing_time_ms = start.elapsed().as_secs_f64() * 1000.0;

        Ok(TokenStats {
            total_tokens,
            unique_tokens,
            compression_ratio,
            processing_time_ms,
        })
    }

    /// Clear the token cache
    pub fn clear_cache(&self) {
        if self.enable_cache {
            let mut cache = self.token_cache.write();
            cache.clear();
        }
    }

    /// Get cache size
    pub fn cache_size(&self) -> usize {
        self.token_cache.read().len()
    }
}

/// Standalone token counting function
#[pyfunction]
pub fn count_tokens_fast(text: &str) -> usize {
    text.split_whitespace().count()
}

/// Hash a string using xxHash3
#[pyfunction]
pub fn hash_text(text: &str) -> u64 {
    xxh3_64(text.as_bytes())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_count_tokens() {
        let optimizer = TokenOptimizer::new(None, None);
        assert_eq!(optimizer.count_tokens("hello world").unwrap(), 2);
        assert_eq!(optimizer.count_tokens("").unwrap(), 0);
    }

    #[test]
    fn test_compress_decompress() {
        let optimizer = TokenOptimizer::new(None, None);
        let text = "This is a test string for compression";
        let compressed = optimizer.compress(text).unwrap();
        let decompressed = optimizer.decompress(&compressed).unwrap();
        assert_eq!(text, decompressed);
    }

    #[test]
    fn test_optimize_prompt() {
        let optimizer = TokenOptimizer::new(None, None);
        let input = "  hello  \n\n  world  \n  ";
        let optimized = optimizer.optimize_prompt(input).unwrap();
        assert_eq!(optimized, "hello\nworld");
    }
}
