"""
Tests for Rust Bridge module.

Tests the graceful degradation pattern:
- When Rust core is NOT available (default): all bridge functions return None/False
- When Rust core IS available: functions return real instances
"""

import pytest
import sys
import os

# Ensure backend is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestRustBridgeFallback:
    """Test that rust_bridge works correctly when Rust is NOT compiled."""

    def test_rust_available_returns_bool(self):
        """rust_available() should return a boolean."""
        from backend.core.rust_bridge import rust_available
        result = rust_available()
        assert isinstance(result, bool)

    def test_rust_import_error_is_string_or_none(self):
        """get_rust_import_error() should return string or None."""
        from backend.core.rust_bridge import get_rust_import_error
        result = get_rust_import_error()
        assert result is None or isinstance(result, str)

    def test_get_rust_token_optimizer_returns_none_or_object(self):
        """Should return None when Rust not available, or instance when available."""
        from backend.core.rust_bridge import get_rust_token_optimizer
        result = get_rust_token_optimizer()
        if result is None:
            assert True  # Expected in CI
        else:
            # Should have Rust optimizer methods
            assert hasattr(result, 'count_tokens')
            assert hasattr(result, 'compress')

    def test_get_rust_crypto_returns_none_or_object(self):
        """Should return None when Rust not available, or instance when available."""
        from backend.core.rust_bridge import get_rust_crypto
        result = get_rust_crypto()
        if result is None:
            assert True
        else:
            assert hasattr(result, 'encrypt')
            assert hasattr(result, 'decrypt')
            assert hasattr(result, 'sha256')

    def test_get_rust_memory_index_returns_none_or_object(self):
        """Should return None when Rust not available, or instance when available."""
        from backend.core.rust_bridge import get_rust_memory_index
        result = get_rust_memory_index(dimension=128)
        if result is None:
            assert True
        else:
            assert hasattr(result, 'add')
            assert hasattr(result, 'search')

    def test_get_rust_sandbox_returns_none_or_object(self):
        """Should return None when Rust not available, or instance when available."""
        from backend.core.rust_bridge import get_rust_sandbox
        result = get_rust_sandbox()
        if result is None:
            assert True
        else:
            assert hasattr(result, 'execute')

    def test_hash_text_fast_returns_none_or_int(self):
        """hash_text_fast should return None or an integer hash."""
        from backend.core.rust_bridge import hash_text_fast
        result = hash_text_fast("hello")
        if result is None:
            assert True
        else:
            assert isinstance(result, int)

    def test_count_tokens_fast_returns_none_or_int(self):
        """count_tokens_fast should return None or token count."""
        from backend.core.rust_bridge import count_tokens_fast
        result = count_tokens_fast("hello world")
        if result is None:
            assert True
        else:
            assert isinstance(result, int)
            assert result >= 0

    def test_compress_lz4_returns_none_or_bytes(self):
        """compress_lz4 should return None or compressed bytes."""
        from backend.core.rust_bridge import compress_lz4
        result = compress_lz4("hello world")
        if result is None:
            assert True
        else:
            assert isinstance(result, bytes)

    def test_decompress_lz4_returns_none_or_str(self):
        """decompress_lz4 should return None or decompressed string."""
        from backend.core.rust_bridge import decompress_lz4
        result = decompress_lz4(b"invalid")
        if result is None:
            assert True
        else:
            assert isinstance(result, str)

    def test_module_imports_without_error(self):
        """Module should always import without error, regardless of Rust availability."""
        import importlib
        mod = importlib.import_module('backend.core.rust_bridge')
        assert hasattr(mod, 'rust_available')
        assert hasattr(mod, 'get_rust_token_optimizer')
        assert hasattr(mod, 'get_rust_crypto')
        assert hasattr(mod, 'get_rust_memory_index')
        assert hasattr(mod, 'get_rust_sandbox')


class TestTokenOptimizerWithRustBridge:
    """Test TokenOptimizer works with and without Rust acceleration."""

    def test_optimizer_initializes(self):
        """TokenOptimizer should always initialize, Rust or not."""
        from backend.efficiency.token_optimizer import TokenOptimizer
        opt = TokenOptimizer()
        assert opt is not None

    def test_estimate_tokens_basic(self):
        """Basic token estimation should work."""
        from backend.efficiency.token_optimizer import TokenOptimizer
        opt = TokenOptimizer()
        assert opt.estimate_tokens("hello") > 0
        assert opt.estimate_tokens("") == 0
        assert opt.estimate_tokens("你好世界") > 0

    def test_compress_prompt_basic(self):
        """Prompt compression should work regardless of Rust."""
        from backend.efficiency.token_optimizer import TokenOptimizer
        opt = TokenOptimizer()
        result = opt.compress_prompt("hello\n\n\nworld\n\n\n")
        assert result.optimized_tokens <= result.original_tokens
        assert result.savings >= 0

    def test_compress_data_returns_none_without_rust(self):
        """LZ4 compression should return None when Rust unavailable."""
        from backend.efficiency.token_optimizer import TokenOptimizer
        opt = TokenOptimizer()
        result = opt.compress_data("test")
        # None if no Rust, bytes if Rust available
        assert result is None or isinstance(result, bytes)

    def test_stats_includes_rust_flag(self):
        """Stats should include rust_accelerated flag."""
        from backend.efficiency.token_optimizer import TokenOptimizer
        opt = TokenOptimizer()
        stats = opt.get_stats()
        assert "rust_accelerated" in stats
        assert isinstance(stats["rust_accelerated"], bool)

    def test_cache_hit_on_second_call(self):
        """Second call with same prompt should be a cache hit."""
        from backend.efficiency.token_optimizer import TokenOptimizer
        opt = TokenOptimizer()
        prompt = "这是一段测试文本用于验证缓存"
        r1 = opt.compress_prompt(prompt)
        r2 = opt.compress_prompt(prompt)
        assert r2.method == "cache"
        assert opt._cache_hits >= 1
