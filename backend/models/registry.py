"""
SerpentAI 模型注册表
管理所有模型适配器实例
"""
import logging
from typing import Dict, Any, Optional, List

from models.base_model import BaseModelAdapter, Message

logger = logging.getLogger(__name__)

class ModelRegistry:
    """
    模型注册表
    管理模型适配器实例的注册、获取、列出
    """
    
    def __init__(self):
        """初始化注册表"""
        self._models: Dict[str, BaseModelAdapter] = {}
        self._default_model: Optional[str] = None
    
    def register(self, name: str, model: BaseModelAdapter, set_as_default: bool = False):
        """
        注册模型
        
        Args:
            name: 模型名称
            model: 模型适配器实例
            set_as_default: 是否设为默认模型
        """
        self._models[name] = model
        logger.info(f"模型已注册: {name}")
        
        if set_as_default or self._default_model is None:
            self._default_model = name
            logger.info(f"默认模型: {name}")
    
    def get_model(self, name: str) -> BaseModelAdapter:
        """
        获取模型实例
        
        Args:
            name: 模型名称
            
        Returns:
            BaseModelAdapter: 模型适配器实例
            
        Raises:
            KeyError: 模型未找到
        """
        if name not in self._models:
            available = list(self._models.keys())
            raise KeyError(f"模型未找到: {name}. 可用模型: {available}")
        
        return self._models[name]
    
    def get_default_model(self) -> BaseModelAdapter:
        """
        获取默认模型
        
        Returns:
            BaseModelAdapter: 默认模型适配器实例
            
        Raises:
            RuntimeError: 没有可用的默认模型
        """
        if self._default_model is None:
            raise RuntimeError("没有可用的默认模型，请先注册模型")
        
        return self._models[self._default_model]
    
    def list_models(self) -> List[str]:
        """
        列出所有已注册的模型
        
        Returns:
            List[str]: 模型名称列表
        """
        return list(self._models.keys())
    
    def get_model_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有模型的信息
        
        Returns:
            Dict: 模型信息字典
        """
        info = {}
        for name, model in self._models.items():
            info[name] = model.get_model_info()
        return info
    
    def set_default(self, name: str):
        """
        设置默认模型
        
        Args:
            name: 模型名称
            
        Raises:
            KeyError: 模型未找到
        """
        if name not in self._models:
            raise KeyError(f"模型未找到: {name}")
        
        self._default_model = name
        logger.info(f"默认模型已设为: {name}")
    
    def remove_model(self, name: str):
        """
        移除模型
        
        Args:
            name: 模型名称
        """
        if name in self._models:
            del self._models[name]
            logger.info(f"模型已移除: {name}")
            
            # 如果移除的是默认模型，重新选择默认模型
            if self._default_model == name:
                if self._models:
                    self._default_model = list(self._models.keys())[0]
                else:
                    self._default_model = None


# 全局注册表实例
_global_registry: Optional[ModelRegistry] = None

def get_global_registry() -> ModelRegistry:
    """
    获取全局模型注册表实例
    
    Returns:
        ModelRegistry: 全局注册表实例
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ModelRegistry()
    return _global_registry

def init_default_models():
    """
    初始化默认模型（在应用启动时调用）
    """
    registry = get_global_registry()
    
    try:
        # 尝试注册 OpenAI 模型
        from models.openai_adapter import OpenAIAdapter
        openai_adapter = OpenAIAdapter()
        registry.register("gpt-4", openai_adapter)
        registry.register("gpt-3.5-turbo", openai_adapter)
    except Exception as e:
        logger.warning(f"OpenAI 模型初始化失败: {e}")
    
    try:
        # 尝试注册 Anthropic 模型
        from models.anthropic_adapter import AnthropicAdapter
        anthropic_adapter = AnthropicAdapter()
        registry.register("claude-3", anthropic_adapter)
    except Exception as e:
        logger.warning(f"Anthropic 模型初始化失败: {e}")
    
    try:
        # 尝试注册本地 Llama 模型
        from models.llama_adapter import LlamaAdapter
        llama_adapter = LlamaAdapter("llama-3-8b")
        registry.register("llama-3-8b", llama_adapter)
    except Exception as e:
        logger.warning(f"Llama 模型初始化失败: {e}")
    
    # 如果没有注册任何模型，注册模拟适配器作为备用
    if not registry.list_models():
        logger.warning("没有可用的真实模型，注册模拟适配器作为备用")
        from models.mock_adapter import MockAdapter
        mock_adapter = MockAdapter()
        registry.register("mock", mock_adapter, set_as_default=True)
        logger.info("已注册模拟适配器（mock）- 用于测试和演示")
    
    logger.info(f"模型注册表初始化完成，已注册 {len(registry.list_models())} 个模型")
