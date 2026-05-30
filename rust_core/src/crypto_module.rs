//! Cryptographic Module - Hardware-accelerated encryption
//!
//! Features:
//! - AES-256-GCM encryption
//! - Secure key derivation (PBKDF2)
//! - SHA-256 hashing
//! - Constant-time comparison

use pyo3::prelude::*;
use aes_gcm::{
    aead::{Aead, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use sha2::{Digest, Sha256, Sha512};
use pbkdf2::pbkdf2_hmac;
use rand::RngCore;
use zeroize::Zeroize;
use std::fs;
use std::path::Path;

/// Generate a random key
pub fn generate_key() -> [u8; 32] {
    let mut key = [0u8; 32];
    OsRng.fill_bytes(&mut key);
    key
}

/// Generate a random nonce
pub fn generate_nonce() -> [u8; 12] {
    let mut nonce = [0u8; 12];
    OsRng.fill_bytes(&mut nonce);
    nonce
}

/// Crypto Module for encryption and hashing
#[pyclass]
pub struct CryptoModule {
    key: Option<[u8; 32]>,
}

#[pymethods]
impl CryptoModule {
    /// Create a new CryptoModule
    #[new]
    pub fn new() -> Self {
        Self { key: None }
    }

    /// Generate a new encryption key
    pub fn generate_key(&mut self) -> Vec<u8> {
        let key = generate_key();
        self.key = Some(key.clone());
        key.to_vec()
    }

    /// Set the encryption key
    pub fn set_key(&mut self, key: Vec<u8>) -> PyResult<()> {
        if key.len() != 32 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Key must be 32 bytes"
            ));
        }
        let mut arr = [0u8; 32];
        arr.copy_from_slice(&key);
        self.key = Some(arr);
        Ok(())
    }

    /// Encrypt data using AES-256-GCM
    pub fn encrypt(&self, plaintext: &[u8]) -> PyResult<Vec<u8>> {
        let key = self.key.as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err(
                "No key set. Call generate_key() or set_key() first."
            ))?;

        let cipher = Aes256Gcm::new_from_slice(key)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        let nonce_bytes = generate_nonce();
        let nonce = Nonce::from_slice(&nonce_bytes);

        let ciphertext = cipher.encrypt(nonce, plaintext)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        // Prepend nonce to ciphertext
        let mut result = nonce_bytes.to_vec();
        result.extend(ciphertext);
        Ok(result)
    }

    /// Decrypt data using AES-256-GCM
    pub fn decrypt(&self, encrypted: &[u8]) -> PyResult<Vec<u8>> {
        let key = self.key.as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err(
                "No key set. Call generate_key() or set_key() first."
            ))?;

        if encrypted.len() < 12 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Encrypted data too short"
            ));
        }

        let (nonce_bytes, ciphertext) = encrypted.split_at(12);
        let nonce = Nonce::from_slice(nonce_bytes);

        let cipher = Aes256Gcm::new_from_slice(key)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

        cipher.decrypt(nonce, ciphertext)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(
                format!("Decryption failed: {}", e)
            ))
    }

    /// Hash data using SHA-256
    #[staticmethod]
    pub fn sha256(data: &[u8]) -> Vec<u8> {
        let mut hasher = Sha256::new();
        hasher.update(data);
        hasher.finalize().to_vec()
    }

    /// Hash data using SHA-512
    #[staticmethod]
    pub fn sha512(data: &[u8]) -> Vec<u8> {
        let mut hasher = Sha512::new();
        hasher.update(data);
        hasher.finalize().to_vec()
    }

    /// Hash a string and return hex
    #[staticmethod]
    pub fn sha256_hex(data: &str) -> String {
        let hash = Self::sha256(data.as_bytes());
        hex::encode(hash)
    }

    /// Derive a key from a password using PBKDF2
    #[staticmethod]
    pub fn derive_key(password: &str, salt: &[u8], iterations: Option<u32>) -> Vec<u8> {
        let iters = iterations.unwrap_or(100_000);
        let mut key = [0u8; 32];
        pbkdf2_hmac::<Sha512>(password.as_bytes(), salt, iters, &mut key);
        key.to_vec()
    }

    /// Generate a random salt
    #[staticmethod]
    pub fn generate_salt(size: Option<usize>) -> Vec<u8> {
        let len = size.unwrap_or(16);
        let mut salt = vec![0u8; len];
        OsRng.fill_bytes(&mut salt);
        salt
    }

    /// Encrypt a file
    pub fn encrypt_file(&self, input_path: &str, output_path: &str) -> PyResult<()> {
        let plaintext = fs::read(input_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

        let encrypted = self.encrypt(&plaintext)?;

        fs::write(output_path, encrypted)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

        Ok(())
    }

    /// Decrypt a file
    pub fn decrypt_file(&self, input_path: &str, output_path: &str) -> PyResult<()> {
        let encrypted = fs::read(input_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

        let plaintext = self.decrypt(&encrypted)?;

        fs::write(output_path, plaintext)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

        Ok(())
    }

    /// Constant-time comparison
    #[staticmethod]
    pub fn compare_constant_time(a: &[u8], b: &[u8]) -> bool {
        if a.len() != b.len() {
            return false;
        }

        let mut result = 0u8;
        for (x, y) in a.iter().zip(b.iter()) {
            result |= x ^ y;
        }
        result == 0
    }
}

impl Default for CryptoModule {
    fn default() -> Self {
        Self::new()
    }
}

/// Hash a password with salt
#[pyfunction]
pub fn hash_password(password: &str, salt: Option<&[u8]>) -> PyResult<String> {
    let salt_bytes = salt.map(|s| s.to_vec()).unwrap_or_else(|| CryptoModule::generate_salt(None));
    let key = CryptoModule::derive_key(password, &salt_bytes, Some(100_000));
    Ok(format!("{}:{}", hex::encode(&salt_bytes), hex::encode(&key)))
}

/// Verify a password against a hash
#[pyfunction]
pub fn verify_password(password: &str, hash: &str) -> PyResult<bool> {
    let parts: Vec<&str> = hash.split(':').collect();
    if parts.len() != 2 {
        return Err(pyo3::exceptions::PyValueError::new_err("Invalid hash format"));
    }

    let salt = hex::decode(parts[0])
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let stored_key = hex::decode(parts[1])
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

    let derived_key = CryptoModule::derive_key(password, &salt, Some(100_000));

    Ok(CryptoModule::compare_constant_time(&derived_key, &stored_key))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encrypt_decrypt() {
        let mut crypto = CryptoModule::new();
        crypto.generate_key();

        let plaintext = b"Hello, World!";
        let encrypted = crypto.encrypt(plaintext).unwrap();
        let decrypted = crypto.decrypt(&encrypted).unwrap();

        assert_eq!(plaintext.to_vec(), decrypted);
    }

    #[test]
    fn test_sha256() {
        let hash = CryptoModule::sha256(b"test");
        assert_eq!(hash.len(), 32);
    }

    #[test]
    fn test_password_hashing() {
        let hash = hash_password("password123", None).unwrap();
        assert!(verify_password("password123", &hash).unwrap());
        assert!(!verify_password("wrong_password", &hash).unwrap());
    }
}
