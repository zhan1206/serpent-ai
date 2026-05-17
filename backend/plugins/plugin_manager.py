# -*- coding: utf-8 -*-
"""
插件管理器 - 插件系统的核心
负责插件发现、加载、生命周期管理和热重载
"""

import os
import sys
import importlib
import importlib.util
import logging
import threading
from typing import Dict, List, Optional, Any
from pathlib import Path

from .plugin_manifest import PluginManifest, ManifestError
from .plugin_base import Plugin, PluginContext, PluginState
from .plugin_registry import PluginRegistry, get_plugin_registry
from .plugin_security import get_global_sandbox

logger = logging.getLogger(__name__)


class PluginManager:
    """
    插件管理器
    
    核心职责：
    1. 插件发现 - 扫描插件目录，加载清单
    2. 插件加载 - 导入插件模块，创建实例
    3. 生命周期管理 - init -> start -> stop -> unload
    4. 依赖解析 - 拓扑排序，按序加载
    5. 热重载 - 重新加载插件模块
    """
    
    def __init__(self, plugin_dirs: List[str] = None):
        """
        初始化插件管理器
        
        Args:
            plugin_dirs: 插件搜索目录列表
        """
        self.plugin_dirs = plugin_dirs or []
        self.registry = get_plugin_registry()
        self.sandbox = get_global_sandbox()
        self._modules: Dict[str, Any] = {}  # name -> module
        self._module_paths: Dict[str, str] = {}  # name -> file path
        self._load_lock = threading.Lock()
        self._event_handlers: Dict[str, List] = {}
    
    def add_plugin_dir(self, directory: str):
        """
        添加插件搜索目录
        
        Args:
            directory: 目录路径
        """
        abs_dir = os.path.abspath(directory)
        if abs_dir not in self.plugin_dirs:
            self.plugin_dirs.append(abs_dir)
            logger.info(f"添加插件目录: {abs_dir}")
    
    def discover_all(self) -> List[str]:
        """
        发现所有插件
        
        扫描所有插件目录，找到包含 plugin.json 的子目录，
        加载清单并注册到注册表。
        
        Returns:
            发现的插件名称列表
        """
        discovered = []
        
        for plugin_dir in self.plugin_dirs:
            if not os.path.isdir(plugin_dir):
                logger.warning(f"插件目录不存在: {plugin_dir}")
                continue
            
            for entry in os.listdir(plugin_dir):
                entry_path = os.path.join(plugin_dir, entry)
                manifest_path = os.path.join(entry_path, "plugin.json")
                
                if os.path.isdir(entry_path) and os.path.exists(manifest_path):
                    try:
                        manifest = PluginManifest.from_file(manifest_path)
                        self.registry.register_discovered(manifest, entry_path)
                        discovered.append(manifest.name)
                        logger.debug(f"发现插件: {manifest.name} @ {entry_path}")
                    except ManifestError as e:
                        logger.warning(f"跳过插件 {entry}: {e}")
                elif os.path.isdir(entry_path):
                    # 检查是否是单文件插件（main.py + plugin.json在同一目录）
                    # 也可能是子目录的子目录
                    for sub_entry in os.listdir(entry_path):
                        sub_path = os.path.join(entry_path, sub_entry)
                        sub_manifest = os.path.join(sub_path, "plugin.json")
                        if os.path.isdir(sub_path) and os.path.exists(sub_manifest):
                            try:
                                manifest = PluginManifest.from_file(sub_manifest)
                                self.registry.register_discovered(manifest, sub_path)
                                if manifest.name not in discovered:
                                    discovered.append(manifest.name)
                            except ManifestError:
                                pass
        
        logger.info(f"插件发现完成: 发现 {len(discovered)} 个插件")
        return discovered
    
    def load_plugin(self, name: str, config: Dict[str, Any] = None) -> Plugin:
        """
        加载并初始化插件
        
        Args:
            name: 插件名称
            config: 插件配置（可选）
            
        Returns:
            插件实例
            
        Raises:
            ValueError: 插件不存在或加载失败
        """
        with self._load_lock:
            plugin_info = self.registry.get_plugin(name)
            if not plugin_info:
                raise ValueError(f"插件不存在: {name}")
            
            # 检查是否已加载
            existing = self.registry.get_instance(name)
            if existing and existing.state in (PluginState.LOADED, PluginState.INITIALIZED, PluginState.STARTED):
                logger.info(f"插件已加载: {name}")
                return existing
            
            manifest = plugin_info["manifest"]
            plugin_dir = plugin_info["directory"]
            
            # 解析依赖
            self._resolve_dependencies(name, manifest.dependencies)
            
            # 注册到沙箱
            self.sandbox.register_plugin(
                name,
                permissions=manifest.permissions,
                strict=False,
            )
            
            try:
                # 导入插件模块
                instance = self._import_plugin(name, manifest, plugin_dir)
                
                # 设置上下文
                ctx = PluginContext(plugin_name=name, sandbox=self.sandbox)
                if config:
                    ctx.config = config
                instance.set_context(ctx)
                
                # 生命周期：load -> init -> start
                instance.on_load()
                instance.on_init()
                instance.on_start()
                
                # 注册实例
                self.registry.set_instance(name, instance)
                
                # 保存配置
                if config:
                    plugin_info["config"] = config
                
                logger.info(f"插件加载成功: {name} v{manifest.version}")
                self._emit_event("plugin_loaded", {"name": name, "version": manifest.version})
                
                return instance
                
            except Exception as e:
                logger.error(f"插件加载失败 [{name}]: {e}", exc_info=True)
                self.registry.set_error(name, str(e))
                self.sandbox.record_error(name)
                raise ValueError(f"插件加载失败: {name}: {e}") from e
    
    def unload_plugin(self, name: str) -> bool:
        """
        卸载插件
        
        Args:
            name: 插件名称
            
        Returns:
            是否成功
        """
        with self._load_lock:
            instance = self.registry.get_instance(name)
            if not instance:
                logger.warning(f"插件未加载: {name}")
                return False
            
            try:
                # 生命周期：stop -> unload
                instance.on_stop()
                instance.on_unload()
                
                # 移除实例
                self.registry.remove_instance(name)
                
                # 清理模块缓存
                if name in self._modules:
                    module = self._modules[name]
                    module_name = module.__name__
                    for key in list(sys.modules.keys()):
                        if key.startswith(module_name):
                            del sys.modules[key]
                    del self._modules[name]
                    self._module_paths.pop(name, None)
                
                # 从沙箱注销
                self.sandbox.unregister_plugin(name)
                
                # 如果是ToolPlugin，移除注册的工具
                from backend.tools.tool_registry import get_global_registry
                registry = get_global_registry()
                if hasattr(instance, "get_tools"):
                    try:
                        tools = instance.get_tools()
                        for tool in tools:
                            registry.remove_tool(tool["name"])
                    except Exception:
                        pass
                
                logger.info(f"插件卸载成功: {name}")
                self._emit_event("plugin_unloaded", {"name": name})
                return True
                
            except Exception as e:
                logger.error(f"插件卸载失败 [{name}]: {e}")
                return False
    
    def reload_plugin(self, name: str) -> Plugin:
        """
        热重载插件
        
        先卸载再重新加载，保留配置
        
        Args:
            name: 插件名称
            
        Returns:
            新的插件实例
        """
        plugin_info = self.registry.get_plugin(name)
        if not plugin_info:
            raise ValueError(f"插件不存在: {name}")
        
        config = plugin_info.get("config", {})
        self.unload_plugin(name)
        
        # 重新扫描清单（可能已更新）
        manifest_path = os.path.join(plugin_info["directory"], "plugin.json")
        if os.path.exists(manifest_path):
            try:
                manifest = PluginManifest.from_file(manifest_path)
                self.registry.register_discovered(manifest, plugin_info["directory"])
            except ManifestError:
                pass
        
        instance = self.load_plugin(name, config)
        logger.info(f"插件热重载成功: {name}")
        self._emit_event("plugin_reloaded", {"name": name})
        return instance
    
    def start_all(self):
        """启动所有已发现的插件"""
        plugins = self.registry.list_plugins()
        for plugin in plugins:
            if plugin["state"] == PluginState.UNLOADED.value:
                try:
                    self.load_plugin(plugin["name"])
                except Exception as e:
                    logger.error(f"自动启动插件失败 [{plugin['name']}]: {e}")
    
    def stop_all(self):
        """停止所有已启动的插件"""
        for name in list(self.registry.list_started()):
            try:
                self.unload_plugin(name)
            except Exception as e:
                logger.error(f"停止插件失败 [{name}]: {e}")
    
    def _import_plugin(self, name: str, manifest: PluginManifest,
                       plugin_dir: str) -> Plugin:
        """
        导入插件模块并创建实例
        
        Args:
            name: 插件名称
            manifest: 插件清单
            plugin_dir: 插件目录
            
        Returns:
            插件实例
        """
        entry_point = manifest.entry_point
        entry_path = os.path.join(plugin_dir, entry_point)
        
        if not os.path.exists(entry_path):
            raise FileNotFoundError(f"插件入口文件不存在: {entry_path}")
        
        # 创建唯一的模块名，避免冲突
        module_name = f"serpentai_plugins.{name}.main"
        
        # 使用 importlib 加载模块
        spec = importlib.util.spec_from_file_location(module_name, entry_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法创建模块规格: {entry_path}")
        
        module = importlib.util.module_from_spec(spec)
        
        # 确保插件目录在 sys.path 中
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)
        
        # 在独立的命名空间中执行模块
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # 查找插件类 - 模块应导出 create_plugin 函数或 Plugin 子类
        instance = None
        
        # 方式1：通过 create_plugin 工厂函数
        if hasattr(module, "create_plugin"):
            instance = module.create_plugin(manifest)
        # 方式2：通过模块中的 Plugin 子类
        else:
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) 
                    and issubclass(attr, Plugin) 
                    and attr is not Plugin
                    and not attr.__name__.startswith("_")):
                    instance = attr(manifest)
                    break
        
        if instance is None:
            raise ValueError(
                f"插件 {name} 未导出有效的插件类或 create_plugin 函数。"
                f"请确保模块中定义了 Plugin 子类或 create_plugin(manifest) 工厂函数。"
            )
        
        self._modules[name] = module
        self._module_paths[name] = entry_path
        
        return instance
    
    def _resolve_dependencies(self, name: str, deps: Dict[str, str]):
        """
        解析插件依赖
        
        Args:
            name: 插件名称
            deps: 依赖字典 {插件名: 版本范围}
            
        Raises:
            ValueError: 依赖不满足
        """
        for dep_name, version_range in deps.items():
            dep_info = self.registry.get_plugin(dep_name)
            
            if not dep_info:
                raise ValueError(
                    f"插件 {name} 依赖 {dep_name}，但该插件未发现。"
                )
            
            dep_instance = self.registry.get_instance(dep_name)
            if not dep_instance:
                # 尝试自动加载依赖
                try:
                    self.load_plugin(dep_name)
                except Exception as e:
                    raise ValueError(
                        f"插件 {name} 依赖 {dep_name}，自动加载失败: {e}"
                    )
            
            # 检查版本
            dep_info_check = self.registry.get_plugin(dep_name)
            if dep_info_check:
                dep_manifest = dep_info_check["manifest"]
                if not dep_manifest.matches_version(version_range):
                    raise ValueError(
                        f"插件 {name} 依赖 {dep_name} {version_range}，"
                        f"但当前版本为 {dep_manifest.version}"
                    )
    
    def _emit_event(self, event: str, data: Dict = None):
        """发送插件系统事件"""
        for handler in self._event_handlers.get(event, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"事件处理器错误 ({event}): {e}")
    
    def on(self, event: str, handler):
        """注册事件处理器"""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)


# 全局管理器实例
_manager_instance = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = PluginManager()
    return _manager_instance
