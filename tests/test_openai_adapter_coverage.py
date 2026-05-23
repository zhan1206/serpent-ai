"""
Comprehensive tests for OpenAI adapter to improve coverage from 21% to 80%+
Tests cover all methods and edge cases with mocked API calls
"""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any, Optional

# Mock the openai module before importing
sys.modules['openai'] = Mock()
sys.modules['openai'].api_key = None
sys.modules['openai'].OpenAI = Mock

from backend.models.openai_adapter import OpenAIAdapter
from backend.models.base_model import Message, ModelResponse


class TestOpenAIAdapter:
    """Comprehensive test suite for OpenAIAdapter"""
    
    @pytest.fixture
    def adapter(self):
        """Create an OpenAI adapter instance"""
        return OpenAIAdapter(model_name="gpt-4o", config={"api_key": "test-key"})
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a properly mocked OpenAI client"""
        client = MagicMock()
        
        # Setup the chat.completions.create mock
        mock_message = Mock()
        mock_message.content = "Hello, I'm OpenAI"
        
        mock_choice = Mock()
        mock_choice.message = mock_message
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        
        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 5
        mock_response.usage = mock_usage
        
        client.chat.completions.create.return_value = mock_response
        
        # Setup models.list mock
        mock_model = Mock()
        mock_model.id = "gpt-4o"
        mock_models_page = Mock()
        mock_models_page.data = [mock_model]
        client.models.list.return_value = mock_models_page
        
        return client
    
    def test_initialization(self):
        """Test adapter initialization with various configs"""
        # Test with config api_key
        adapter = OpenAIAdapter("gpt-4o", config={"api_key": "config-key"})
        assert adapter.model_name == "gpt-4o"
        assert adapter.config["api_key"] == "config-key"
        assert adapter.is_initialized is False
        assert adapter.base_url is None  # Set during initialize()
        
        # Test with base_url in config
        adapter = OpenAIAdapter("gpt-4o", config={"api_key": "key", "base_url": "https://custom.com"})
        assert adapter.config.get("base_url") == "https://custom.com"
        assert adapter.base_url is None  # Set during initialize()
    
    @patch('backend.models.openai_adapter.openai')
    @patch('backend.models.openai_adapter.settings')
    def test_initialize_success(self, mock_settings, mock_openai, mock_openai_client):
        """Test successful initialization"""
        mock_settings.OPENAI_API_KEY = "settings-key"
        mock_settings.OPENAI_API_BASE = None
        mock_openai.OpenAI.return_value = mock_openai_client
        
        adapter = OpenAIAdapter("gpt-4o", config={"api_key": "test-key"})
        result = adapter.initialize()
        
        assert result is True
        assert adapter.is_initialized is True
        assert adapter.client is not None
    
    @patch('backend.models.openai_adapter.settings')
    def test_initialize_no_api_key(self, mock_settings):
        """Test initialization failure when no API key"""
        mock_settings.OPENAI_API_KEY = None
        mock_settings.OPENAI_API_BASE = None
        
        adapter = OpenAIAdapter("gpt-4o", config={})
        result = adapter.initialize()
        
        assert result is False
        assert adapter.is_initialized is False
    
    @patch('backend.models.openai_adapter.openai')
    def test_initialize_connection_error(self, mock_openai):
        """Test initialization failure on connection error"""
        mock_client = MagicMock()
        mock_client.models.list.side_effect = Exception("Connection failed")
        mock_openai.OpenAI.return_value = mock_client
        
        adapter = OpenAIAdapter("gpt-4o", config={"api_key": "test-key"})
        adapter.api_key = "test-key"
        
        result = adapter.initialize()
        
        assert result is False
    
    @patch('backend.models.openai_adapter.openai')
    def test_generate_not_initialized(self, mock_openai):
        """Test generate raises error when not initialized"""
        adapter = OpenAIAdapter("gpt-4o", config={"api_key": "test-key"})
        adapter.is_initialized = False
        
        # Make initialize return False
        with patch.object(OpenAIAdapter, 'initialize', return_value=False):
            messages = [Message(role="user", content="Hello")]
            
            with pytest.raises(RuntimeError, match="OpenAI适配器未初始化"):
                adapter.generate(messages)
    
    def test_validate_messages(self):
        """Test message validation"""
        adapter = OpenAIAdapter("gpt-4o")
        
        # Valid messages
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi"),
            Message(role="tool", content="Result", tool_call_id="123")
        ]
        assert adapter.validate_messages(messages) is True
        
        # Empty messages
        assert adapter.validate_messages([]) is False
        
        # Invalid role
        bad_messages = [Message(role="invalid", content="test")]
        assert adapter.validate_messages(bad_messages) is False
    
    def test_count_tokens(self):
        """Test token counting"""
        adapter = OpenAIAdapter("gpt-4o")
        
        text = "Hello world"
        tokens = adapter.count_tokens(text)
        assert isinstance(tokens, int)
        assert tokens > 0
        
        # Test with empty string
        assert adapter.count_tokens("") == 0
        
        # Test with long text
        long_text = "a" * 1000
        assert adapter.count_tokens(long_text) > 0
    
    def test_get_model_info(self):
        """Test getting model info"""
        adapter = OpenAIAdapter("gpt-4o")
        adapter.is_initialized = True
        
        info = adapter.get_model_info()
        assert info["name"] == "gpt-4o"
        assert info["provider"] == "openai"
        assert info["context_length"] == 128000
        assert "input" in info["pricing"]
        
        # Test with unknown model
        adapter.model_name = "unknown-model"
        info = adapter.get_model_info()
        assert info["context_length"] == 8192  # Default
    
    def test_estimate_cost(self):
        """Test cost estimation"""
        adapter = OpenAIAdapter("gpt-4o")
        
        # Test with gpt-4o
        adapter.model_name = "gpt-4o"
        cost = adapter.estimate_cost(1000, 500)
        expected = (1000/1000) * 0.005 + (500/1000) * 0.015
        assert abs(cost - expected) < 0.001
        
        # Test with unknown model (uses default pricing)
        adapter.model_name = "unknown"
        cost = adapter.estimate_cost(1000, 500)
        expected = (1000/1000) * 0.01 + (500/1000) * 0.03
        assert abs(cost - expected) < 0.001
    
    def test_pricing_lookup(self):
        """Test pricing lookup for various models"""
        test_cases = [
            ("gpt-4o", 0.005, 0.015),
            ("gpt-4o-mini", 0.00015, 0.0006),
            ("gpt-4-turbo", 0.01, 0.03),
            ("gpt-3.5-turbo", 0.0005, 0.0015),
            ("o1-preview", 0.015, 0.06),
        ]
        
        for model_name, expected_input, expected_output in test_cases:
            adapter = OpenAIAdapter(model_name)
            # Access pricing directly from class var
            pricing = OpenAIAdapter.PRICING.get(model_name, {"input": 0.01, "output": 0.03})
            assert pricing["input"] == expected_input
            assert pricing["output"] == expected_output
    
    def test_context_length_lookup(self):
        """Test context length lookup"""
        test_cases = [
            ("gpt-4o", 128000),
            ("gpt-3.5-turbo", 16385),
            ("gpt-4", 8192),
        ]
        
        for model_name, expected_length in test_cases:
            adapter = OpenAIAdapter(model_name)
            length = OpenAIAdapter.CONTEXT_LENGTHS.get(model_name, 8192)
            assert length == expected_length
    
    @patch('backend.models.openai_adapter.openai')
    def test_generate_success(self, mock_openai, mock_openai_client):
        """Test successful generation"""
        adapter = OpenAIAdapter("gpt-4o", config={"api_key": "test-key"})
        adapter.is_initialized = True
        adapter.client = mock_openai_client
        
        messages = [Message(role="user", content="Hello")]
        response = adapter.generate(messages)
        
        # Just check it's not None and has expected attributes
        assert response is not None
        assert hasattr(response, 'content')
        assert hasattr(response, 'model')
        assert response.model == "gpt-4o"
    
    @patch('backend.models.openai_adapter.openai')
    def test_generate_with_tools(self, mock_openai, mock_openai_client):
        """Test generate with tool calls"""
        adapter = OpenAIAdapter("gpt-4o", config={"api_key": "test-key"})
        adapter.is_initialized = True
        adapter.client = mock_openai_client
        
        messages = [Message(role="user", content="What's the weather?")]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {}
                }
            }
        ]
        
        response = adapter.generate(messages, tools=tools)
        
        assert response.content == "Hello, I'm OpenAI"
        assert response.input_tokens == 10
        
        # Verify tools were passed to API
        call_args = mock_openai_client.chat.completions.create.call_args
        assert "tools" in call_args.kwargs
    
    @patch('backend.models.openai_adapter.openai')
    def test_generate_with_temperature(self, mock_openai, mock_openai_client):
        """Test generate with temperature parameter"""
        adapter = OpenAIAdapter("gpt-4o", config={"api_key": "test-key"})
        adapter.is_initialized = True
        adapter.client = mock_openai_client
        
        messages = [Message(role="user", content="Hello")]
        adapter.generate(messages, temperature=0.9)
        
        # Verify temperature was passed
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.9
    
    @patch('backend.models.openai_adapter.openai')
    def test_generate_with_max_tokens(self, mock_openai, mock_openai_client):
        """Test generate with max_tokens parameter"""
        adapter = OpenAIAdapter("gpt-4o", config={"api_key": "test-key"})
        adapter.is_initialized = True
        adapter.client = mock_openai_client
        
        messages = [Message(role="user", content="Hello")]
        adapter.generate(messages, max_tokens=100)
        
        # Verify max_tokens was passed
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args.kwargs["max_tokens"] == 100
