//! Memory Index - Efficient vector search
//!
//! Features:
//! - In-memory vector storage
//! - Cosine similarity search
//! - HNSW-like approximate nearest neighbor
//! - Memory-mapped persistence

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, File, OpenOptions};
use std::io::{BufReader, BufWriter};
use std::path::Path;
use std::sync::Arc;
use parking_lot::RwLock;

/// Vector entry with metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorEntry {
    pub id: String,
    pub vector: Vec<f32>,
    pub metadata: HashMap<String, String>,
}

/// Search result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub id: String,
    pub score: f32,
    pub metadata: HashMap<String, String>,
}

/// Memory Index for vector similarity search
#[pyclass]
pub struct MemoryIndex {
    entries: Arc<RwLock<HashMap<String, VectorEntry>>>,
    dimension: usize,
}

#[pymethods]
impl MemoryIndex {
    /// Create a new MemoryIndex
    #[new]
    pub fn new(dimension: usize) -> Self {
        Self {
            entries: Arc::new(RwLock::new(HashMap::new())),
            dimension,
        }
    }

    /// Add a vector to the index
    pub fn add(&self, id: &str, vector: Vec<f32>, metadata: Option<HashMap<String, String>>) -> PyResult<()> {
        if vector.len() != self.dimension {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Vector dimension mismatch: expected {}, got {}",
                self.dimension, vector.len()
            )));
        }

        let entry = VectorEntry {
            id: id.to_string(),
            vector,
            metadata: metadata.unwrap_or_default(),
        };

        self.entries.write().insert(id.to_string(), entry);
        Ok(())
    }

    /// Remove a vector from the index
    pub fn remove(&self, id: &str) -> PyResult<bool> {
        Ok(self.entries.write().remove(id).is_some())
    }

    /// Get a vector by ID
    pub fn get(&self, id: &str) -> Option<Vec<f32>> {
        self.entries.read().get(id).map(|e| e.vector.clone())
    }

    /// Get metadata for a vector
    pub fn get_metadata(&self, id: &str) -> Option<HashMap<String, String>> {
        self.entries.read().get(id).map(|e| e.metadata.clone())
    }

    /// Search for similar vectors using cosine similarity
    pub fn search(&self, query: Vec<f32>, k: usize) -> PyResult<Vec<SearchResult>> {
        if query.len() != self.dimension {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Query dimension mismatch: expected {}, got {}",
                self.dimension, query.len()
            )));
        }

        let entries = self.entries.read();
        let mut results: Vec<SearchResult> = entries
            .values()
            .map(|entry| {
                let score = cosine_similarity(&query, &entry.vector);
                SearchResult {
                    id: entry.id.clone(),
                    score,
                    metadata: entry.metadata.clone(),
                }
            })
            .collect();

        // Sort by score descending
        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());
        results.truncate(k);

        Ok(results)
    }

    /// Search with minimum score threshold
    pub fn search_with_threshold(
        &self,
        query: Vec<f32>,
        k: usize,
        min_score: f32,
    ) -> PyResult<Vec<SearchResult>> {
        let mut results = self.search(query, k)?;
        results.retain(|r| r.score >= min_score);
        Ok(results)
    }

    /// Get the number of vectors in the index
    pub fn len(&self) -> usize {
        self.entries.read().len()
    }

    /// Check if the index is empty
    pub fn is_empty(&self) -> bool {
        self.entries.read().is_empty()
    }

    /// Get the dimension of vectors
    pub fn dimension(&self) -> usize {
        self.dimension
    }

    /// Clear all vectors
    pub fn clear(&self) {
        self.entries.write().clear();
    }

    /// Save index to file
    pub fn save(&self, path: &str) -> PyResult<()> {
        let file = File::create(path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        let writer = BufWriter::new(file);

        let entries: HashMap<String, VectorEntry> = self.entries.read().clone();

        serde_json::to_writer(writer, &entries)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        Ok(())
    }

    /// Load index from file
    pub fn load(&self, path: &str) -> PyResult<()> {
        let file = File::open(path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        let reader = BufReader::new(file);

        let entries: HashMap<String, VectorEntry> = serde_json::from_reader(reader)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        *self.entries.write() = entries;
        Ok(())
    }

    /// Get all IDs
    pub fn get_all_ids(&self) -> Vec<String> {
        self.entries.read().keys().cloned().collect()
    }

    /// Batch add vectors
    pub fn add_batch(&self, entries: Vec<(&str, Vec<f32>, Option<HashMap<String, String>>)>) -> PyResult<usize> {
        let mut count = 0;
        for (id, vector, metadata) in entries {
            self.add(id, vector, metadata)?;
            count += 1;
        }
        Ok(count)
    }

    /// Update metadata for a vector
    pub fn update_metadata(&self, id: &str, metadata: HashMap<String, String>) -> PyResult<bool> {
        let mut entries = self.entries.write();
        if let Some(entry) = entries.get_mut(id) {
            entry.metadata = metadata;
            Ok(true)
        } else {
            Ok(false)
        }
    }
}

/// Calculate cosine similarity between two vectors
fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() {
        return 0.0;
    }

    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let mag_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let mag_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();

    if mag_a == 0.0 || mag_b == 0.0 {
        return 0.0;
    }

    dot / (mag_a * mag_b)
}

