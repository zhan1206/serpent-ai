"""
SerpentAI Models Module - Full Test Suite
Tests ALL public methods for all model adapters with comprehensive mocking.
Target: 80%+ coverage
"""
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import pytest

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from models.base_model import (
    Message, ModelResponse, TokenUsage, BaseModelAdapter,
    create_adapter, list_supported_models, estimate_tokens,
    truncate_messages
)
from models.token_counter import TokenCounter, get_global_counter
from models.registry import ModelRegistry, get_global_registry
from models.model_router import (
    ModelRouter, TaskComplexity, ModelScore, RoutingRule,
    get_global_router
)


# ==================== Fixtures ====================

@pytest.fixture
def sample_messages():
    """Sample messages for testing"""
    return [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello, how are you?"),
        Message(role="assistant", content="I'm doing well, thank you!"),
    ]


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client"""
    client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "Test response"
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 20
    mock_response.usage.completion_tokens = 15
    client.chat.completions.create.return_value = mock_response
    return client


# ==================== Test Base Model ====================

class TestMessage:
    """Test Message model"""

    def test_create_message(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None
        assert msg.tool_calls is None
        assert msg.tool_call_id is None

    def test_create_message_with_tool(self):
        msg = Message(
            role="assistant",
            content="",
            tool_calls=[{"id": "123", "function": {"name": "test"}}],
            name="assistant"
        )
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1


class TestModelResponse:
    """Test ModelResponse model"""

    def test_create_response(self):
        resp = ModelResponse(
            content="Test",
            model="gpt-4",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30
        )
        assert resp.content == "Test"
        assert resp.model == "gpt-4"
        assert resp.cost == 0.0
        assert resp.latency_ms == 0


class TestTokenUsage:
    """Test TokenUsage model"""

    def test_create_token_usage(self):
        usage = TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150)
        assert usage.total_tokens == 150
        assert usage.to_dict() == {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150
        }

    def test_token_usage_default_total(self):
        """Test that total_tokens defaults to 0"""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 0  # Default value


class MockBaseAdapter(BaseModelAdapter):
    """Concrete implementation for testing"""

    def initialize(self):
        self.is_initialized = True
        return True

    def generate(self, messages, temperature=0.7, max_tokens=None, tools=None, stream=False):
        return ModelResponse(content="test", model=self.model_name, input_tokens=10, output_tokens=5)

    def count_tokens(self, text):
        return len(text) // 1

    def get_model_info(self):
        return {"name": self.model_name}


class TestBaseModelAdapter:
    """Test BaseModelAdapter abstract class"""

    def test_validate_messages_valid(self, sample_messages):
        adapter = MockBaseAdapter("test-model")
        result = adapter.validate_messages(sample_messages)
        assert result is True

    def test_validate_messages_empty(self):
        adapter = MockBaseAdapter("test-model")
        result = adapter.validate_messages([])
        assert result is False

    def test_validate_messages_invalid_role(self):
        adapter = MockBaseAdapter("test-model")
        msg = Message(role="invalid_role", content="test")
        result = adapter.validate_messages([msg])
        assert result is False

    def test_validate_messages_tool_role(self):
        """Test that 'tool' role is valid"""
        adapter = MockBaseAdapter("test-model")
        msg = Message(role="tool", content="test", tool_call_id="123")
        result = adapter.validate_messages([msg])
        assert result is True

    def test_estimate_cost_default(self):
        adapter = MockBaseAdapter("test-model")
        cost = adapter.estimate_cost(1000, 500)
        expected = (1000 / 1000) * 0.01 + (500 / 1000) * 0.03
        assert cost == pytest.approx(expected)

    def test_repr(self):
        adapter = MockBaseAdapter("test-model")
        adapter.is_initialized = True
        repr_str = repr(adapter)
        assert "MockBaseAdapter" in repr_str
        assert "test-model" in repr_str


class TestCreateAdapter:
    """Test create_adapter function"""

    def test_create_unsupported_model(self):
        with pytest.raises(ValueError):
            create_adapter("unsupported-model")


class TestListSupportedModels:
    """Test list_supported_models function"""

    def test_returns_list(self):
        models = list_supported_models()
        assert isinstance(models, list)
        assert len(models) > 0
        assert "gpt-4o" in models
        assert "claude-3-opus" in models


class TestEstimateTokens:
    """Test estimate_tokens function"""

    def test_estimate_tokens(self):
        text = "Hello, world!"
        result = estimate_tokens(text)
        expected = len(text) // 1.3
        assert result == expected

    def test_estimate_tokens_empty(self):
        result = estimate_tokens("")
        assert result == 0


class TestTruncateMessages:
    """Test truncate_messages function"""

    def test_truncate_messages(self, sample_messages):
        result = truncate_messages(sample_messages, max_tokens=100, reserve_tokens=50)
        assert isinstance(result, list)
        assert len(result) <= len(sample_messages)

    def test_truncate_messages_empty(self):
        result = truncate_messages([], max_tokens=100)
        assert result == []


# ==================== Test OpenAI Adapter ====================

class TestOpenAIAdapter:
    """Test OpenAIAdapter"""

    @patch('openai.OpenAI')
    def test_initialize_success(self, mock_openai_class):
        mock_client = Mock()
        mock_client.models.list.return_value = []
        mock_openai_class.return_value = mock_client

        with patch('models.openai_adapter.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.OPENAI_API_BASE = None

            from models.openai_adapter import OpenAIAdapter
            adapter = OpenAIAdapter("gpt-4o")
            result = adapter.initialize()

            assert result is True
            assert adapter.is_initialized is True

    def test_initialize_failure_no_key(self):
        """Test initialization failure when no API key"""
        with patch('models.openai_adapter.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            mock_settings.openai = Mock()
            mock_settings.openai.api_key = None

            from models.openai_adapter import OpenAIAdapter
            adapter = OpenAIAdapter("gpt-4o")
            result = adapter.initialize()

            assert result is False

    @patch('openai.OpenAI')
    def test_generate_success(self, mock_openai_class, sample_messages):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Test response from OpenAI"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 15
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        with patch('models.openai_adapter.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.OPENAI_API_BASE = None

            from models.openai_adapter import OpenAIAdapter
            adapter = OpenAIAdapter("gpt-4o")
            adapter.is_initialized = True
            adapter.client = mock_client

            response = adapter.generate(sample_messages)

            assert isinstance(response, ModelResponse)
            assert response.content == "Test response from OpenAI"
            assert response.input_tokens == 20
            assert response.output_tokens == 15

    def test_count_tokens(self):
        from models.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter("gpt-4o")
        result = adapter.count_tokens("Hello, world!")
        assert result > 0

    def test_get_model_info(self):
        from models.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter("gpt-4o")
        info = adapter.get_model_info()
        assert info["name"] == "gpt-4o"
        assert info["provider"] == "openai"
        assert "pricing" in info

    def test_estimate_cost(self):
        from models.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter("gpt-4o")
        cost = adapter.estimate_cost(1000, 500)
        assert cost > 0


# ==================== Test Anthropic Adapter ====================

class TestAnthropicAdapter:
    """Test AnthropicAdapter"""

    @patch('anthropic.Anthropic')
    def test_initialize_success(self, mock_anthropic_class):
        mock_client = Mock()
        mock_client.models.list.return_value = []
        mock_anthropic_class.return_value = mock_client

        with patch('models.anthropic_adapter.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mock_settings.ANTHROPIC_API_BASE = None

            from models.anthropic_adapter import AnthropicAdapter
            adapter = AnthropicAdapter("claude-3-opus")
            result = adapter.initialize()

            assert result is True

    def test_convert_messages_to_anthropic_format(self):
        from models.anthropic_adapter import AnthropicAdapter
        adapter = AnthropicAdapter("claude-3-opus")

        messages = [
            Message(role="system", content="You are helpful."),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]

        anthropic_msgs, system = adapter._convert_messages_to_anthropic_format(messages)

        assert system == "You are helpful."
        assert len(anthropic_msgs) == 2
        assert anthropic_msgs[0]["role"] == "user"
        assert anthropic_msgs[1]["role"] == "assistant"

    @patch('anthropic.Anthropic')
    def test_generate_success(self, mock_anthropic_class):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Test response from Anthropic"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 20
        mock_response.usage.output_tokens = 15
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        with patch('models.anthropic_adapter.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mock_settings.ANTHROPIC_API_BASE = None

            from models.anthropic_adapter import AnthropicAdapter
            adapter = AnthropicAdapter("claude-3-opus")
            adapter.is_initialized = True
            adapter.client = mock_client

            messages = [Message(role="user", content="Hello")]
            response = adapter.generate(messages)

            assert isinstance(response, ModelResponse)
            assert response.content == "Test response from Anthropic"

    def test_count_tokens(self):
        from models.anthropic_adapter import AnthropicAdapter
        adapter = AnthropicAdapter("claude-3-opus")
        result = adapter.count_tokens("Hello")
        assert result > 0

    def test_get_model_info(self):
        from models.anthropic_adapter import AnthropicAdapter
        adapter = AnthropicAdapter("claude-3-opus")
        info = adapter.get_model_info()
        assert info["provider"] == "anthropic"
        assert info["supports_tools"] is True

    def test_estimate_cost(self):
        from models.anthropic_adapter import AnthropicAdapter
        adapter = AnthropicAdapter("claude-3-opus")
        cost = adapter.estimate_cost(1000, 500)
        assert cost > 0


# ==================== Test DeepSeek Adapter ====================

class TestDeepSeekAdapter:
    """Test DeepSeekAdapter"""

    def test_initialize_no_key(self):
        """Test initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            from models.deepseek_adapter import DeepSeekAdapter
            adapter = DeepSeekAdapter("deepseek-chat")
            result = adapter.initialize()
            assert result is False

    def test_generate_with_mock_client(self, sample_messages, mock_openai_client):
        """Test generate with pre-configured mock"""
        from models.deepseek_adapter import DeepSeekAdapter
        adapter = DeepSeekAdapter("deepseek-chat")
        adapter.is_initialized = True
        adapter.client = mock_openai_client

        response = adapter.generate(sample_messages)

        assert isinstance(response, ModelResponse)
        assert response.content == "Test response"

    def test_count_tokens(self):
        from models.deepseek_adapter import DeepSeekAdapter
        adapter = DeepSeekAdapter("deepseek-chat")
        result = adapter.count_tokens("Hello, 你好")
        assert result > 0

    def test_get_model_info(self):
        from models.deepseek_adapter import DeepSeekAdapter
        adapter = DeepSeekAdapter("deepseek-chat")
        info = adapter.get_model_info()
        assert info["provider"] == "deepseek"

    def test_estimate_cost(self):
        from models.deepseek_adapter import DeepSeekAdapter
        adapter = DeepSeekAdapter("deepseek-chat")
        cost = adapter._estimate_cost(1000, 500)
        assert cost > 0


