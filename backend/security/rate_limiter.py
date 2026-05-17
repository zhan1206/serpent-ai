"""
SerpentAI 安全模块 - 速率限制器 (Layer 2)
防止DDoS和暴力破解
"""

import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging
import threading

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """速率限制结果"""
    allowed: bool
    current_count: int
    limit: int
    remaining: int
    reset_at: Optional[datetime]
    retry_after: Optional[int]  # 秒
    
    def to_dict(self) -> Dict:
        return {
            "allowed": self.allowed,
            "current_count": self.current_count,
            "limit": self.limit,
            "remaining": self.remaining,
            "reset_at": self.reset_at.isoformat() if self.reset_at else None,
            "retry_after": self.retry_after
        }


class RateLimitRule:
    """速率限制规则"""
    
    def __init__(
        self,
        name: str,
        limit: int,
        window_seconds: int,
        block_duration_seconds: int = 0
    ):
        """
        Args:
            name: 规则名称
            limit: 允许的最大请求数
            window_seconds: 时间窗口（秒）
            block_duration_seconds: 超出限制后阻止的时间（秒）
        """
        self.name = name
        self.limit = limit
        self.window_seconds = window_seconds
        self.block_duration_seconds = block_duration_seconds


class RateLimiter:
    """
    速率限制器 - 第二层防御
    功能：
    1. 基于时间窗口的限流
    2. 用户级别限制
    3. IP级别限制
    4. 操作级别限制
    5. 智能封禁
    """
    
    # 默认规则
    DEFAULT_RULES = {
        "global": RateLimitRule("global", limit=1000, window_seconds=60),
        "login": RateLimitRule("login", limit=5, window_seconds=300, block_duration_seconds=900),
        "api": RateLimitRule("api", limit=100, window_seconds=60),
        "chat": RateLimitRule("chat", limit=10, window_seconds=60),
        "tool_execute": RateLimitRule("tool_execute", limit=50, window_seconds=60),
        "file_upload": RateLimitRule("file_upload", limit=10, window_seconds=300),
    }
    
    def __init__(self):
        # 规则
        self._rules: Dict[str, RateLimitRule] = self.DEFAULT_RULES.copy()
        
        # 请求记录: key -> [(timestamp, count), ...]
        self._requests: Dict[str, list] = {}
        
        # 封禁记录: key -> blocked_until
        self._blocked: Dict[str, datetime] = {}
        
        # 锁
        self._lock = threading.Lock()
        
        # 清理配置
        self._cleanup_interval = 300  # 5分钟清理一次
        self._last_cleanup = time.time()
        
        logger.info("速率限制器初始化完成")
    
    def check(self, user_id: str, operation: str = "global") -> RateLimitResult:
        """
        检查请求是否允许
        
        Args:
            user_id: 用户ID
            operation: 操作类型
        
        Returns:
            RateLimitResult: 检查结果
        """
        with self._lock:
            # 清理过期记录
            self._maybe_cleanup()
            
            key = f"{user_id}:{operation}"
            
            # 检查是否被封禁
            if key in self._blocked:
                blocked_until = self._blocked[key]
                if datetime.now() < blocked_until:
                    retry_after = int((blocked_until - datetime.now()).total_seconds())
                    return RateLimitResult(
                        allowed=False,
                        current_count=0,
                        limit=0,
                        remaining=0,
                        reset_at=blocked_until,
                        retry_after=retry_after
                    )
                else:
                    # 解除封禁
                    del self._blocked[key]
            
            # 获取规则
            rule = self._rules.get(operation, self._rules["global"])
            
            # 获取请求历史
            if key not in self._requests:
                self._requests[key] = []
            
            now = time.time()
            window_start = now - rule.window_seconds
            
            # 清理窗口外的请求
            self._requests[key] = [t for t in self._requests[key] if t > window_start]
            
            current_count = len(self._requests[key])
            
            # 检查限制
            if current_count >= rule.limit:
                # 超出限制
                if rule.block_duration_seconds > 0:
                    # 封禁
                    self._blocked[key] = datetime.now() + timedelta(
                        seconds=rule.block_duration_seconds
                    )
                    logger.warning(
                        f"用户 {user_id} 因操作 {operation} 超出速率限制被封禁 "
                        f"{rule.block_duration_seconds} 秒"
                    )
                
                reset_at = datetime.fromtimestamp(
                    self._requests[key][0] + rule.window_seconds
                )
                retry_after = int(reset_at.timestamp() - now)
                
                return RateLimitResult(
                    allowed=False,
                    current_count=current_count,
                    limit=rule.limit,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=retry_after if retry_after > 0 else 1
                )
            
            # 记录请求
            self._requests[key].append(now)
            
            return RateLimitResult(
                allowed=True,
                current_count=current_count + 1,
                limit=rule.limit,
                remaining=rule.limit - current_count - 1,
                reset_at=datetime.fromtimestamp(now + rule.window_seconds),
                retry_after=None
            )
    
    def check_ip(self, ip_address: str, operation: str = "global") -> RateLimitResult:
        """
        检查IP是否允许
        
        Args:
            ip_address: IP地址
            operation: 操作类型
        
        Returns:
            RateLimitResult: 检查结果
        """
        # IP级别使用更严格的限制
        return self.check(f"ip:{ip_address}", operation)
    
    def check_global(self, identifier: str) -> RateLimitResult:
        """
        全局限流检查
        
        Args:
            identifier: 标识符（用户ID、IP等）
        
        Returns:
            RateLimitResult: 检查结果
        """
        return self.check(identifier, "global")
    
    def _maybe_cleanup(self):
        """定期清理过期记录"""
        now = time.time()
        
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = now
        
        # 清理过期的请求记录
        for key in list(self._requests.keys()):
            window_start = now - self._rules.get(
                key.split(":")[-1], self._rules["global"]
            ).window_seconds
            
            self._requests[key] = [t for t in self._requests[key] if t > window_start]
            
            # 删除空记录
            if not self._requests[key]:
                del self._requests[key]
        
        # 清理过期的封禁记录
        for key in list(self._blocked.keys()):
            if datetime.now() >= self._blocked[key]:
                del self._blocked[key]
    
    def get_remaining(self, user_id: str, operation: str = "global") -> int:
        """获取剩余请求次数"""
        with self._lock:
            key = f"{user_id}:{operation}"
            
            if key not in self._requests:
                rule = self._rules.get(operation, self._rules["global"])
                return rule.limit
            
            now = time.time()
            rule = self._rules.get(operation, self._rules["global"])
            window_start = now - rule.window_seconds
            
            current = len([t for t in self._requests[key] if t > window_start])
            
            return max(0, rule.limit - current)
    
    def reset(self, user_id: str, operation: str = None):
        """重置用户的速率限制计数"""
        with self._lock:
            if operation:
                key = f"{user_id}:{operation}"
                if key in self._requests:
                    del self._requests[key]
                if key in self._blocked:
                    del self._blocked[key]
            else:
                # 重置所有
                keys_to_remove = [k for k in self._requests.keys() if k.startswith(f"{user_id}:")]
                for key in keys_to_remove:
                    del self._requests[key]
                    if key in self._blocked:
                        del self._blocked[key]
    
    def unblock(self, user_id: str, operation: str = None):
        """解除用户的封禁"""
        with self._lock:
            if operation:
                key = f"{user_id}:{operation}"
                if key in self._blocked:
                    del self._blocked[key]
            else:
                keys_to_remove = [k for k in self._blocked.keys() if k.startswith(f"{user_id}:")]
                for key in keys_to_remove:
                    del self._blocked[key]
    
    def add_rule(self, rule: RateLimitRule):
        """添加自定义规则"""
        self._rules[rule.name] = rule
        logger.info(f"速率限制规则已添加: {rule.name}")
    
    def remove_rule(self, name: str) -> bool:
        """移除规则"""
        if name in self.DEFAULT_RULES:
            logger.warning(f"不能移除默认规则: {name}")
            return False
        
        if name in self._rules:
            del self._rules[name]
            logger.info(f"速率限制规则已移除: {name}")
            return True
        
        return False
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            return {
                "total_keys": len(self._requests),
                "blocked_keys": len(self._blocked),
                "rules_count": len(self._rules),
                "rules": {
                    name: {
                        "limit": rule.limit,
                        "window_seconds": rule.window_seconds,
                        "block_duration_seconds": rule.block_duration_seconds
                    }
                    for name, rule in self._rules.items()
                }
            }
