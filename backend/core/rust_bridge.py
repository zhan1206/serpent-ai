"""
Rust Core Bridge - Rust核心模块的Python桥接层

架构策略：
- 尝试导入 serpent_ai_core (Rust/PyO3 编译产物)
- 如果不可用，回退到纯Python实现
- 所有公开API保持一致，上层代码无需关心底层

安装Rust模块（可选）：
    cd rust_core && maturin develop --release

使用方式：
    from backend.core.rust_bridge import rust_available, get_token_optimizer, get_crypto, get_memory_index
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_rust_core = None
_rust_available = False
_rust_import_error: Optional[str] = None

try:
    import serpent_ai_core
    _rust_core = serpent_ai_core
    _rust_available = True
    logger.info("Rust core module (serpent_ai_core) loaded successfully")
except ImportError as e:
    _rust_import_error = str(e)
    logger.info(f"Rust core module not available, using Python fallback: {e}")


def rust_available() -> bool:
    """检查Rust核心模块是否可用"""
    return _rust_available


def get_rust_import_error() -> Optional[str]:
    """获取Rust模块导入失败原因"""
    return _rust_import_error


def get_rust_token_optimizer():
    """
    获取Rust TokenOptimizer实例（如可用）
    
    Rust版本提供：
    - 基于xxHash的快速token计数
    - LZ4/ZSTD压缩
    - Rayon并行批处理
    - 高性能prompt优化
    """
    if not _rust_available:
        return None
    try:
        return _rust_core.TokenOptimizer(
            compression_level=3,
            enable_cache=True
        )
    except Exception as e:
        logger.warning(f"Failed to create Rust TokenOptimizer: {e}")
        return None


def get_rust_crypto():
    """
    获取Rust CryptoModule实例（如可用）
    
    Rust版本提供：
    - AES-256-GCM硬件加速加密
    - PBKDF2-SHA512密钥派生
    - SHA-256/SHA-512哈希
    - 常量时间比较
    - zeroize安全密钥清理
    """
    if not _rust_available:
        return None
    try:
        return _rust_core.CryptoModule()
    except Exception as e:
        logger.warning(f"Failed to create Rust CryptoModule: {e}")
        return None


def get_rust_memory_index(dimension: int):
    """
    获取Rust MemoryIndex实例（如可用）
    
    Rust版本提供：
    - 基于HashMap的内存向量存储
    - 余弦相似度搜索
    - JSON序列化持久化
    - parking_lot RwLock并发安全
    """
    if not _rust_available:
        return None
    try:
        return _rust_core.MemoryIndex(dimension)
    except Exception as e:
        logger.warning(f"Failed to create Rust MemoryIndex: {e}")
        return None


def get_rust_sandbox(working_dir: Optional[str] = None):
    """
    获取Rust ToolSandbox实例（如可用）
    
    Rust版本提供：
    - 进程隔离执行
    - 资源限制（CPU/内存/时间）
    - 路径白名单
    - 环境变量注入
    """
    if not _rust_available:
        return None
    try:
        return _rust_core.ToolSandbox(
            limits=_rust_core.default_limits(),
            working_dir=working_dir
        )
    except Exception as e:
        logger.warning(f"Failed to create Rust ToolSandbox: {e}")
        return None


def hash_text_fast(text: str) -> Optional[int]:
    """xxHash3快速哈希（Rust版），返回None表示不可用"""
    if not _rust_available:
        return None
    try:
        return _rust_core.hash_text(text)
    except Exception:
        return None


def count_tokens_fast(text: str) -> Optional[int]:
    """快速token计数（Rust版），返回None表示不可用"""
    if not _rust_available:
        return None
    try:
        return _rust_core.count_tokens_fast(text)
    except Exception:
        return None


def compress_lz4(text: str) -> Optional[bytes]:
    """LZ4压缩（Rust版），返回None表示不可用"""
    if not _rust_available:
        return None
    try:
        optimizer = _rust_core.TokenOptimizer(enable_cache=False)
        return optimizer.compress(text)
    except Exception:
        return None


def decompress_lz4(data: bytes) -> Optional[str]:
    """LZ4解压（Rust版），返回None表示不可用"""
    if not _rust_available:
        return None
    try:
        optimizer = _rust_core.TokenOptimizer(enable_cache=False)
        return optimizer.decompress(data)
    except Exception:
        return None
