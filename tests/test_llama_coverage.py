"""
额外测试 - 提高 llama_adapter.py 覆盖率到 >80%
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, MagicMock


class TestLlamaAdapterCoverage:
    """Llama 适配器覆盖率测试"""

    def test_find_model_file_with_gguf(self):
        """测试查找 .gguf 模型文件"""
        mock_llama_module = MagicMock()
        
        with patch.dict('sys.modules', {'llama_cpp': mock_llama_module}):
            # 创建临时目录和模型文件
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                # 直接设置 settings.LOCAL_MODEL_DIR
                import backend.models.llama_adapter as mod
                original_dir = mod.settings.LOCAL_MODEL_DIR
                mod.settings.LOCAL_MODEL_DIR = tmpdir
                
                try:
                    # 创建测试模型文件
                    from pathlib import Path
                    model_file = Path(tmpdir) / "llama-3-8b-Q4_K_M.gguf"
                    model_file.write_text("fake model")
                    
                    if 'backend.models.llama_adapter' in __import__('sys').modules:
                        del __import__('sys').modules['backend.models.llama_adapter']
                    
                    from backend.models.llama_adapter import LlamaAdapter
                    adapter = LlamaAdapter("llama-3-8b")
                    
                    result = adapter._find_model_file()
                    
                    assert result is not None
                    assert result.exists()
                finally:
                    mod.settings.LOCAL_MODEL_DIR = original_dir

    def test_find_model_file_not_found(self):
        """测试找不到模型文件"""
        mock_llama_module = MagicMock()
        
        with patch.dict('sys.modules', {'llama_cpp': mock_llama_module}):
            with patch('backend.models.llama_adapter.settings') as mock_settings:
                mock_settings.LLAMA_CPP_THREADS = 4
                mock_settings.LLAMA_CPP_GPU_LAYERS = 0
                mock_settings.LOCAL_MODEL_DIR = "/nonexistent_path"
                
                if 'backend.models.llama_adapter' in __import__('sys').modules:
                    del __import__('sys').modules['backend.models.llama_adapter']
                
                from backend.models.llama_adapter import LlamaAdapter
                adapter = LlamaAdapter("nonexistent-model")
                
                result = adapter._find_model_file()
                
                assert result is None

    def test_generate_streaming_code_path(self):
        """测试流式生成的代码路径"""
        mock_llama_module = MagicMock()
        mock_instance = MagicMock()
        
        # 模拟流式输出
        mock_instance.return_value = [
            {"choices": [{"text": "Hello"}]},
            {"choices": [{"text": " world"}]},
        ]
        mock_llama_module.Llama.return_value = mock_instance
        
        with patch.dict('sys.modules', {'llama_cpp': mock_llama_module}):
            with patch('backend.models.llama_adapter.settings') as mock_settings:
                mock_settings.LLAMA_CPP_THREADS = 4
                mock_settings.LLAMA_CPP_GPU_LAYERS = 0
                mock_settings.LOCAL_MODEL_DIR = "/tmp"
                
                if 'backend.models.llama_adapter' in __import__('sys').modules:
                    del __import__('sys').modules['backend.models.llama_adapter']
                
                from backend.models.llama_adapter import LlamaAdapter
                with patch.object(LlamaAdapter, '_find_model_file', return_value="/tmp/test.gguf"):
                    adapter = LlamaAdapter("llama-3-8b")
                    adapter.llama = mock_instance
                    adapter.is_initialized = True
                    adapter.model_path = "/tmp/test.gguf"
                    
                    from backend.models.base_model import Message
                    messages = [Message(role="user", content="Hello")]
                    
                    response = adapter.generate(messages, stream=True)
                    
                    assert hasattr(response, 'content')
                    assert "Hello" in response.content

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

    def test_download_model_success(self):
        """测试成功下载模型"""
        mock_llama_module = MagicMock()
        
        with patch.dict('sys.modules', {'llama_cpp': mock_llama_module}):
            if 'backend.models.llama_adapter' in __import__('sys').modules:
                del __import__('sys').modules['backend.models.llama_adapter']
            
            from backend.models.llama_adapter import LlamaAdapter
            
            # 模拟 huggingface_hub 导入和下载
            mock_hf = MagicMock(return_value="/tmp/model.gguf")
            
            with patch.dict('sys.modules', {'huggingface_hub': MagicMock(hf_hub_download=mock_hf)}):
                with patch('pathlib.Path.mkdir'):
                    result = LlamaAdapter.download_model(
                        "TheBloke/Llama-3-8B-GGUF",
                        output_dir="/tmp"
                    )
                    
                    assert result is not None

    def test_generate_with_max_tokens(self):
        """测试指定 max_tokens"""
        mock_llama_module = MagicMock()
        mock_instance = MagicMock()
        mock_instance.return_value = {"choices": [{"text": "Response"}]}
        mock_llama_module.Llama.return_value = mock_instance
        
        with patch.dict('sys.modules', {'llama_cpp': mock_llama_module}):
            with patch('backend.models.llama_adapter.settings') as mock_settings:
                mock_settings.LLAMA_CPP_THREADS = 4
                mock_settings.LLAMA_CPP_GPU_LAYERS = 0
                mock_settings.LOCAL_MODEL_DIR = "/tmp"
                
                if 'backend.models.llama_adapter' in __import__('sys').modules:
                    del __import__('sys').modules['backend.models.llama_adapter']
                
                from backend.models.llama_adapter import LlamaAdapter
                with patch.object(LlamaAdapter, '_find_model_file', return_value="/tmp/test.gguf"):
                    adapter = LlamaAdapter("llama-3-8b")
                    adapter.llama = mock_instance
                    adapter.is_initialized = True
                    
                    from backend.models.base_model import Message
                    messages = [Message(role="user", content="Hello")]
                    
                    # 指定 max_tokens
                    response = adapter.generate(messages, max_tokens=512)
                    
                    # 验证 max_tokens 被传递
                    call_args = mock_instance.call_args
                    assert call_args.kwargs["max_tokens"] == 512
