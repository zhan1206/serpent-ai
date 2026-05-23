"""
额外测试 - 提高覆盖率到 >80%
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from backend.models.base_model import Message, ModelResponse, BaseModelAdapter


class TestErrorPaths:
    """测试错误路径以提高覆盖率"""

    def test_openai_adapter_initialize_exception(self):
        """测试 OpenAI 适配器初始化异常"""
        mock_openai_module = MagicMock()
        mock_openai_module.OpenAI.side_effect = Exception("Connection error")
        mock_openai_module.api_key = "test-key"
        
        with patch.dict('sys.modules', {'openai': mock_openai_module}):
            with patch('backend.models.openai_adapter.settings') as mock_settings:
                mock_settings.OPENAI_API_KEY = "test-key"
                
                if 'backend.models.openai_adapter' in __import__('sys').modules:
                    del __import__('sys').modules['backend.models.openai_adapter']
                
                from backend.models.openai_adapter import OpenAIAdapter
                adapter = OpenAIAdapter("gpt-4o")
                result = adapter.initialize()
                
                assert result == False

    def test_anthropic_adapter_generate_error(self):
        """测试 Anthropic 生成时的错误"""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client
        
        mock_settings = MagicMock()
        mock_settings.ANTHROPIC_API_KEY = "test-key"
        mock_settings.ANTHROPIC_API_BASE = None
        
        with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
            with patch('core.config.settings', mock_settings):
                if 'backend.models.anthropic_adapter' in __import__('sys').modules:
                    del __import__('sys').modules['backend.models.anthropic_adapter']
                
                from backend.models.anthropic_adapter import AnthropicAdapter
                adapter = AnthropicAdapter("claude-3-opus")
                adapter.client = mock_client
                adapter.is_initialized = True
                
                messages = [Message(role="user", content="Hello")]
                
                with pytest.raises(Exception):
                    adapter.generate(messages)

    def test_llama_adapter_model_file_not_found(self):
        """测试 Llama 模型文件不存在"""
        mock_llama_module = MagicMock()
        
        with patch.dict('sys.modules', {'llama_cpp': mock_llama_module}):
            with patch('backend.models.llama_adapter.settings') as mock_settings:
                mock_settings.LLAMA_CPP_THREADS = 4
                mock_settings.LLAMA_CPP_GPU_LAYERS = 0
                mock_settings.LOCAL_MODEL_DIR = "/tmp/models"
                
                if 'backend.models.llama_adapter' in __import__('sys').modules:
                    del __import__('sys').modules['backend.models.llama_adapter']
                
                from backend.models.llama_adapter import LlamaAdapter
                with patch.object(LlamaAdapter, '_find_model_file', return_value=None):
                    adapter = LlamaAdapter("llama-3-8b")
                    result = adapter.initialize()
                    
                    assert result == False

    def test_openai_generate_api_error(self):
        """测试 OpenAI 生成时 API 错误"""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        mock_openai_module = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client
        mock_openai_module.api_key = "test-key"
        
        with patch.dict('sys.modules', {'openai': mock_openai_module}):
            with patch('backend.models.openai_adapter.settings') as mock_settings:
                mock_settings.OPENAI_API_KEY = "test-key"
                
                if 'backend.models.openai_adapter' in __import__('sys').modules:
                    del __import__('sys').modules['backend.models.openai_adapter']
                
                from backend.models.openai_adapter import OpenAIAdapter
                adapter = OpenAIAdapter("gpt-4o")
                adapter.client = mock_client
                adapter.is_initialized = True
                
                messages = [Message(role="user", content="Hello")]
                
                with pytest.raises(Exception):
                    adapter.generate(messages)

    def test_registry_get_model_info_empty(self):
        """测试获取空注册表的信息"""
        from backend.models.registry import ModelRegistry
        
        registry = ModelRegistry()
        info = registry.get_model_info()
        
        assert info == {}

    @pytest.mark.asyncio
    async def test_mock_adapter_generate_with_tool_calls(self):
        """测试 Mock 适配器处理工具调用消息"""
        from backend.models.mock_adapter import MockAdapter
        
        adapter = MockAdapter("mock")
        adapter.initialize()
        
        messages = [
            Message(role="assistant", content="", tool_calls=[{"id": "1", "function": {"name": "test", "arguments": "{}"}}]),
            Message(role="tool", content="result", name="test", tool_call_id="1")
        ]
        
        response = await adapter.generate(messages)
        
        assert hasattr(response, 'content')
        assert response.content != ""


class TestLlamaAdapterExtra:
    """Llama 适配器额外测试"""

    def test_download_model_no_hub(self):
        """测试下载模型时 huggingface_hub 未安装"""
        from backend.models.llama_adapter import LlamaAdapter
        
        # 模拟 from huggingface_hub import hf_hub_download 失败
        with patch('builtins.__import__', side_effect=ImportError("No module")):
            with pytest.raises(ImportError):
                LlamaAdapter.download_model("test/model")

    def test_get_model_info_unknown_model(self):
        """测试未知模型的信息"""
        mock_llama_module = MagicMock()
        
        with patch.dict('sys.modules', {'llama_cpp': mock_llama_module}):
            with patch('backend.models.llama_adapter.settings') as mock_settings:
                mock_settings.LLAMA_CPP_THREADS = 4
                mock_settings.LLAMA_CPP_GPU_LAYERS = 0
                
                if 'backend.models.llama_adapter' in __import__('sys').modules:
                    del __import__('sys').modules['backend.models.llama_adapter']
                
                from backend.models.llama_adapter import LlamaAdapter
                adapter = LlamaAdapter("unknown-model")
                adapter.is_initialized = True
                
                info = adapter.get_model_info()
                
                assert info["name"] == "unknown-model"
                assert info["context_length"] == 2048  # 默认值


class TestOpenAIAdapterExtra:
    """OpenAI 适配器额外测试"""

    def test_get_model_info_unknown_model(self):
        """测试未知模型的信息"""
        mock_openai_module = MagicMock()
        mock_openai_module.OpenAI = MagicMock()
        mock_openai_module.api_key = "test-key"
        
        with patch.dict('sys.modules', {'openai': mock_openai_module}):
            with patch('backend.models.openai_adapter.settings') as mock_settings:
                mock_settings.OPENAI_API_KEY = "test-key"
                
                if 'backend.models.openai_adapter' in __import__('sys').modules:
                    del __import__('sys').modules['backend.models.openai_adapter']
                
                from backend.models.openai_adapter import OpenAIAdapter
                adapter = OpenAIAdapter("unknown-model")
                adapter.is_initialized = True
                
                info = adapter.get_model_info()
                
                assert info["name"] == "unknown-model"
                assert info["context_length"] == 8192  # 默认值
                assert info["pricing"]["input"] == 0.01  # 默认价格


class TestAnthropicAdapterExtra:
    """Anthropic 适配器额外测试"""

    def test_get_model_info_unknown_model(self):
        """测试未知模型的信息"""
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic = MagicMock()
        
        with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
            with patch('backend.models.anthropic_adapter.settings') as mock_settings:
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                
                if 'backend.models.anthropic_adapter' in __import__('sys').modules:
                    del __import__('sys').modules['backend.models.anthropic_adapter']
                
                from backend.models.anthropic_adapter import AnthropicAdapter
                adapter = AnthropicAdapter("unknown-model")
                adapter.is_initialized = True
                
                info = adapter.get_model_info()
                
                assert info["name"] == "unknown-model"
                assert info["context_length"] == 200000  # 默认值
                assert info["pricing"]["input"] == 0.01  # 默认价格

    def test_count_tokens_fallback(self):
        """测试 Anthropic Token 计数回退到估算"""
        mock_client = MagicMock()
        mock_client.messages.count_tokens.side_effect = Exception("API Error")
        
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client
        
        mock_settings = MagicMock()
        mock_settings.ANTHROPIC_API_KEY = "test-key"
        
        with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
            with patch('core.config.settings', mock_settings):
                if 'backend.models.anthropic_adapter' in __import__('sys').modules:
                    del __import__('sys').modules['backend.models.anthropic_adapter']
                
                from backend.models.anthropic_adapter import AnthropicAdapter
                adapter = AnthropicAdapter("claude-3-opus")
                adapter.client = mock_client
                adapter.is_initialized = True
                
                count = adapter.count_tokens("测试文本")
                
                assert isinstance(count, int)
                assert count > 0
