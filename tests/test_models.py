"""
SerpentAI 模型适配层单元测试
测试基础模型接口和各个适配器
"""
import pytest
from unittest.mock import Mock, patch
from models.base_model import Message, ModelResponse, BaseModelAdapter, create_adapter
from core.config import settings

class TestMessage:
    """测试消息模型"""
    
    def test_create_user_message(self):
        """测试创建用户消息"""
        msg = Message(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"
        assert msg.name is None
    
    def test_create_system_message(self):
        """测试创建系统消息"""
        msg = Message(role="system", content="你是一个有用的助手")
        assert msg.role == "system"
        assert "助手" in msg.content
    
    def test_create_assistant_message_with_tool_calls(self):
        """测试创建带工具调用的助手消息"""
        tool_calls = [
            {
                "id": "call_123",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "Beijing"}'
                }
            }
        ]
        msg = Message(
            role="assistant",
            content="",
            tool_calls=tool_calls
        )
        assert msg.role == "assistant"
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0]["function"]["name"] == "get_weather"

class TestModelResponse:
    """测试模型响应模型"""
    
    def test_create_response(self):
        """测试创建模型响应"""
        response = ModelResponse(
            content="你好！我是AI助手。",
            model="gpt-3.5-turbo",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            cost=0.001
        )
        assert response.model == "gpt-3.5-turbo"
        assert response.total_tokens == 30
        assert response.cost > 0

class TestBaseModelAdapter:
    """测试基础模型适配器"""
    
    def test_validate_messages_valid(self):
        """测试验证有效消息"""
        adapter = Mock(spec=BaseModelAdapter)
        adapter.validate_messages = BaseModelAdapter.__init__.__func__.__self__.__class__.validate_messages
        
        messages = [
            Message(role="system", content="系统提示"),
            Message(role="user", content="用户消息"),
            Message(role="assistant", content="助手回复")
        ]
        
        # 创建真实适配器实例
        class DummyAdapter(BaseModelAdapter):
            def initialize(self):
                return True
            def generate(self, messages, **kwargs):
                return ModelResponse(content="test", model="test", input_tokens=0, output_tokens=0)
            def count_tokens(self, text):
                return 0
            def get_model_info(self):
                return {}
        
        dummy = DummyAdapter("test")
        result = dummy.validate_messages(messages)
        assert result == True
    
    def test_validate_messages_invalid_role(self):
        """测试验证无效角色"""
        class DummyAdapter(BaseModelAdapter):
            def initialize(self):
                return True
            def generate(self, messages, **kwargs):
                return ModelResponse(content="test", model="test", input_tokens=0, output_tokens=0)
            def count_tokens(self, text):
                return 0
            def get_model_info(self):
                return {}
        
        dummy = DummyAdapter("test")
        messages = [
            Message(role="invalid_role", content="测试")
        ]
        result = dummy.validate_messages(messages)
        assert result == False
    
    def test_estimate_tokens(self):
        """测试Token估算"""
        text = "这是一个测试文本，用于估算Token数量。"
        estimated = BaseModelAdapter.estimate_tokens(text)
        assert estimated > 0
        assert isinstance(estimated, int)
    
    def test_truncate_messages(self):
        """测试消息截断"""
        messages = [
            Message(role="user", content="消息1"),
            Message(role="assistant", content="回复1"),
            Message(role="user", content="消息2"),
            Message(role="assistant", content="回复2"),
            Message(role="user", content="消息3"),
        ]
        
        truncated = BaseModelAdapter.truncate_messages(messages, max_tokens=10, reserve_tokens=0)
        assert len(truncated) <= len(messages)

class TestCreateAdapter:
    """测试创建适配器工厂函数"""
    
    @patch('models.base_model.OpenAIAdapter')
    def test_create_openai_adapter(self, mock_openai):
        """测试创建OpenAI适配器"""
        mock_openai.return_value = Mock()
        adapter = create_adapter("gpt-3.5-turbo")
        assert adapter is not None
    
    @patch('models.base_model.AnthropicAdapter')
    def test_create_anthropic_adapter(self, mock_anthropic):
        """测试创建Anthropic适配器"""
        mock_anthropic.return_value = Mock()
        adapter = create_adapter("claude-3-opus")
        assert adapter is not None
    
    def test_create_unsupported_model(self):
        """测试创建不支持的模型"""
        with pytest.raises(ValueError, match="不支持的模型"):
            create_adapter("unsupported-model")

class TestListSupportedModels:
    """测试列出支持的模型"""
    
    def test_list_models(self):
        """测试获取模型列表"""
        models = create_adapter.__globals__['list_supported_models']()
        assert isinstance(models, list)
        assert len(models) > 0
        assert "gpt-4o" in models
        assert "claude-3-opus" in models

# ==================== 集成测试（需要真实API密钥） ====================

@pytest.mark.integration
class TestOpenAIAdapterIntegration:
    """OpenAI适配器集成测试（需要真实API密钥）"""
    
    def test_initialize_with_real_key(self):
        """测试使用真实API密钥初始化"""
        if not settings.OPENAI_API_KEY:
            pytest.skip("未配置OPENAI_API_KEY")
        
        from models.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter("gpt-3.5-turbo")
        result = adapter.initialize()
        assert result == True
        assert adapter.is_initialized == True
    
    def test_generate(self):
        """测试生成响应"""
        if not settings.OPENAI_API_KEY:
            pytest.skip("未配置OPENAI_API_KEY")
        
        from models.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter("gpt-3.5-turbo")
        adapter.initialize()
        
        messages = [
            Message(role="user", content="用一句话介绍自己")
        ]
        
        response = adapter.generate(messages, max_tokens=50)
        assert response.content != ""
        assert response.model == "gpt-3.5-turbo"
        assert response.input_tokens > 0
        assert response.output_tokens > 0

@pytest.mark.integration
class TestAnthropicAdapterIntegration:
    """Anthropic适配器集成测试（需要真实API密钥）"""
    
    def test_initialize_with_real_key(self):
        """测试使用真实API密钥初始化"""
        if not settings.ANTHROPIC_API_KEY:
            pytest.skip("未配置ANTHROPIC_API_KEY")
        
        from models.anthropic_adapter import AnthropicAdapter
        adapter = AnthropicAdapter("claude-3-haiku")
        result = adapter.initialize()
        assert result == True

# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试"""
    
    def test_token_estimation_speed(self):
        """测试Token估算速度"""
        import time
        
        text = "测试文本" * 1000
        start = time.time()
        
        for _ in range(1000):
            BaseModelAdapter.estimate_tokens(text)
        
        elapsed = time.time() - start
        assert elapsed < 1.0  # 应该在1秒内完成1000次估算

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
