"""
Tests for Anthropic adapter to improve coverage from 18% to 80%+
Focuses on testable methods with proper mocking
"""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

# Mock the anthropic module before importing
sys.modules['anthropic'] = Mock()
sys.modules['anthropic'].Anthropic = Mock

from backend.models.anthropic_adapter import AnthropicAdapter
from backend.models.base_model import Message, ModelResponse


class TestAnthropicAdapter:
    """Test suite for AnthropicAdapter"""
    
    @pytest.fixture
    def adapter(self):
        """Create an Anthropic adapter instance"""
        return AnthropicAdapter(model_name="claude-3-opus", config={"api_key": "test-key"})
    
    def test_initialization(self):
        """Test adapter initialization"""
        adapter = AnthropicAdapter("claude-3-opus", config={"api_key": "config-key"})
        assert adapter.model_name == "claude-3-opus"
        assert adapter.config["api_key"] == "config-key"
        assert adapter.is_initialized is False
    
    @patch('backend.models.anthropic_adapter.anthropic')
    @patch('backend.models.anthropic_adapter.settings')
    def test_initialize_success(self, mock_settings, mock_anthropic):
        """Test successful initialization"""
        mock_settings.ANTHROPIC_API_KEY = "settings-key"
        
        mock_client = MagicMock()
        mock_model = Mock()
        mock_model.id = "claude-3-opus"
        mock_page = Mock()
        mock_page.data = [mock_model]
        mock_client.models.list.return_value = mock_page
        mock_anthropic.Anthropic.return_value = mock_client
        
        adapter = AnthropicAdapter("claude-3-opus", config={"api_key": "test-key"})
        result = adapter.initialize()
        
        assert result is True
        assert adapter.is_initialized is True
    
    @patch('backend.models.anthropic_adapter.settings')
    def test_initialize_no_api_key(self, mock_settings):
        """Test initialization failure when no API key"""
        mock_settings.ANTHROPIC_API_KEY = None
        
        adapter = AnthropicAdapter("claude-3-opus", config={})
        result = adapter.initialize()
        
        assert result is False
        assert adapter.is_initialized is False
    
    def test_convert_messages_to_anthropic_format(self):
        """Test message conversion to Anthropic format"""
        adapter = AnthropicAdapter("claude-3-opus")
        
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there"),
            Message(role="user", content="How are you?")
        ]
        
        anthropic_messages, system_message = adapter._convert_messages_to_anthropic_format(messages)
        
        assert system_message == "You are helpful"
        assert len(anthropic_messages) == 3
        assert anthropic_messages[0]["role"] == "user"
        assert anthropic_messages[0]["content"] == "Hello"
        assert anthropic_messages[1]["role"] == "assistant"
    
    def test_validate_messages(self):
        """Test message validation"""
        adapter = AnthropicAdapter("claude-3-opus")
        
        # Valid messages
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi"),
        ]
        assert adapter.validate_messages(messages) is True
        
        # Empty messages
        assert adapter.validate_messages([]) is False
        
        # Invalid role
        bad_messages = [Message(role="invalid", content="test")]
        assert adapter.validate_messages(bad_messages) is False
    
    def test_count_tokens(self):
        """Test token counting"""
        adapter = AnthropicAdapter("claude-3-opus")
        
        text = "Hello world"
        tokens = adapter.count_tokens(text)
        assert isinstance(tokens, int)
        assert tokens > 0
        
        # Test with empty string
        assert adapter.count_tokens("") == 0
    
    def test_get_model_info(self):
        """Test getting model info"""
        adapter = AnthropicAdapter("claude-3-opus")
        adapter.is_initialized = True
        
        info = adapter.get_model_info()
        assert info["name"] == "claude-3-opus"
        assert info["provider"] == "anthropic"
        assert info["context_length"] == 200000
        assert info["supports_tools"] is True
        assert info["supports_vision"] is True
        
        # Test with unknown model
        adapter.model_name = "unknown-model"
        info = adapter.get_model_info()
        assert info["context_length"] == 200000  # Default for Anthropic
    
    def test_estimate_cost(self):
        """Test cost estimation"""
        adapter = AnthropicAdapter("claude-3-opus")
        
        # Test with claude-3-opus
        adapter.model_name = "claude-3-opus"
        cost = adapter.estimate_cost(1000, 500)
        expected = (1000/1000) * 0.015 + (500/1000) * 0.075
        assert abs(cost - expected) < 0.001
    
    def test_pricing_lookup(self):
        """Test pricing lookup for various models"""
        test_cases = [
            ("claude-3-opus", 0.015, 0.075),
            ("claude-3-sonnet", 0.003, 0.015),
            ("claude-3-haiku", 0.00025, 0.00125),
        ]
        
        for model_name, expected_input, expected_output in test_cases:
            adapter = AnthropicAdapter(model_name)
            pricing = adapter.PRICING.get(model_name, {"input": 0.01, "output": 0.03})
            assert pricing["input"] == expected_input
            assert pricing["output"] == expected_output
    
    def test_context_length_lookup(self):
        """Test context length lookup"""
        test_cases = [
            ("claude-3-opus", 200000),
            ("claude-3-sonnet", 200000),
            ("claude-2.1", 200000),
        ]
        
        for model_name, expected_length in test_cases:
            adapter = AnthropicAdapter(model_name)
            length = adapter.CONTEXT_LENGTHS.get(model_name, 200000)
            assert length == expected_length
    
    @patch('backend.models.anthropic_adapter.anthropic')
    def test_generate_not_initialized(self, mock_anthropic):
        """Test generate raises error when not initialized"""
        adapter = AnthropicAdapter("claude-3-opus", config={"api_key": "test-key"})
        adapter.is_initialized = False
        
        messages = [Message(role="user", content="Hello")]
        
        # Mock initialize to return False
        with patch.object(AnthropicAdapter, 'initialize', return_value=False):
            with pytest.raises(RuntimeError, match="Anthropic适配器未初始化"):
                adapter.generate(messages)
