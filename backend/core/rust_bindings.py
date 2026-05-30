"""
Python wrapper for serpent_ai_core Rust module.

Provides a Pythonic interface to the high-performance Rust modules.
"""

from typing import Optional, Dict, List, Any
import os
import sys

# Try to import the Rust module
try:
    from serpent_ai_core import (
        TokenOptimizer,
        ToolSandbox,
        CryptoModule,
        MemoryIndex,
        count_tokens_fast,
        hash_text,
        euclidean_distance,
        dot_product,
        normalize_vector,
        hash_password,
        verify_password,
        default_limits,
        strict_limits,
        permissive_limits,
    )
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    # Provide fallback Python implementations
    import hashlib
    import json
    from dataclasses import dataclass, field
    from typing import Tuple

    @dataclass
    class TokenStats:
        total_tokens: int
        unique_tokens: int
        compression_ratio: float
        processing_time_ms: float

    class TokenOptimizer:
        """Fallback Python implementation of TokenOptimizer."""

        def __init__(self, compression_level: int = 3, enable_cache: bool = True):
            self.compression_level = compression_level
            self.enable_cache = enable_cache
            self._cache: Dict[int, str] = {}

        def count_tokens(self, text: str) -> int:
            """Count tokens using tiktoken (accurate) or approximation formula."""
            try:
                import tiktoken
                enc = tiktoken.get_encoding("cl100k_base")
                return len(enc.encode(text))
            except Exception:
                # Fallback: approximation formula
                # Chinese: ~1.5-2 chars per token; English: ~4 chars per token
                chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
                other_chars = len(text) - chinese_chars
                return int(chinese_chars * 0.5 + other_chars * 0.25)

        def count_tokens_batch(self, texts: List[str]) -> List[int]:
            return [self.count_tokens(t) for t in texts]

        def compress(self, text: str) -> bytes:
            import lz4.frame
            return lz4.frame.compress(text.encode())

        def decompress(self, data: bytes) -> str:
            import lz4.frame
            return lz4.frame.decompress(data).decode()

        def compression_ratio(self, original: str, compressed: bytes) -> float:
            if len(original) == 0:
                return 0.0
            return 1.0 - (len(compressed) / len(original))

        def optimize_prompt(self, text: str) -> str:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)

        def extract_unique_tokens(self, text: str) -> List[str]:
            seen = set()
            result = []
            for token in text.split():
                if token not in seen:
                    seen.add(token)
                    result.append(token)
            return result

        def get_stats(self, text: str) -> TokenStats:
            import time
            start = time.time()
            total = self.count_tokens(text)
            unique = len(self.extract_unique_tokens(text))
            compressed = self.compress(text)
            ratio = self.compression_ratio(text, compressed)
            elapsed = (time.time() - start) * 1000
            return TokenStats(total, unique, ratio, elapsed)

        def clear_cache(self):
            self._cache.clear()

        def cache_size(self) -> int:
            return len(self._cache)

    class ToolSandbox:
        """Fallback Python implementation of ToolSandbox."""

        @dataclass
        class ResourceLimits:
            max_memory_mb: int = 100
            max_cpu_seconds: int = 30
            max_file_size_mb: int = 10
            max_processes: int = 1
            allow_network: bool = False

        def __init__(self, limits: Optional['ToolSandbox.ResourceLimits'] = None,
                     working_dir: Optional[str] = None):
            self.limits = limits or self.ResourceLimits()
            self.working_dir = working_dir
            self.env_vars: Dict[str, str] = {}

        def set_env(self, key: str, value: str):
            self.env_vars[key] = value

        def set_limits(self, limits: 'ToolSandbox.ResourceLimits'):
            self.limits = limits

        def execute(self, command: str, args: List[str]) -> Dict[str, Any]:
            import subprocess
            import time
            start = time.time()
            try:
                result = subprocess.run(
                    [command] + args,
                    capture_output=True,
                    timeout=self.limits.max_cpu_seconds,
                    cwd=self.working_dir,
                    env={**os.environ, **self.env_vars}
                )
                return {
                    'stdout': result.stdout.decode(),
                    'stderr': result.stderr.decode(),
                    'exit_code': result.returncode,
                    'duration_ms': int((time.time() - start) * 1000),
                    'memory_used_mb': 0,
                    'timed_out': False
                }
            except subprocess.TimeoutExpired:
                return {
                    'stdout': '',
                    'stderr': 'Timeout',
                    'exit_code': -1,
                    'duration_ms': self.limits.max_cpu_seconds * 1000,
                    'memory_used_mb': 0,
                    'timed_out': True
                }

        def execute_python(self, script: str) -> Dict[str, Any]:
            return self.execute('python', ['-c', script])

        def is_path_allowed(self, path: str) -> bool:
            if self.working_dir:
                return path.startswith(self.working_dir)
            return True

        def get_limits(self) -> 'ToolSandbox.ResourceLimits':
            return self.limits

        def get_working_dir(self) -> Optional[str]:
            return self.working_dir

    class CryptoModule:
        """Fallback Python implementation of CryptoModule."""

        def __init__(self):
            self._key: Optional[bytes] = None

        def generate_key(self) -> bytes:
            import secrets
            self._key = secrets.token_bytes(32)
            return self._key

        def set_key(self, key: bytes):
            if len(key) != 32:
                raise ValueError("Key must be 32 bytes")
            self._key = key

        def encrypt(self, plaintext: bytes) -> bytes:
            from cryptography.fernet import Fernet
            import base64
            if not self._key:
                raise RuntimeError("No key set")
            fernet_key = base64.urlsafe_b64encode(self._key)
            f = Fernet(fernet_key)
            return f.encrypt(plaintext)

        def decrypt(self, encrypted: bytes) -> bytes:
            from cryptography.fernet import Fernet
            import base64
            if not self._key:
                raise RuntimeError("No key set")
            fernet_key = base64.urlsafe_b64encode(self._key)
            f = Fernet(fernet_key)
            return f.decrypt(encrypted)

        @staticmethod
        def sha256(data: bytes) -> bytes:
            return hashlib.sha256(data).digest()

        @staticmethod
        def sha512(data: bytes) -> bytes:
            return hashlib.sha512(data).digest()

        @staticmethod
        def sha256_hex(data: str) -> str:
            return hashlib.sha256(data.encode()).hexdigest()

        @staticmethod
        def derive_key(password: str, salt: bytes, iterations: int = 100000) -> bytes:
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives import hashes
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA512(),
                length=32,
                salt=salt,
                iterations=iterations,
            )
            return kdf.derive(password.encode())

        @staticmethod
        def generate_salt(size: int = 16) -> bytes:
            import secrets
            return secrets.token_bytes(size)

    class MemoryIndex:
        """Fallback Python implementation of MemoryIndex."""

        def __init__(self, dimension: int):
            self.dimension = dimension
            self._entries: Dict[str, Dict[str, Any]] = {}

        def add(self, id: str, vector: List[float], metadata: Optional[Dict[str, str]] = None):
            if len(vector) != self.dimension:
                raise ValueError(f"Vector dimension mismatch: expected {self.dimension}")
            self._entries[id] = {
                'vector': vector,
                'metadata': metadata or {}
            }

        def remove(self, id: str) -> bool:
            return self._entries.pop(id, None) is not None

        def get(self, id: str) -> Optional[List[float]]:
            entry = self._entries.get(id)
            return entry['vector'] if entry else None

        def search(self, query: List[float], k: int) -> List[Dict[str, Any]]:
            import math
            if len(query) != self.dimension:
                raise ValueError(f"Query dimension mismatch")

            def cosine_sim(a: List[float], b: List[float]) -> float:
                dot = sum(x * y for x, y in zip(a, b))
                mag_a = math.sqrt(sum(x * x for x in a))
                mag_b = math.sqrt(sum(x * x for x in b))
                return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0

            results = []
            for id, entry in self._entries.items():
                score = cosine_sim(query, entry['vector'])
                results.append({
                    'id': id,
                    'score': score,
                    'metadata': entry['metadata']
                })

            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:k]

        def len(self) -> int:
            return len(self._entries)

        def is_empty(self) -> bool:
            return len(self._entries) == 0

        def clear(self):
            self._entries.clear()

        def save(self, path: str):
            with open(path, 'w') as f:
                json.dump(self._entries, f)

        def load(self, path: str):
            with open(path, 'r') as f:
                self._entries = json.load(f)

    def count_tokens_fast(text: str) -> int:
        """Fast token count with Chinese-aware approximation."""
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
            other_chars = len(text) - chinese_chars
            return int(chinese_chars * 0.5 + other_chars * 0.25)

    def hash_text(text: str) -> int:
        return hash(text)

    def euclidean_distance(a: List[float], b: List[float]) -> float:
        import math
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def dot_product(a: List[float], b: List[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    def normalize_vector(vector: List[float]) -> List[float]:
        import math
        mag = math.sqrt(sum(x * x for x in vector))
        return [x / mag for x in vector] if mag else vector

    def hash_password(password: str, salt: Optional[bytes] = None) -> str:
        import secrets
        salt_bytes = salt or secrets.token_bytes(16)
        key = CryptoModule.derive_key(password, salt_bytes)
        return f"{salt_bytes.hex()}:{key.hex()}"

    def verify_password(password: str, hash_str: str) -> bool:
        parts = hash_str.split(':')
        if len(parts) != 2:
            return False
        salt = bytes.fromhex(parts[0])
        stored_key = bytes.fromhex(parts[1])
        derived = CryptoModule.derive_key(password, salt)
        return derived == stored_key

    def default_limits():
        return ToolSandbox.ResourceLimits()

    def strict_limits():
        return ToolSandbox.ResourceLimits(
            max_memory_mb=50,
            max_cpu_seconds=10,
            max_file_size_mb=1,
            max_processes=1,
            allow_network=False
        )

    def permissive_limits():
        return ToolSandbox.ResourceLimits(
            max_memory_mb=500,
            max_cpu_seconds=60,
            max_file_size_mb=50,
            max_processes=5,
            allow_network=True
        )


__all__ = [
    'TokenOptimizer',
    'ToolSandbox',
    'CryptoModule',
    'MemoryIndex',
    'count_tokens_fast',
    'hash_text',
    'euclidean_distance',
    'dot_product',
    'normalize_vector',
    'hash_password',
    'verify_password',
    'default_limits',
    'strict_limits',
    'permissive_limits',
    'RUST_AVAILABLE',
]
