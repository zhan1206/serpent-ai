# -*- coding: utf-8 -*-
"""
插件基类 - 定义插件的抽象接口
包含 Plugin、ToolPlugin、ModelPlugin、GatewayPlugin、HookPlugin 五种基类
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from .plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)


class PluginState(Enum):
    """插件状态枚举"""
    UNLOADED = "unloaded"       # 未加载
    LOADED = "loaded"           # 已加载（模块已导入）
    INITIALIZED = "initialized" # 已初始化（on_init 已调用）
    STARTED = "started"         # 已启动（on_start 已调用）
    STOPPED = "stopped"         # 已停止
    ERROR = "error"             # 错误状态


class PluginContext:
    """
    插件运行上下文
    提供插件与系统交互的接口
    """
    
    def __init__(self, plugin_name: str, sandbox=None):
        self.plugin_name = plugin_name
        self.sandbox = sandbox
        self._config: Dict[str, Any] = {}
        self._data: Dict[str, Any] = {}
        self._handlers: Dict[str, List[Callable]] = {}
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取插件配置"""
        return self._config
    
    @config.setter
    def config(self, value: Dict[str, Any]):
        self._config = value
    
    @property
    def data(self) -> Dict[str, Any]:
        """获取插件私有数据存储"""
        return self._data
    
    def get_tool_registry(self):
        """获取工具注册表"""
        from backend.tools.tool_registry import get_global_registry
        return get_global_registry()
    
    def get_settings(self):
        """获取全局配置"""
        from backend.core.config import get_settings
        return get_settings()
    
    def emit(self, event: str, data: Any = None):
        """
        发送事件
        
        Args:
            event: 事件名称
            data: 事件数据
        """
        logger.debug(f"[{self.plugin_name}] 发送事件: {event}")
        handlers = self._handlers.get(event, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"[{self.plugin_name}] 事件处理器错误 ({event}): {e}")
    
    def on(self, event: str, handler: Callable):
        """
        注册事件处理器
        
        Args:
            event: 事件名称
            handler: 处理函数
        """
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)
    
    def off(self, event: str, handler: Optional[Callable] = None):
        """
        移除事件处理器
        
        Args:
            event: 事件名称
            handler: 要移除的处理函数（None则移除该事件所有处理器）
        """
        if handler:
            handlers = self._handlers.get(event, [])
            if handler in handlers:
                handlers.remove(handler)
        else:
            self._handlers.pop(event, None)


