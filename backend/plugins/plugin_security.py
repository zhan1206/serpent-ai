# -*- coding: utf-8 -*-
"""
插件安全沙箱 - 资源限制与权限控制
防止恶意插件越权访问系统资源
"""

import os
import time
import logging
import threading
# resource module is Unix-only; use fallback on Windows
try:
    import resource as res_module
except ImportError:
    res_module = None
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict

logger = logging.getLogger(__name__)


class Permission(Enum):
    """权限枚举"""
    NETWORK = "network"
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    CLIPBOARD = "clipboard"
    NOTIFICATION = "notification"
    DATABASE = "database"
    SHELL = "shell"
    CAMERA = "camera"
    MICROPHONE = "microphone"
    LOCATION = "location"
    CONTACTS = "contacts"
    CALENDAR = "calendar"
    TOOL_REGISTER = "tool_register"
    MODEL_REGISTER = "model_register"
    GATEWAY_REGISTER = "gateway_register"
    HOOK_REGISTER = "hook_register"


@dataclass
class ResourceLimits:
    """
    插件资源限制配置
    
    Attributes:
        max_memory_mb: 最大内存使用量（MB）
        max_cpu_percent: 最大CPU使用率百分比
        max_execution_time: 单次执行最大时长（秒）
        max_file_size_mb: 最大文件大小（MB）
        max_network_calls: 最大网络调用次数（0为不限制）
        max_filesystem_ops: 最大文件系统操作次数（0为不限制）
        allowed_paths: 允许访问的文件路径列表（空列表表示所有路径）
        blocked_paths: 禁止访问的文件路径列表
        allowed_hosts: 允许连接的网络主机列表（空列表表示所有主机）
        blocked_hosts: 禁止连接的网络主机列表
    """
    max_memory_mb: int = 256
    max_cpu_percent: int = 50
    max_execution_time: float = 30.0
    max_file_size_mb: int = 100
    max_network_calls: int = 100
    max_filesystem_ops: int = 1000
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=lambda: [
        "/etc/passwd", "/etc/shadow", "/etc/sudoers",
        "C:\\Windows\\System32", "C:\\Windows\\SysWOW64",
    ])
    allowed_hosts: List[str] = field(default_factory=list)
    blocked_hosts: List[str] = field(default_factory=list)


@dataclass
class PluginUsageStats:
    """插件使用统计"""
    memory_bytes: int = 0
    cpu_time_seconds: float = 0.0
    execution_count: int = 0
    network_calls: int = 0
    filesystem_ops: int = 0
    errors: int = 0
    last_execution_time: float = 0.0
    total_execution_time: float = 0.0


