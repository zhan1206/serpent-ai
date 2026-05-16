"""
SerpentAI 配置管理模块
负责所有配置的统一管理和热更新
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache
import os
from pathlib import Path

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
    NEO4J_PASSWORD: str = "serpent_ai_2024"
    
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
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ENCRYPTION_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 记忆系统配置
    VECTOR_DIMENSION: int = 384  # sentence-transformers维度
    SIMILARITY_THRESHOLD: float = 0.7
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

@lru_cache()
def get_settings() -> Settings:
    """获取配置单例（带缓存）"""
    settings = Settings()
    
    # 确保必要的目录存在
    for directory in [settings.DATA_DIR, settings.LOGS_DIR, settings.CONFIG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    return settings

def reload_settings() -> Settings:
    """重新加载配置（清除缓存）"""
    get_settings.cache_clear()
    return get_settings()

# 全局配置实例
settings = get_settings()
