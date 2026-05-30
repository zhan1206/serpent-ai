"""
SerpentAI 配置管理模块
负责所有配置的统一管理和热更新
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache
import os
import secrets
from pathlib import Path
try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None  # 优雅降级
import base64


def _generate_secure_key(length: int = 64) -> str:
    """
    生成安全的随机密钥
    
    注意：
    - 用于 SECRET_KEY 时可返回 hex 字符串
    - 用于 ENCRYPTION_KEY 时必须返回 base64 编码的 32 字节数据
    """
    return secrets.token_hex(length)


def _generate_fernet_key() -> bytes:
    """
    生成 Fernet 兼容的 32 字节密钥
    必须符合 cryptography.fernet.Fernet 规范：
    44 字符的 url-safe base64 编码数据
    """
    if Fernet is None:
        # 回退：手动生成 32 字节密钥
        return base64.urlsafe_b64encode(secrets.token_bytes(32))
    return Fernet.generate_key()


def _get_config_dir() -> Path:
    """获取配置目录"""
    base = Path(__file__).resolve().parent.parent
    return base / "config"


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    APP_NAME: str = "SerpentAI"
    APP_VERSION: str = "0.1.0-alpha"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, production, testing
    
    # 路径配置
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    CONFIG_DIR: Path = BASE_DIR / "config"
    
    # 数据库配置
    SQLITE_URL: str = "sqlite+aiosqlite:///serpent_ai.db"
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: Optional[str] = None  # 生产环境必须设置
    
    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # 模型配置
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_API_BASE: str = "https://api.anthropic.com"
    
    # 本地模型配置
    LOCAL_MODEL_DIR: str = "./models"
    LLAMA_CPP_THREADS: int = 4
    LLAMA_CPP_GPU_LAYERS: int = 0  # 0表示仅CPU
    
    # 安全配置
    SECRET_KEY: str = ""  # 生产环境必须设置
    ENCRYPTION_KEY: Optional[str] = None  # 生产环境必须设置
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 记忆系统配置
    VECTOR_DIMENSION: int = 384  # sentence-transformers维度
    SIMILARITY_THRESHOLD: float = 0.7
    MAX_INSTANT_MEMORIES: int = 10   # 瞬时记忆最大消息数
    MAX_SHORT_TERM_MEMORIES: int = 1000
    MAX_LONG_TERM_MEMORIES: int = 10000
    
    # Token优化配置
    ENABLE_TOKEN_OPTIMIZATION: bool = True
    PROMPT_CACHE_TTL: int = 3600  # 1小时
    TOOL_ID_MAPPING_ENABLED: bool = True
    CONTEXT_COMPRESSION_RATIO: float = 0.7
    
    # 多智能体配置
    MAX_AGENTS: int = 10
    AGENT_COMMUNICATION_TIMEOUT: int = 30
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_ROTATION: str = "100 MB"
    LOG_RETENTION: str = "30 days"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_secure_defaults()
    
    def _ensure_secure_defaults(self):
        """确保安全默认值"""
        config_dir = _get_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # 密钥文件路径
        secret_file = config_dir / ".secret_key"
        encryption_file = config_dir / ".encryption_key"
        neo4j_file = config_dir / ".neo4j_password"
        
        # SECRET_KEY: 从文件读取或生成
        if not self.SECRET_KEY:
            if secret_file.exists():
                self.SECRET_KEY = secret_file.read_text().strip()
            else:
                self.SECRET_KEY = _generate_secure_key(64)
                secret_file.write_text(self.SECRET_KEY)
                os.chmod(str(secret_file), 0o600)  # 仅所有者可读写
        
        # ENCRYPTION_KEY: 从文件读取或生成（必须是 Fernet 兼容格式）
        if not self.ENCRYPTION_KEY:
            if encryption_file.exists():
                raw = encryption_file.read_text().strip()
                # 如果是 base64 格式直接使用
                self.ENCRYPTION_KEY = raw
            else:
                # 生成 Fernet 兼容密钥
                fernet_key = _generate_fernet_key()
                encryption_file.write_bytes(fernet_key)
                os.chmod(str(encryption_file), 0o600)
                self.ENCRYPTION_KEY = fernet_key.decode()
        
        # NEO4J_PASSWORD: 从文件读取或生成
        if not self.NEO4J_PASSWORD:
            if neo4j_file.exists():
                self.NEO4J_PASSWORD = neo4j_file.read_text().strip()
            else:
                self.NEO4J_PASSWORD = _generate_secure_key(24)
                neo4j_file.write_text(self.NEO4J_PASSWORD)
                os.chmod(str(neo4j_file), 0o600)
        
        # 生产环境强制检查
        if self.ENVIRONMENT == "production":
            if "change-in-production" in self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError("⚠️ 生产环境 SECRET_KEY 未正确配置！")
            if not self.ENCRYPTION_KEY or len(self.ENCRYPTION_KEY) < 16:
                raise ValueError("⚠️ 生产环境 ENCRYPTION_KEY 未正确配置！")
            if self.DEBUG:
                raise ValueError("⚠️ 生产环境禁止 DEBUG=True！")
    
    def validate_security(self) -> List[str]:
        """验证安全配置，返回警告列表"""
        warnings = []
        if self.ENVIRONMENT == "production":
            if len(self.SECRET_KEY) < 32:
                warnings.append("SECRET_KEY 长度不足 32 字符")
            if not self.ENCRYPTION_KEY:
                warnings.append("ENCRYPTION_KEY 未设置")
            if self.DEBUG:
                warnings.append("生产环境不应启用 DEBUG")
            if not self.NEO4J_PASSWORD or len(self.NEO4J_PASSWORD) < 16:
                warnings.append("NEO4J_PASSWORD 不够安全")
        return warnings


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例（带缓存）"""
    settings = Settings()
    
    # 确保必要的目录存在
    for directory in [settings.DATA_DIR, settings.LOGS_DIR, settings.CONFIG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    return settings

def reload_settings() -> Settings:
    """重新加载配置（清除缓存 + 重新初始化）"""
    get_settings.cache_clear()
    return get_settings()

# 全局配置实例
settings = get_settings()