class PluginSandbox:
    """
    插件安全沙箱
    
    管理插件的权限检查、资源限制和使用统计
    """
    
    # 权限到清单权限字符串的映射
    PERMISSION_MAP = {
        Permission.NETWORK: "network",
        Permission.FILESYSTEM_READ: "filesystem",
        Permission.FILESYSTEM_WRITE: "filesystem",
        Permission.CLIPBOARD: "clipboard",
        Permission.NOTIFICATION: "notification",
        Permission.DATABASE: "database",
        Permission.SHELL: "shell",
        Permission.CAMERA: "camera",
        Permission.MICROPHONE: "microphone",
        Permission.LOCATION: "location",
        Permission.CONTACTS: "contacts",
        Permission.CALENDAR: "calendar",
    }
    
    # 默认资源限制
    DEFAULT_LIMITS = ResourceLimits()
    
    # 严格资源限制（用于不受信任的插件）
    STRICT_LIMITS = ResourceLimits(
        max_memory_mb=64,
        max_cpu_percent=25,
        max_execution_time=10.0,
        max_file_size_mb=10,
        max_network_calls=20,
        max_filesystem_ops=100,
    )
    
    def __init__(self):
        self._plugin_permissions: Dict[str, Set[Permission]] = {}
        self._plugin_limits: Dict[str, ResourceLimits] = {}
        self._plugin_stats: Dict[str, PluginUsageStats] = {}
        self._lock = threading.Lock()
        self._audit_log: List[Dict[str, Any]] = []
    
    def register_plugin(self, plugin_name: str,
                       permissions: List[str] = None,
                       strict: bool = False):
        """
        注册插件到沙箱
        
        Args:
            plugin_name: 插件名称
            permissions: 权限列表（对应清单中的权限字符串）
            strict: 是否使用严格限制
        """
        with self._lock:
            # 解析权限
            perm_set = set()
            if permissions:
                for perm_str in permissions:
                    for perm, perm_name in self.PERMISSION_MAP.items():
                        if perm_name == perm_str:
                            perm_set.add(perm)
            
            # 始终授予注册权限（根据插件类型）
            perm_set.add(Permission.TOOL_REGISTER)
            
            self._plugin_permissions[plugin_name] = perm_set
            self._plugin_limits[plugin_name] = (
                self.STRICT_LIMITS if strict else self.DEFAULT_LIMITS
            )
            self._plugin_stats[plugin_name] = PluginUsageStats()
            
            logger.info(
                f"沙箱注册插件: {plugin_name} | "
                f"权限: {[p.value for p in perm_set]} | "
                f"严格模式: {strict}"
            )
    
    def unregister_plugin(self, plugin_name: str):
        """
        从沙箱注销插件
        
        Args:
            plugin_name: 插件名称
        """
        with self._lock:
            self._plugin_permissions.pop(plugin_name, None)
            self._plugin_limits.pop(plugin_name, None)
            self._plugin_stats.pop(plugin_name, None)
    
    def check_permission(self, plugin_name: str, permission: Permission) -> bool:
        """
        检查插件是否拥有指定权限
        
        Args:
            plugin_name: 插件名称
            permission: 要检查的权限
            
        Returns:
            是否有权限
        """
        perms = self._plugin_permissions.get(plugin_name, set())
        has = permission in perms
        if not has:
            self._audit(
                plugin_name, "permission_denied",
                {"permission": permission.value}
            )
            logger.warning(
                f"权限拒绝: {plugin_name} 请求 {permission.value}"
            )
        return has
    
    def check_filesystem_access(self, plugin_name: str, path: str,
                                write: bool = False) -> bool:
        """
        检查文件系统访问权限
        
        Args:
            plugin_name: 插件名称
            path: 文件路径
            write: 是否为写操作
            
        Returns:
            是否允许访问
        """
        required = Permission.FILESYSTEM_WRITE if write else Permission.FILESYSTEM_READ
        if not self.check_permission(plugin_name, required):
            return False
        
        limits = self._plugin_limits.get(plugin_name, self.DEFAULT_LIMITS)
        norm_path = os.path.normpath(os.path.abspath(path))
        
        # 检查黑名单
        for blocked in limits.blocked_paths:
            blocked_norm = os.path.normpath(os.path.abspath(blocked))
            if norm_path.startswith(blocked_norm):
                self._audit(
                    plugin_name, "filesystem_blocked",
                    {"path": path, "reason": "blocked_path"}
                )
                logger.warning(f"文件系统访问被阻止: {plugin_name} -> {path}")
                return False
        
        # 检查白名单（如果设置了）
        if limits.allowed_paths:
            allowed = False
            for allow_path in limits.allowed_paths:
                allow_norm = os.path.normpath(os.path.abspath(allow_path))
                if norm_path.startswith(allow_norm):
                    allowed = True
                    break
            if not allowed:
                self._audit(
                    plugin_name, "filesystem_blocked",
                    {"path": path, "reason": "not_in_allowed_paths"}
                )
                return False
        
        # 更新使用统计
        stats = self._plugin_stats.get(plugin_name)
        if stats:
            stats.filesystem_ops += 1
        
        return True
    
    def check_network_access(self, plugin_name: str, host: str) -> bool:
        """
        检查网络访问权限
        
        Args:
            plugin_name: 插件名称
            host: 目标主机
            
        Returns:
            是否允许访问
        """
        if not self.check_permission(plugin_name, Permission.NETWORK):
            return False
        
        limits = self._plugin_limits.get(plugin_name, self.DEFAULT_LIMITS)
        
        # 检查网络调用限制
        stats = self._plugin_stats.get(plugin_name)
        if stats and limits.max_network_calls > 0:
            if stats.network_calls >= limits.max_network_calls:
                self._audit(
                    plugin_name, "network_limit",
                    {"host": host, "reason": "max_calls_reached"}
                )
                return False
        
        # 检查主机黑名单
        for blocked in limits.blocked_hosts:
            if blocked in host:
                self._audit(
                    plugin_name, "network_blocked",
                    {"host": host, "reason": "blocked_host"}
                )
                return False
        
        # 更新统计
        if stats:
            stats.network_calls += 1
        
        return True
    
    def record_execution(self, plugin_name: str, duration: float = 0.0):
        """
        记录插件执行
        
        Args:
            plugin_name: 插件名称
            duration: 执行时长（秒）
        """
        stats = self._plugin_stats.get(plugin_name)
        if stats:
            stats.execution_count += 1
            stats.last_execution_time = duration
            stats.total_execution_time += duration
    
    def record_error(self, plugin_name: str):
        """记录插件错误"""
        stats = self._plugin_stats.get(plugin_name)
        if stats:
            stats.errors += 1
    
    def check_execution_time(self, plugin_name: str, elapsed: float) -> bool:
        """
        检查执行时间是否超限
        
        Args:
            plugin_name: 插件名称
            elapsed: 已执行时长（秒）
            
        Returns:
            是否在限制内
        """
        limits = self._plugin_limits.get(plugin_name, self.DEFAULT_LIMITS)
        if elapsed > limits.max_execution_time:
            self._audit(
                plugin_name, "execution_timeout",
                {"elapsed": elapsed, "limit": limits.max_execution_time}
            )
            return False
        return True
    
    def get_stats(self, plugin_name: str) -> Optional[PluginUsageStats]:
        """获取插件使用统计"""
        return self._plugin_stats.get(plugin_name)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有插件使用统计"""
        result = {}
        for name, stats in self._plugin_stats.items():
            result[name] = {
                "execution_count": stats.execution_count,
                "network_calls": stats.network_calls,
                "filesystem_ops": stats.filesystem_ops,
                "errors": stats.errors,
                "total_execution_time": round(stats.total_execution_time, 2),
                "last_execution_time": round(stats.last_execution_time, 2),
            }
        return result
    
    def get_limits(self, plugin_name: str) -> ResourceLimits:
        """获取插件资源限制"""
        return self._plugin_limits.get(plugin_name, self.DEFAULT_LIMITS)
    
    def _audit(self, plugin_name: str, action: str, details: Dict = None):
        """记录审计日志"""
        entry = {
            "timestamp": time.time(),
            "plugin": plugin_name,
            "action": action,
            "details": details or {},
        }
        self._audit_log.append(entry)
        # 限制审计日志长度
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]
    
    def get_audit_log(self, plugin_name: str = None,
                     limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取审计日志
        
        Args:
            plugin_name: 插件名称（None返回所有）
            limit: 最大条数
        """
        logs = self._audit_log
        if plugin_name:
            logs = [e for e in logs if e["plugin"] == plugin_name]
        return logs[-limit:]


# 全局沙箱实例
_sandbox_instance = None


def get_global_sandbox() -> PluginSandbox:
    """获取全局沙箱实例"""
    global _sandbox_instance
    if _sandbox_instance is None:
        _sandbox_instance = PluginSandbox()
    return _sandbox_instance
