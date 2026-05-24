"""Multi-Level Cache - 多级缓存系统"""

from typing import Any, Dict, Optional


class MultiLevelCache:
    """
    多级缓存系统
    提示词缓存、工具缓存、记忆缓存、模型响应缓存
    """
    
    def __init__(self):
        """初始化多级缓存"""
        # LRU缓存
        self.prompt_cache: Dict[str, Any] = {}
        self.tool_cache: Dict[str, Any] = {}
        self.memory_cache: Dict[str, Any] = {}
        self.model_response_cache: Dict[str, Any] = {}
        
        # 缓存配置
        self.max_sizes = {
            "prompt": 100,      # 最多100个提示词缓存
            "tool": 50,        # 最多50个工具缓存
            "memory": 1000,   # 最多1000条记忆缓存
            "model_response": 200  # 最多200个模型响应缓存
        }
        
        self.hits = 0
        self.misses = 0
    
    def get(self, cache_type: str, key: str) -> Optional[Any]:
        """
        从缓存获取
        
        Args:
            cache_type: 缓存类型 (prompt/tool/memory/model_response)
            key: 缓存键
            
        Returns:
            缓存的值，如果没有则返回None
        """
        cache = getattr(self, f"{cache_type}_cache", {})
        
        if key in cache:
            self.hits += 1
            # 移到末尾（LRU）
            cache[key] = cache.pop(key)
            return cache[key]
        
        self.misses += 1
        return None
    
    def set(self, cache_type: str, key: str, value: Any):
        """
        设置缓存
        
        Args:
            cache_type: 缓存类型
            key: 缓存键
            value: 缓存值
        """
        cache = getattr(self, f"{cache_type}_cache", {})
        
        # 添加到缓存
        cache[key] = value
        
        # 检查大小并移除最旧的
        max_size = self.max_sizes.get(cache_type, 100)
        while len(cache) > max_size:
            # 移除第一个（最旧的）
            cache.popitem(last=False)
    
    def clear(self, cache_type: Optional[str] = None):
        """
        清空缓存
        
        Args:
            cache_type: 缓存类型，不提供则清空所有
        """
        if cache_type:
            cache = getattr(self, f"{cache_type}_cache", {})
            cache.clear()
        else:
            self.prompt_cache.clear()
            self.tool_cache.clear()
            self.memory_cache.clear()
            self.model_response_cache.clear()
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total = self.hits + self.misses
        hit_rate = self.hits / max(1, total) * 100
        
        return {
            "prompt_cache_size": len(self.prompt_cache),
            "tool_cache_size": len(self.tool_cache),
            "memory_cache_size": len(self.memory_cache),
            "model_response_cache_size": len(self.model_response_cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percent": hit_rate
        }
