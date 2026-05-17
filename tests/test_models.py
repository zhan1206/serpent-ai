"""
SerpentAI 模型适配层单元测试
"""
import pytest
from unittest.mock import Mock, patch
from backend.models.base_model import Message, ModelResponse, BaseModelAdapter, create_adapter, estimate_tokens, truncate_messages, list_supported_models


class TestMessage:
    """测试消息模型"""

    def test_create_user_message(self):
        msg = Message(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"

    def test_create_system_message(self):
        msg = Message(role="system", content="你是一个有用的助手")
        assert msg.role == "system"

    def test_create_assistant_message_with_tool_calls(self):
        tool_calls = [
            {
                "id": "call_123",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "Beijing"}'
                }
            }
        ]
        msg = Message(role="assistant", content="", tool_calls=tool_calls)
        assert msg.role == "assistant"
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0]["function"]["name"] == "get_weather"


class TestModelResponse:
    """测试模型响应模型"""

    def test_create_response(self):
        response = ModelResponse(
            content="你好！",
            model="gpt-3.5-turbo",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            cost=0.001
        )
        assert response.model == "gpt-3.5-turbo"
        assert response.total_tokens == 30


class TestBaseModelAdapter:
    """测试基础模型适配器"""

    def test_validate_messages_valid(self):
        """测试验证有效消息"""
        class DummyAdapter(BaseModelAdapter):
            def initialize(self): return True
            def generate(self, messages, **kwargs): return ModelResponse(content="t", model="t", input_tokens=0, output_tokens=0)
            def count_tokens(self, text): return 0
            def get_model_info(self): return {}

        dummy = DummyAdapter("test")
        messages = [
            Message(role="system", content="系统提示"),
            Message(role="user", content="用户消息"),
        ]
        result = dummy.validate_messages(messages)
        assert result == True

    def test_validate_messages_invalid_role(self):
        """测试验证无效角色"""
        class DummyAdapter(BaseModelAdapter):
            def initialize(self): return True
            def generate(self, messages, **kwargs): return ModelResponse(content="t", model="t", input_tokens=0, output_tokens=0)
            def count_tokens(self, text): return 0
            def get_model_info(self): return {}

        dummy = DummyAdapter("test")
        messages = [Message(role="invalid_role", content="测试")]
        result = dummy.validate_messages(messages)
        assert result == False

    def test_estimate_tokens_module_function(self):
        """测试Token估算（模块级函数）"""
        text = "这是一个测试文本，用于估算Token数量。"
        estimated = estimate_tokens(text)
        assert estimated > 0
        assert isinstance(estimated, (int, float))

    def test_truncate_messages_module_function(self):
        """测试消息截断（模块级函数）"""
        messages = [
            Message(role="user", content="消息1"),
            Message(role="assistant", content="回复1"),
            Message(role="user", content="消息2"),
        ]
        truncated = truncate_messages(messages, max_tokens=10)
        assert len(truncated) <= len(messages)

    def test_estimate_cost(self):
        """测试费用估算"""
        class DummyAdapter(BaseModelAdapter):
            def initialize(self): return True
            def generate(self, messages, **kwargs): return ModelResponse(content="t", model="t", input_tokens=0, output_tokens=0)
            def count_tokens(self, text): return 0
            def get_model_info(self): return {}

        dummy = DummyAdapter("test")
        cost = dummy.estimate_cost(100, 50)
        assert isinstance(cost, float)


class TestCreateAdapter:
    """测试创建适配器工厂函数"""

    def test_create_adapter_gpt(self):
        """测试创建OpenAI类适配器"""
        import sys
        from unittest.mock import MagicMock
        sys.modules['openai'] = MagicMock()
        sys.modules['anthropic'] = MagicMock()
        try:
            adapter = create_adapter("gpt-4o")
            assert adapter is not None
        finally:
            sys.modules.pop('openai', None)
            sys.modules.pop('anthropic', None)

    def test_create_adapter_claude(self):
        """测试创建Anthropic类适配器"""
        import sys
        from unittest.mock import MagicMock
        sys.modules['openai'] = MagicMock()
        sys.modules['anthropic'] = MagicMock()
        try:
            adapter = create_adapter("claude-3-opus")
            assert adapter is not None
        finally:
            del sys.modules['openai']
            del sys.modules['anthropic']

    def test_create_adapter_llama(self):
        """测试创建Llama类适配器"""
        import sys
        from unittest.mock import MagicMock
        sys.modules['openai'] = MagicMock()
        try:
            adapter = create_adapter("llama-3-8b")
            assert adapter is not None
        finally:
            del sys.modules['openai']

    def test_create_unsupported_model(self):
        """测试创建不支持的模型"""
        import sys
        from unittest.mock import MagicMock
        sys.modules['openai'] = MagicMock()
        try:
            with pytest.raises(ValueError):
                create_adapter("unsupported-model-xyz")
        finally:
            del sys.modules['openai']

    def test_create_adapter_with_config(self):
        """测试带配置创建适配器"""
        import sys
        from unittest.mock import MagicMock
        sys.modules['openai'] = MagicMock()
        try:
            adapter = create_adapter("gpt-4o", config={"api_key": "test"})
            assert adapter is not None
        finally:
            del sys.modules['openai']


class TestListSupportedModels:
    """测试列出支持的模型"""

    def test_list_models(self):
        models = list_supported_models()
        assert isinstance(models, list)
        assert len(models) > 0
        assert "gpt-4o" in models
        assert "claude-3-opus" in models


class TestPerformance:
    """性能测试"""

    def test_token_estimation_speed(self):
        import time

        text = "测试文本" * 1000
        start = time.time()

        for _ in range(1000):
            estimate_tokens(text)

        elapsed = time.time() - start
        assert elapsed < 2.0