# ==================== Test Doubao Adapter ====================

class TestDoubaoAdapter:
    """Test DoubaoAdapter"""

    def test_initialize_no_key(self):
        """Test initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            from models.doubao_adapter import DoubaoAdapter
            adapter = DoubaoAdapter("doubao-pro-32k")
            result = adapter.initialize()
            assert result is False

    def test_generate_with_mock_client(self, sample_messages, mock_openai_client):
        """Test generate with pre-configured mock"""
        from models.doubao_adapter import DoubaoAdapter
        adapter = DoubaoAdapter("doubao-pro-32k")
        adapter.is_initialized = True
        adapter.client = mock_openai_client

        response = adapter.generate(sample_messages)

        assert isinstance(response, ModelResponse)

    def test_count_tokens(self):
        from models.doubao_adapter import DoubaoAdapter
        adapter = DoubaoAdapter("doubao-pro-32k")
        result = adapter.count_tokens("Hello")
        assert result > 0

    def test_get_model_info(self):
        from models.doubao_adapter import DoubaoAdapter
        adapter = DoubaoAdapter("doubao-pro-32k")
        info = adapter.get_model_info()
        assert info["provider"] == "doubao"

    def test_estimate_cost(self):
        from models.doubao_adapter import DoubaoAdapter
        adapter = DoubaoAdapter("doubao-pro-32k")
        cost = adapter._estimate_cost(1000, 500)
        assert cost > 0


# ==================== Test Gemini Adapter ====================

class TestGeminiAdapter:
    """Test GeminiAdapter"""

    def test_create_adapter(self):
        """Test that adapter can be created"""
        from models.gemini_adapter import GeminiAdapter
        adapter = GeminiAdapter("gemini-1.5-flash")
        assert adapter.model_name == "gemini-1.5-flash"
        assert adapter._genai is None
        assert adapter._model is None

    def test_count_tokens(self):
        from models.gemini_adapter import GeminiAdapter
        adapter = GeminiAdapter("gemini-1.5-flash")
        result = adapter.count_tokens("Hello")
        assert result > 0

    def test_get_model_info(self):
        from models.gemini_adapter import GeminiAdapter
        adapter = GeminiAdapter("gemini-1.5-flash")
        info = adapter.get_model_info()
        assert info["provider"] == "gemini"

    def test_estimate_cost(self):
        from models.gemini_adapter import GeminiAdapter
        adapter = GeminiAdapter("gemini-1.5-flash")
        cost = adapter._estimate_cost(1000, 500)
        assert cost > 0


# ==================== Test Llama Adapter ====================

class TestLlamaAdapter:
    """Test LlamaAdapter"""

    def test_create_adapter(self):
        """Test that adapter can be created"""
        from models.llama_adapter import LlamaAdapter
        adapter = LlamaAdapter("llama-3-8b")
        assert adapter.model_name == "llama-3-8b"
        assert adapter.llama is None
        assert adapter.n_ctx == 2048

    def test_convert_messages_to_prompt(self):
        from models.llama_adapter import LlamaAdapter
        adapter = LlamaAdapter("llama-3-8b")

        messages = [
            Message(role="system", content="You are helpful."),
            Message(role="user", content="Hello"),
        ]

        prompt = adapter._convert_messages_to_prompt(messages)
        assert "System:" in prompt
        assert "User:" in prompt
        assert "Hello" in prompt

    def test_generate_with_mock_llama(self, sample_messages):
        """Test generate with mocked llama instance"""
        from models.llama_adapter import LlamaAdapter
        adapter = LlamaAdapter("llama-3-8b")
        adapter.is_initialized = True
        adapter.llama = Mock()
        adapter.llama.return_value = {
            "choices": [{"text": "Llama response"}]
        }

        response = adapter.generate(sample_messages)

        assert isinstance(response, ModelResponse)
        assert response.content == "Llama response"
        assert response.cost == 0.0  # Local model has no cost

    def test_get_model_info(self):
        from models.llama_adapter import LlamaAdapter
        adapter = LlamaAdapter("llama-3-8b")
        info = adapter.get_model_info()
        assert info["provider"] == "local"
        assert info["pricing"]["input"] == 0.0

    def test_unload_model(self):
        from models.llama_adapter import LlamaAdapter
        adapter = LlamaAdapter("llama-3-8b")
        adapter.llama = Mock()
        adapter.is_initialized = True

        adapter.unload_model()

        assert adapter.llama is None
        assert adapter.is_initialized is False

    def test_estimate_cost(self):
        from models.llama_adapter import LlamaAdapter
        adapter = LlamaAdapter("llama-3-8b")
        cost = adapter.estimate_cost(100, 50)
        assert cost == 0.0


# ==================== Test Qwen Adapter ====================

class TestQwenAdapter:
    """Test QwenAdapter"""

    def test_initialize_no_key(self):
        """Test initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            from models.qwen_adapter import QwenAdapter
            adapter = QwenAdapter("qwen-turbo")
            result = adapter.initialize()
            assert result is False

    def test_generate_with_mock_client(self, sample_messages, mock_openai_client):
        """Test generate with pre-configured mock"""
        from models.qwen_adapter import QwenAdapter
        adapter = QwenAdapter("qwen-turbo")
        adapter.is_initialized = True
        adapter.client = mock_openai_client

        response = adapter.generate(sample_messages)

        assert isinstance(response, ModelResponse)

    def test_count_tokens(self):
        from models.qwen_adapter import QwenAdapter
        adapter = QwenAdapter("qwen-turbo")
        result = adapter.count_tokens("Hello")
        assert result > 0

    def test_get_model_info(self):
        from models.qwen_adapter import QwenAdapter
        adapter = QwenAdapter("qwen-turbo")
        info = adapter.get_model_info()
        assert info["provider"] == "qwen"

    def test_estimate_cost(self):
        from models.qwen_adapter import QwenAdapter
        adapter = QwenAdapter("qwen-turbo")
        cost = adapter._estimate_cost(1000, 500)
        assert cost > 0


