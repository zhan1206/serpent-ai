# -*- coding: utf-8 -*-
"""
插件注册表 - 跟踪所有已安装和已加载的插件
管理插件状态、发现和查询
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .plugin_manifest import PluginManifest
from .plugin_base import Plugin, PluginState
from .plugin_security import PluginSandbox

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    插件注册表
    
    维护所有已知插件的信息，包括：
    - 已发现但未加载的插件
    - 已加载的插件实例
    - 插件状态跟踪
    - 插件持久化元数据
    """
    
    def __init__(self, sandbox: Optional[PluginSandbox] = None):
        """
        初始化注册表
        
        Args:
            sandbox: 安全沙箱实例
        """
        self.sandbox = sandbox
        self._plugins: Dict[str, Dict[str, Any]] = {}  # name -> plugin_info
        self._instances: Dict[str, Plugin] = {}  # name -> Plugin instance
        self._lock = __import__("threading").Lock()
    
    def register_discovered(self, manifest: PluginManifest, plugin_dir: str):
        """
        注册一个已发现的插件
        
        Args:
            manifest: 插件清单
            plugin_dir: 插件目录路径
        """
        with self._lock:
            name = manifest.name
            if name not in self._plugins:
                self._plugins[name] = {
                    "manifest": manifest,
                    "directory": plugin_dir,
                    "state": PluginState.UNLOADED.value,
                    "loaded_at": None,
                    "error": None,
                    "config": {},
                }
                logger.info(f"发现插件: {name} v{manifest.version} @ {plugin_dir}")
            else:
                # 更新已存在的插件信息
                self._plugins[name]["manifest"] = manifest
                self._plugins[name]["directory"] = plugin_dir
    
    def set_instance(self, plugin_name: str, instance: Plugin):
        """
        设置插件实例
        
        Args:
            plugin_name: 插件名称
            instance: 插件实例
        """
        with self._lock:
            self._instances[plugin_name] = instance
            if plugin_name in self._plugins:
                self._plugins[plugin_name]["state"] = instance.state.value
                self._plugins[plugin_name]["loaded_at"] = datetime.now().isoformat()
    
    def remove_instance(self, plugin_name: str):
        """移除插件实例"""
        with self._lock:
            self._instances.pop(plugin_name, None)
            if plugin_name in self._plugins:
                self._plugins[plugin_name]["state"] = PluginState.UNLOADED.value
                self._plugins[plugin_name]["loaded_at"] = None
    
    def update_state(self, plugin_name: str, state: PluginState):
        """更新插件状态"""
        with self._lock:
            if plugin_name in self._plugins:
                self._plugins[plugin_name]["state"] = state.value
    
    def set_error(self, plugin_name: str, error: str):
        """记录插件错误"""
        with self._lock:
            if plugin_name in self._plugins:
                self._plugins[plugin_name]["state"] = PluginState.ERROR.value
                self._plugins[plugin_name]["error"] = error
    
    def get_plugin(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        获取插件信息
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            插件信息字典，不存在返回None
        """
        return self._plugins.get(plugin_name)
    
    def get_instance(self, plugin_name: str) -> Optional[Plugin]:
        """获取插件实例"""
        return self._instances.get(plugin_name)
    
    def list_plugins(self, state: Optional[str] = None,
                    plugin_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有已知插件
        
        Args:
            state: 按状态过滤
            plugin_type: 按类型过滤
            
        Returns:
            插件信息列表
        """
        plugins = []
        for name, info in self._plugins.items():
            if state and info["state"] != state:
                continue
            manifest = info["manifest"]
            if plugin_type and manifest.plugin_type != plugin_type:
                continue
            plugins.append(self._format_plugin_info(name, info))
        return plugins
    
    def list_loaded(self) -> List[str]:
        """列出已加载的插件名称"""
        return [
            name for name, info in self._plugins.items()
            if info["state"] in (PluginState.LOADED.value,
                                  PluginState.INITIALIZED.value,
                                  PluginState.STARTED.value)
        ]
    
    def list_started(self) -> List[str]:
        """列出已启动的插件名称"""
        return [
            name for name, info in self._plugins.items()
            if info["state"] == PluginState.STARTED.value
        ]
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索插件
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的插件列表
        """
        query = query.lower()
        results = []
        for name, info in self._plugins.items():
            manifest = info["manifest"]
            searchable = f"{name} {manifest.description} {' '.join(manifest.tags)} {manifest.author}".lower()
            if query in searchable:
                results.append(self._format_plugin_info(name, info))
        return results
    
    def get_plugin_count(self) -> Dict[str, int]:
        """获取插件统计"""
        stats = {"total": len(self._plugins), "loaded": 0, "started": 0, "error": 0}
        for info in self._plugins.values():
            if info["state"] in (PluginState.LOADED.value, PluginState.INITIALIZED.value, PluginState.STARTED.value):
                stats["loaded"] += 1
            if info["state"] == PluginState.STARTED.value:
                stats["started"] += 1
            if info["state"] == PluginState.ERROR.value:
                stats["error"] += 1
        return stats
    
    def _format_plugin_info(self, name: str, info: Dict) -> Dict[str, Any]:
        """格式化插件信息用于API返回"""
        manifest = info["manifest"]
        return {
            "name": name,
            "version": manifest.version,
            "type": manifest.plugin_type,
            "description": manifest.description,
            "author": manifest.author,
            "license": manifest.license,
            "tags": manifest.tags,
            "state": info["state"],
            "loaded_at": info["loaded_at"],
            "error": info["error"],
            "directory": info["directory"],
            "dependencies": manifest.dependencies,
            "permissions": manifest.permissions,
        }

# 全局注册表实例
_registry_instance = None


def get_plugin_registry() -> PluginRegistry:
    """获取全局插件注册表"""
    global _registry_instance
    if _registry_instance is None:
        from .plugin_security import get_global_sandbox
        _registry_instance = PluginRegistry(sandbox=get_global_sandbox())
    return _registry_instance
