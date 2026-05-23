"""
SerpentAI 模型模块扩展测试
测试模型注册表和Mock适配器
"""

import pytest
import sys
import os
import time
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Any, Optional

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from models.base_model import BaseModelAdapter, Message, ModelResponse
from models.registry import ModelRegistry, get_global_registry, init_default_models
from models.mock_adapter import MockAdapter


class TestModelRegistry:
    """测试模型注册表"""
    
    @pytest.fixture
    def registry(self):
        """创建干净的注册表"""
        return ModelRegistry()
    
    def test_initialization(self, registry):
        """测试初始化"""
        assert registry is not None
        assert len(registry.list_models()) == 0
        with pytest.raises(RuntimeError):
            registry.get_default_model()
    
    def test_register_model(self, registry):
        """测试注册模型"""
        adapter = MockAdapter(model_name="test-model")
        registry.register("test", adapter)
        
        assert "test" in registry.list_models()
        assert registry.get_default_model() is not None  # 第一个注册的是默认
    
    def test_register_multiple_models(self, registry):
        """测试注册多个模型"""
        adapter1 = MockAdapter(model_name="model1")
        adapter2 = MockAdapter(model_name="model2")
        
        registry.register("model1", adapter1)
        registry.register("model2", adapter2, set_as_default=False)
        
        models = registry.list_models()
        assert len(models) == 2
        assert "model1" in models
        assert "model2" in models
    
    def test_set_default_model(self, registry):
        """测试设置默认模型"""
        adapter1 = MockAdapter(model_name="model1")
        adapter2 = MockAdapter(model_name="model2")
        
        registry.register("model1", adapter1)
        registry.register("model2", adapter2)
        
        # 默认应该是model1
        default = registry.get_default_model()
        assert default.model_name == "model1"
        
        # 设置model2为默认
        registry.set_default("model2")
        default = registry.get_default_model()
        assert default.model_name == "model2"
    
    def test_get_model(self, registry):
        """测试获取模型"""
        adapter = MockAdapter(model_name="test")
        registry.register("test", adapter)
        
        retrieved = registry.get_model("test")
        assert retrieved is not None
        assert retrieved.model_name == "test"
    
    def test_get_nonexistent_model(self, registry):
        """测试获取不存在的模型"""
        with pytest.raises(KeyError):
            registry.get_model("nonexistent")
    
    def test_remove_model(self, registry):
        """测试移除模型"""
        adapter1 = MockAdapter(model_name="model1")
        adapter2 = MockAdapter(model_name="model2")
        
        registry.register("model1", adapter1)
        registry.register("model2", adapter2)
        
        registry.remove_model("model1")
        
        models = registry.list_models()
        assert len(models) == 1
        assert "model1" not in models
    
    def test_remove_default_model(self, registry):
        """测试移除默认模型"""
        adapter1 = MockAdapter(model_name="model1")
        adapter2 = MockAdapter(model_name="model2")
        
        registry.register("model1", adapter1)
        registry.register("model2", adapter2)
        
        # 移除默认模型（model1）
        registry.remove_model("model1")
        
        # 默认模型应该自动切换到model2
        default = registry.get_default_model()
        assert default.model_name == "model2"
    
    def test_list_models(self, registry):
        """测试列出所有模型"""
        adapter1 = MockAdapter(model_name="model1")
        adapter2 = MockAdapter(model_name="model2")
        adapter3 = MockAdapter(model_name="model3")
        
        registry.register("model1", adapter1)
        registry.register("model2", adapter2)
        registry.register("model3", adapter3)
        
        models = registry.list_models()
        assert len(models) == 3
    
    def test_get_model_info(self, registry):
        """测试获取模型信息"""
        adapter = MockAdapter(model_name="test")
        registry.register("test", adapter)
        
        info = registry.get_model_info()
        
        assert "test" in info
        assert "name" in info["test"]
        assert "provider" in info["test"]
        assert "context_length" in info["test"]
        assert "is_mock" in info["test"]
        assert "supports_streaming" in info["test"]
        assert "supports_tools" in info["test"]
        assert "cost_per_1k_tokens" in info["test"]
        assert "note" in info["test"]
    
    def test_get_global_registry(self):
        """测试获取全局注册表"""
        registry1 = get_global_registry()
        registry2 = get_global_registry()
        
        # 应该是同一个实例（单例）
        assert registry1 is registry2


class TestMockAdapter:
    """测试Mock适配器（用于测试和开发）"""
    
    @pytest.fixture
    def adapter(self):
        return MockAdapter(model_name="mock-gpt-4o")
    
    def test_initialization(self, adapter):
        """测试初始化"""
        assert adapter is not None
        assert adapter.model_name == "mock-gpt-4o"
        # is_initialized 在 initialize() 后才为 True
        assert not adapter.is_initialized
        result = adapter.initialize()
        assert result
        assert adapter.is_initialized
    
    @pytest.mark.asyncio
    async def test_generate(self, adapter):
        """测试生成响应"""
        messages = [
            Message(role="user", content="你好")
        ]
        
        response = await adapter.generate(messages)
        
        assert response is not None
        assert response.content is not None
        assert response.model == "mock-gpt-4o"
        assert response.input_tokens > 0
        assert response.output_tokens > 0
        assert response.total_tokens > 0
        assert response.cost == 0.0
        assert response.latency_ms > 0
        assert "provider" in response.metadata
        assert "temperature" in response.metadata
        assert "note" in response.metadata
    
    @pytest.mark.asyncio
    async def test_generate_streaming(self, adapter):
        """测试流式生成"""
        messages = [
            Message(role="user", content="你好")
        ]
        
        # generate(stream=True) 返回异步生成器
        chunks = []
        async for chunk in await adapter.generate(messages, stream=True):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0
    
    def test_count_tokens(self, adapter):
        """测试Token计数"""
        text = "Hello, world!"
        tokens = adapter.count_tokens(text)
        
        assert tokens > 0
        assert isinstance(tokens, int)
    
    def test_get_model_info(self, adapter):
        """测试获取模型信息"""
        info = adapter.get_model_info()
        
        assert "name" in info
        assert "provider" in info
        assert "context_length" in info
        assert "is_mock" in info
        assert "supports_streaming" in info
        assert "supports_tools" in info
        assert "cost_per_1k_tokens" in info
        assert "note" in info
        assert info["is_mock"] is True
        assert info["cost_per_1k_tokens"] == 0.0
        assert "This is a mock model for testing only." in info["note"]


class TestInitDefaultModels:
    """测试初始化默认模型"""
    
    def test_init_default_models_with_mock(self):
        """测试初始化默认模型（使用Mock适配器）"""
        # 清除全局注册表
        import models.registry as registry_module
        registry_module._global_registry = None
        
        registry = get_global_registry()
        assert len(registry.list_models()) == 0
        
        # 直接注册Mock适配器（模拟所有真实模型失败的情况）
        from models.mock_adapter import MockAdapter
        mock_adapter = MockAdapter()
        registry.register("mock", mock_adapter, set_as_default=True)
        
        # 应该注册了Mock适配器
        models = registry.list_models()
        assert len(models) >= 1
        assert "mock" in models
        
        # 默认模型应该是Mock
        default = registry.get_default_model()
        assert default.model_name == "mock-model"  # MockAdapter 默认名称


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
