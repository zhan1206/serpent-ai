"""
SerpentAI 缓存管理模块
基于Redis的多级缓存系统，支持Token优化
"""
import json
import pickle
import hashlib
from typing import Any, Optional, Callable, Union
import logging
from functools import wraps
import redis

from core.config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """Redis缓存管理器（单例模式）"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            try:
                self._client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD,
                    decode_responses=False,  # 使用二进制模式支持pickle
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                # 测试连接
                self._client.ping()
                logger.info(f"Redis缓存连接成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            except redis.ConnectionError as e:
                logger.warning(f"Redis连接失败，将使用内存缓存: {e}")
                self._client = None
            except Exception as e:
                logger.error(f"Redis初始化失败: {e}")
                self._client = None
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """获取Redis客户端"""
        return self._client
    
    def is_available(self) -> bool:
        """检查Redis是否可用"""
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except:
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        if not self.is_available():
            return default
        
        try:
            data = self._client.get(key)
            if data is None:
                return default
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"缓存读取失败 [{key}]: {e}")
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.is_available():
            return False
        
        try:
            data = pickle.dumps(value)
            if ttl is not None:
                self._client.setex(key, ttl, data)
            else:
                self._client.set(key, data)
            return True
        except Exception as e:
            logger.error(f"缓存写入失败 [{key}]: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.is_available():
            return False
        
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"缓存删除失败 [{key}]: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if not self.is_available():
            return False
        
        try:
            return bool(self._client.exists(key))
        except Exception as e:
            logger.error(f"缓存检查失败 [{key}]: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """按模式删除缓存"""
        if not self.is_available():
            return 0
        
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"批量删除缓存失败 [{pattern}]: {e}")
            return 0
    
    # ==================== Token优化专用方法 ====================
    
    def cache_prompt(self, prompt: str, ttl: int = 3600) -> str:
        """
        缓存提示词，返回缓存键
        用于提示词蒸馏和永久缓存系统
        """
        # 生成提示词的哈希键
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        cache_key = f"prompt_cache:{prompt_hash}"
        
        if not self.exists(cache_key):
            self.set(cache_key, prompt, ttl)
            logger.debug(f"提示词已缓存: {cache_key[:20]}...")
        
        return cache_key
    
    def get_cached_prompt(self, prompt_hash: str) -> Optional[str]:
        """获取缓存的提示词"""
        cache_key = f"prompt_cache:{prompt_hash}"
        return self.get(cache_key)
    
    def cache_tool_mapping(self, tool_name: str, tool_description: str) -> str:
        """
        缓存工具ID映射
        用于工具预编译与ID映射系统
        """
        tool_id = hashlib.md5(tool_name.encode()).hexdigest()[:8]
        cache_key = f"tool_map:{tool_id}"
        
        mapping = {
            "name": tool_name,
            "description": tool_description,
            "id": tool_id
        }
        self.set(cache_key, mapping, ttl=86400)  # 24小时
        logger.debug(f"工具映射已缓存: {tool_name} -> {tool_id}")
        
        return tool_id
    
    def get_tool_name(self, tool_id: str) -> Optional[str]:
        """根据工具ID获取工具名称"""
        cache_key = f"tool_map:{tool_id}"
        mapping = self.get(cache_key)
        return mapping["name"] if mapping else None

# 全局缓存管理器实例
cache_manager = CacheManager()

# ==================== 装饰器：缓存函数结果 ====================

def cached(ttl: int = 3600, key_prefix: str = "func_cache"):
    """
    函数结果缓存装饰器
    用法：
    @cached(ttl=600, key_prefix="my_func")
    def my_function(args):
        ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key_parts = [key_prefix, func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
            cache_key = f"{key_prefix}:{cache_key}"
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {func.__name__}")
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache_manager.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

# ==================== 内存缓存备选方案 ====================

class InMemoryCache:
    """内存缓存（Redis不可用时的备选方案）"""
    
    def __init__(self):
        self._cache = {}
        self._ttl = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        import time
        if key in self._cache:
            if key in self._ttl and self._ttl[key] < time.time():
                del self._cache[key]
                del self._ttl[key]
                return default
            return self._cache[key]
        return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        import time
        self._cache[key] = value
        if ttl is not None:
            self._ttl[key] = time.time() + ttl
        return True
    
    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
        if key in self._ttl:
            del self._ttl[key]
        return True

# 根据Redis可用性选择缓存后端
if cache_manager.is_available():
    cache = cache_manager
else:
    logger.warning("使用内存缓存作为备选方案")
    cache = InMemoryCache()
