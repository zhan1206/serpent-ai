"""Multi-Level Cache - 多级缓存系统

基于内存的 LRU 缓存，支持4种缓存类型。
"""

from typing import Any, Dict, Optional


class MultiLevelCache:
    """
    多级缓存系统
    
    支持 prompt/tool/memory/model_response 四种缓存类型。
    使用显式 dict 映射，避免 getattr/setattr 动态属性名。
    """
    
    # 允许的缓存类型
    VALID_TYPES = {"prompt", "tool", "memory", "model_response"}
    
    def __init__(self):
        """初始化多级缓存"""
        self._caches: Dict[str, Dict[str, Any]] = {
            "prompt": {},
            "tool": {},
            "memory": {},
            "model_response": {},
        }
        
        self.max_sizes = {
            "prompt": 100,
            "tool": 50,
            "memory": 1000,
            "model_response": 200
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
        if cache_type not in self.VALID_TYPES:
            self.misses += 1
            return None
        
        cache = self._caches[cache_type]
        
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
        if cache_type not in self.VALID_TYPES:
            return
        
        cache = self._caches[cache_type]
        cache[key] = value
        
        max_size = self.max_sizes.get(cache_type, 100)
        while len(cache) > max_size:
            cache.popitem(last=False)
    
    def clear(self, cache_type: Optional[str] = None):
        """清空缓存"""
        if cache_type:
            if cache_type in self._caches:
                self._caches[cache_type].clear()
        else:
            for cache in self._caches.values():
                cache.clear()
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total = self.hits + self.misses
        hit_rate = self.hits / max(1, total) * 100
        
        return {
            "prompt_cache_size": len(self._caches["prompt"]),
            "tool_cache_size": len(self._caches["tool"]),
            "memory_cache_size": len(self._caches["memory"]),
            "model_response_cache_size": len(self._caches["model_response"]),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percent": hit_rate
        }