class Plugin(ABC):
    """
    插件基类
    所有插件必须继承此类并实现生命周期方法
    """
    
    def __init__(self, manifest: PluginManifest):
        """
        初始化插件
        
        Args:
            manifest: 插件清单
        """
        self.manifest = manifest
        self.state = PluginState.UNLOADED
        self.context: Optional[PluginContext] = None
        self._logger = logging.getLogger(f"plugin.{manifest.name}")
    
    @property
    def name(self) -> str:
        """插件名称"""
        return self.manifest.name
    
    @property
    def version(self) -> str:
        """插件版本"""
        return self.manifest.version
    
    @property
    def description(self) -> str:
        """插件描述"""
        return self.manifest.description
    
    def set_context(self, context: PluginContext):
        """设置插件运行上下文"""
        self.context = context
    
    def on_load(self):
        """
        插件加载时调用（模块导入后）
        用于注册工具、模型等资源
        """
        self.state = PluginState.LOADED
        self._logger.info(f"插件已加载: {self.name} v{self.version}")
    
    def on_init(self):
        """
        插件初始化时调用
        用于初始化插件内部状态
        """
        self.state = PluginState.INITIALIZED
        self._logger.info(f"插件已初始化: {self.name}")
    
    def on_start(self):
        """
        插件启动时调用
        用于启动后台任务、连接外部服务等
        """
        self.state = PluginState.STARTED
        self._logger.info(f"插件已启动: {self.name}")
    
    def on_stop(self):
        """
        插件停止时调用
        用于清理后台任务、断开连接等
        """
        self.state = PluginState.STOPPED
        self._logger.info(f"插件已停止: {self.name}")
    
    def on_unload(self):
        """
        插件卸载时调用
        用于释放所有资源
        """
        self.state = PluginState.UNLOADED
        self._logger.info(f"插件已卸载: {self.name}")
    
    def on_error(self, error: Exception):
        """
        插件错误回调
        
        Args:
            error: 错误对象
        """
        self.state = PluginState.ERROR
        self._logger.error(f"插件错误 [{self.name}]: {error}", exc_info=True)
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取插件信息
        
        Returns:
            插件元数据字典
        """
        return {
            "name": self.name,
            "version": self.version,
            "type": self.manifest.plugin_type,
            "description": self.description,
            "author": self.manifest.author,
            "license": self.manifest.license,
            "state": self.state.value,
            "tags": self.manifest.tags,
            "permissions": self.manifest.permissions,
            "dependencies": self.manifest.dependencies,
        }


class ToolPlugin(Plugin):
    """
    工具插件基类
    提供自定义工具给SerpentAI调用
    """
    
    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        获取插件提供的工具列表
        
        Returns:
            工具元数据列表，每个工具包含:
            - name: 工具名称
            - description: 工具描述
            - input_schema: JSON Schema 格式的输入参数定义
            - handler: 工具执行函数
            
        示例:
            return [{
                "name": "my_tool",
                "description": "我的自定义工具",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词"}
                    },
                    "required": ["query"]
                },
                "handler": self._handle_my_tool,
                "category": "custom"
            }]
        """
        pass
    
    def on_load(self):
        """加载时注册工具到工具注册表"""
        super().on_load()
        tools = self.get_tools()
        if tools and self.context:
            registry = self.context.get_tool_registry()
            for tool in tools:
                registry.register_custom_tool(tool)
                self._logger.info(f"注册工具: {tool.get('name')}")


class ModelPlugin(Plugin):
    """
    模型插件基类
    提供自定义AI模型适配器
    """
    
    @abstractmethod
    def get_models(self) -> List[Dict[str, Any]]:
        """
        获取插件提供的模型列表
        
        Returns:
            模型元数据列表，每个模型包含:
            - name: 模型名称
            - display_name: 显示名称
            - adapter_class: 适配器类
            - config_schema: 模型配置JSON Schema
        """
        pass
    
    @abstractmethod
    def create_adapter(self, model_name: str, config: Dict[str, Any]):
        """
        创建模型适配器实例
        
        Args:
            model_name: 模型名称
            config: 模型配置
            
        Returns:
            模型适配器实例
        """
        pass


class GatewayPlugin(Plugin):
    """
    网关插件基类
    提供自定义消息网关（如新的IM平台适配）
    """
    
    @abstractmethod
    def get_gateway_type(self) -> str:
        """
        获取网关类型标识
        
        Returns:
            网关类型字符串（如 "wechat", "slack"）
        """
        pass
    
    @abstractmethod
    def create_gateway(self, config: Dict[str, Any]):
        """
        创建网关实例
        
        Args:
            config: 网关配置
            
        Returns:
            网关实例
        """
        pass
    
    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """
        获取网关配置的JSON Schema
        
        Returns:
            配置Schema字典
        """
        pass


class HookPlugin(Plugin):
    """
    钩子插件基类
    在SerpentAI生命周期事件中注入自定义逻辑
    """
    
    def get_hooks(self) -> Dict[str, Callable]:
        """
        获取插件提供的钩子函数
        
        Returns:
            {事件名: 处理函数} 字典
            支持的事件:
            - before_chat: 聊天前处理
            - after_chat: 聊天后处理
            - before_tool_call: 工具调用前
            - after_tool_call: 工具调用后
            - before_memory_save: 记忆保存前
            - on_error: 全局错误处理
        """
        return {}
    
    def on_load(self):
        """加载时注册钩子"""
        super().on_load()
        hooks = self.get_hooks()
        if hooks and self.context:
            for event, handler in hooks.items():
                self.context.on(f"serpentai.{event}", handler)
                self._logger.info(f"注册钩子: {event}")