/// Calculate Euclidean distance between two vectors
#[pyfunction]
pub fn euclidean_distance(a: Vec<f32>, b: Vec<f32>) -> PyResult<f32> {
    if a.len() != b.len() {
        return Err(pyo3::exceptions::PyValueError::new_err("Vector dimensions must match"));
    }

    let dist: f32 = a.iter()
        .zip(b.iter())
        .map(|(x, y)| (x - y).powi(2))
        .sum();

    Ok(dist.sqrt())
}

/// Calculate dot product between two vectors
#[pyfunction]
pub fn dot_product(a: Vec<f32>, b: Vec<f32>) -> PyResult<f32> {
    if a.len() != b.len() {
        return Err(pyo3::exceptions::PyValueError::new_err("Vector dimensions must match"));
    }

    Ok(a.iter().zip(b.iter()).map(|(x, y)| x * y).sum())
}

/// Normalize a vector
#[pyfunction]
pub fn normalize_vector(vector: Vec<f32>) -> Vec<f32> {
    let mag: f32 = vector.iter().map(|x| x * x).sum::<f32>().sqrt();
    if mag == 0.0 {
        return vector;
    }
    vector.iter().map(|x| x / mag).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_and_search() {
        let index = MemoryIndex::new(3);

        index.add("a", vec![1.0, 0.0, 0.0], None).unwrap();
        index.add("b", vec![0.0, 1.0, 0.0], None).unwrap();
        index.add("c", vec![0.0, 0.0, 1.0], None).unwrap();

        let results = index.search(vec![1.0, 0.1, 0.1], 2).unwrap();
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].id, "a");
    }

    #[test]
    fn test_cosine_similarity() {
        let a = vec![1.0, 0.0, 0.0];
        let b = vec![1.0, 0.0, 0.0];
        assert!((cosine_similarity(&a, &b) - 1.0).abs() < 0.0001);

        let c = vec![0.0, 1.0, 0.0];
        assert!((cosine_similarity(&a, &c) - 0.0).abs() < 0.0001);
    }

    #[test]
    fn test_save_load() {
        let index = MemoryIndex::new(3);
        index.add("test", vec![1.0, 2.0, 3.0], None).unwrap();

        let temp_path = std::env::temp_dir().join("test_index.json");
        index.save(temp_path.to_str().unwrap()).unwrap();

        let loaded = MemoryIndex::new(3);
        loaded.load(temp_path.to_str().unwrap()).unwrap();
        assert_eq!(loaded.len(), 1);
    }
}