# ==================== Test Wenxin Adapter ====================

class TestWenxinAdapter:
    """Test WenxinAdapter"""

    def test_create_with_short_name(self):
        """Test model name mapping"""
        from models.wenxin_adapter import WenxinAdapter
        adapter = WenxinAdapter("ernie-4.0")
        assert adapter.model_name == "ernie-4.0-8k"

    def test_initialize_no_key(self):
        """Test initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            from models.wenxin_adapter import WenxinAdapter
            adapter = WenxinAdapter("ernie-4.0-8k")
            result = adapter.initialize()
            assert result is False

    def test_generate_with_mock_client(self, sample_messages, mock_openai_client):
        """Test generate with pre-configured mock"""
        from models.wenxin_adapter import WenxinAdapter
        adapter = WenxinAdapter("ernie-4.0-8k")
        adapter.is_initialized = True
        adapter.client = mock_openai_client

        response = adapter.generate(sample_messages)

        assert isinstance(response, ModelResponse)

    def test_count_tokens(self):
        from models.wenxin_adapter import WenxinAdapter
        adapter = WenxinAdapter("ernie-4.0-8k")
        result = adapter.count_tokens("Hello")
        assert result > 0

    def test_get_model_info(self):
        from models.wenxin_adapter import WenxinAdapter
        adapter = WenxinAdapter("ernie-4.0-8k")
        info = adapter.get_model_info()
        assert info["provider"] == "wenxin"

    def test_estimate_cost(self):
        from models.wenxin_adapter import WenxinAdapter
        adapter = WenxinAdapter("ernie-4.0-8k")
        cost = adapter._estimate_cost(1000, 500)
        assert cost > 0


# ==================== Test Token Counter ====================

class TestTokenCounter:
    """Test TokenCounter class"""

    def test_count_with_default_ratio(self):
        with patch('models.token_counter._tiktoken_available', False):
            result = TokenCounter.count("Hello, world!", "gpt-4o")
            assert result > 0

    def test_count_messages(self, sample_messages):
        with patch('models.token_counter._tiktoken_available', False):
            total = TokenCounter.count_messages(sample_messages, "gpt-4o")
            assert total > 0

    def test_record_and_get_stats(self):
        counter = TokenCounter()
        counter.record(100, 50)
        counter.record(200, 75)

        stats = counter.get_stats()
        assert stats["total_input_tokens"] == 300
        assert stats["total_output_tokens"] == 125
        assert stats["total_tokens"] == 425
        assert stats["call_count"] == 2

    def test_reset(self):
        counter = TokenCounter()
        counter.record(100, 50)
        counter.reset()

        stats = counter.get_stats()
        assert stats["total_input_tokens"] == 0
        assert stats["call_count"] == 0

    def test_get_global_counter(self):
        counter = get_global_counter()
        assert isinstance(counter, TokenCounter)


# ==================== Test Model Registry ====================

class TestModelRegistry:
    """Test ModelRegistry class"""

    def test_register_and_get_model(self):
        registry = ModelRegistry()
        adapter = MockBaseAdapter("test-model")
        registry.register("test", adapter)

        retrieved = registry.get_model("test")
        assert retrieved == adapter

    def test_get_nonexistent_model(self):
        registry = ModelRegistry()
        with pytest.raises(KeyError):
            registry.get_model("nonexistent")

    def test_get_default_model(self):
        registry = ModelRegistry()
        adapter = MockBaseAdapter("default-model")
        registry.register("default", adapter, set_as_default=True)

        default = registry.get_default_model()
        assert default == adapter

    def test_get_default_model_not_set(self):
        registry = ModelRegistry()
        with pytest.raises(RuntimeError):
            registry.get_default_model()

    def test_list_models(self):
        registry = ModelRegistry()
        registry.register("model1", MockBaseAdapter("m1"))
        registry.register("model2", MockBaseAdapter("m2"))

        models = registry.list_models()
        assert len(models) == 2
        assert "model1" in models

    def test_get_model_info(self):
        registry = ModelRegistry()
        registry.register("model1", MockBaseAdapter("m1"))

        info = registry.get_model_info()
        assert "model1" in info

    def test_set_default(self):
        registry = ModelRegistry()
        registry.register("model1", MockBaseAdapter("m1"))
        registry.register("model2", MockBaseAdapter("m2"))

        registry.set_default("model2")
        assert registry._default_model == "model2"

    def test_remove_model(self):
        registry = ModelRegistry()
        registry.register("model1", MockBaseAdapter("m1"))
        registry.register("model2", MockBaseAdapter("m2"), set_as_default=True)

        registry.remove_model("model2")

        assert "model2" not in registry.list_models()
        assert registry._default_model == "model1"  # Should switch to remaining

    def test_remove_and_clear_default(self):
        """Test removing all models"""
        registry = ModelRegistry()
        registry.register("model1", MockBaseAdapter("m1"), set_as_default=True)

        registry.remove_model("model1")

        assert len(registry.list_models()) == 0
        assert registry._default_model is None

    def test_get_global_registry(self):
        registry = get_global_registry()
        assert isinstance(registry, ModelRegistry)


# ==================== Test Model Router ====================

class TestTaskComplexity:
    """Test TaskComplexity enum"""

    def test_values(self):
        assert TaskComplexity.SIMPLE.value == "simple"
        assert TaskComplexity.MEDIUM.value == "medium"
        assert TaskComplexity.COMPLEX.value == "complex"


class TestModelScore:
    """Test ModelScore dataclass"""

    def test_success_rate(self):
        score = ModelScore(model_name="test", success_count=8, fail_count=2)
        assert score.success_rate == 0.8

    def test_success_rate_no_calls(self):
        score = ModelScore(model_name="test")
        assert score.success_rate == 0.5

    def test_avg_latency(self):
        score = ModelScore(model_name="test", success_count=5, total_latency_ms=1000)
        assert score.avg_latency_ms == 200.0

    def test_avg_cost(self):
        score = ModelScore(model_name="test", success_count=5, total_cost=1.0)
        assert score.avg_cost == 0.2


class TestModelRouter:
    """Test ModelRouter class"""

    def test_initialize(self):
        router = ModelRouter()
        assert router._registry is None
        assert len(router._rules) > 0
        assert TaskComplexity.SIMPLE in router._rules

    def test_set_registry(self):
        router = ModelRouter()
        registry = ModelRegistry()
        router.set_registry(registry)
        assert router._registry == registry

    def test_classify_complexity_simple(self):
        router = ModelRouter()
        messages = [Message(role="user", content="Hello")]
        complexity = router.classify_complexity(messages)
        assert complexity == TaskComplexity.SIMPLE

    def test_classify_complexity_medium(self):
        router = ModelRouter()
        messages = [Message(role="user", content="Please summarize this document for me")]
        complexity = router.classify_complexity(messages)
        assert complexity == TaskComplexity.MEDIUM

    def test_classify_complexity_complex(self):
        router = ModelRouter()
        messages = [Message(role="user", content="Please analyze and explain the architecture of this complex system")]
        complexity = router.classify_complexity(messages)
        assert complexity == TaskComplexity.COMPLEX

    def test_classify_complexity_empty(self):
        router = ModelRouter()
        complexity = router.classify_complexity([])
        assert complexity == TaskComplexity.SIMPLE

    def test_select_model_with_registry(self):
        router = ModelRouter()
        registry = Mock()
        registry.list_models.return_value = ["gpt-4o", "gpt-3.5-turbo", "mock"]
        router.set_registry(registry)

        messages = [Message(role="user", content="Hello")]
        model = router.select_model(messages)

        assert model in ["gpt-4o", "gpt-3.5-turbo", "mock"]

    def test_select_model_no_registry(self):
        router = ModelRouter()
        model = router.select_model([Message(role="user", content="Hello")])
        assert model == "mock"

    def test_select_model_with_preferred(self):
        """Test selecting with preferred model"""
        router = ModelRouter()
        registry = Mock()
        registry.list_models.return_value = ["gpt-4o", "mock"]
        router.set_registry(registry)

        model = router.select_model(
            [Message(role="user", content="Hello")],
            preferred_model="gpt-4o"
        )
        assert model == "gpt-4o"

    def test_record_success(self):
        router = ModelRouter()
        router.record_success("gpt-4o", 500, 100, 50, 0.01)

        scores = router.get_scores()
        assert "gpt-4o" in scores
        assert scores["gpt-4o"]["success_rate"] == 1.0

    def test_record_multiple_successes(self):
        router = ModelRouter()
        router.record_success("gpt-4o", 500, 100, 50, 0.01)
        router.record_success("gpt-4o", 300, 100, 50, 0.01)

        scores = router.get_scores()
        assert scores["gpt-4o"]["total_calls"] == 2

    def test_record_failure(self):
        router = ModelRouter()
        router.record_failure("gpt-4o")

        assert "gpt-4o" in router._fail_cooldown

    def test_record_failure_increments_count(self):
        router = ModelRouter()
        router.record_failure("gpt-4o")

        scores = router.get_scores()
        assert scores["gpt-4o"]["total_calls"] == 1
        assert scores["gpt-4o"]["success_rate"] == 0.0

    def test_is_in_cooldown(self):
        router = ModelRouter()
        router._fail_cooldown["test-model"] = time.time() + 60
        assert router._is_in_cooldown("test-model") is True

    def test_is_not_in_cooldown(self):
        router = ModelRouter()
        assert router._is_in_cooldown("test-model") is False

    def test_cooldown_expires(self):
        router = ModelRouter()
        router._fail_cooldown["test-model"] = time.time() - 10  # Already expired
        assert router._is_in_cooldown("test-model") is False

    def test_get_routing_info(self):
        router = ModelRouter()
        info = router.get_routing_info()

        assert "rules" in info
        assert "scores" in info
        assert "cooldown" in info

    def test_add_rule(self):
        router = ModelRouter()
        new_rule = RoutingRule(
            complexity=TaskComplexity.SIMPLE,
            preferred_models=["custom-model"],
            max_cost_per_1k=0.1
        )
        router.add_rule(new_rule)

        assert TaskComplexity.SIMPLE in router._rules
        assert "custom-model" in router._rules[TaskComplexity.SIMPLE].preferred_models

    def test_compute_routing_score(self):
        router = ModelRouter()
        rule = router._rules[TaskComplexity.SIMPLE]

        # Add some score history
        router.record_success("gpt-4o-mini", 200, 100, 50, 0.0005)

        score = router._compute_routing_score("gpt-4o-mini", rule)
        assert 0 <= score <= 1

    def test_compute_routing_score_unknown_model(self):
        router = ModelRouter()
        rule = router._rules[TaskComplexity.SIMPLE]

        score = router._compute_routing_score("unknown-model", rule)
        assert score == 0.5  # Default for unknown

    def test_meets_constraints(self):
        router = ModelRouter()
        rule = router._rules[TaskComplexity.SIMPLE]

        result = router._meets_constraints("test-model", rule)
        assert result is True

    def test_get_global_router(self):
        router = get_global_router()
        assert isinstance(router, ModelRouter)


# ==================== Integration Tests ====================

class TestIntegration:
    """Integration tests for model interactions"""

    def test_registry_with_router(self):
        """Test registry and router working together"""
        registry = ModelRegistry()
        adapter = MockBaseAdapter("test-model")
        registry.register("test", adapter, set_as_default=True)

        router = ModelRouter()
        router.set_registry(registry)

        model_name = router.select_model([Message(role="user", content="Test")])
        assert model_name == "test"

    def test_full_generate_flow(self, sample_messages, mock_openai_client):
        """Test full flow from registry to generate"""
        with patch('openai.OpenAI', return_value=mock_openai_client):
            with patch('models.openai_adapter.settings') as mock_settings:
                mock_settings.OPENAI_API_KEY = "test-key"
                mock_settings.OPENAI_API_BASE = None

                from models.openai_adapter import OpenAIAdapter
                adapter = OpenAIAdapter("gpt-4o")
                adapter.is_initialized = True
                adapter.client = mock_openai_client

                registry = ModelRegistry()
                registry.register("gpt-4o", adapter, set_as_default=True)

                model = registry.get_default_model()
                response = model.generate(sample_messages)

                assert isinstance(response, ModelResponse)
                assert response.model == "gpt-4o"

    def test_router_records_success_on_generate(self):
        """Test that router can record model performance"""
        router = ModelRouter()

        # Simulate successful generation
        router.record_success("gpt-4o", latency_ms=500, input_tokens=100, output_tokens=50, cost=0.01)

        scores = router.get_scores()
        assert scores["gpt-4o"]["total_calls"] == 1
        assert scores["gpt-4o"]["success_rate"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
