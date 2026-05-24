"""
SerpentAI 模型抽象层 - Llama.cpp适配器
支持本地运行开源模型（Llama 3, Mistral, Qwen等）
基于llama.cpp Python绑定，支持CPU和GPU加速
"""
import os
from typing import List, Dict, Any, Optional, Generator
import logging
import time
from pathlib import Path
import json

from backend.core.config import settings
from backend.models.base_model import BaseModelAdapter, Message, ModelResponse, TokenUsage

logger = logging.getLogger(__name__)

class LlamaAdapter(BaseModelAdapter):
    """
    Llama.cpp模型适配器
    支持本地运行开源大模型
    支持模型：Llama 3/2, Mistral, Qwen, Gemma等
    """
    
    # 支持的模型列表及默认参数
    SUPPORTED_MODELS = {
        "llama-3-8b": {
            "context_length": 8192,
            "threads": 4,
            "gpu_layers": 0,
        },
        "llama-3-70b": {
            "context_length": 8192,
            "threads": 8,
            "gpu_layers": 0,
        },
        "mistral-7b": {
            "context_length": 8192,
            "threads": 4,
            "gpu_layers": 0,
        },
        "qwen-7b": {
            "context_length": 8192,
            "threads": 4,
            "gpu_layers": 0,
        },
        "gemma-7b": {
            "context_length": 8192,
            "threads": 4,
            "gpu_layers": 0,
        },
    }
    
    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化Llama.cpp适配器
        
        Args:
            model_name: 模型名称（如 llama-3-8b）
            config: 配置字典（model_path, threads, gpu_layers等）
        """
        super().__init__(model_name, config)
        self.llama = None
        self.model_path = None
        self.n_ctx = 2048
        self.n_threads = settings.LLAMA_CPP_THREADS
        self.n_gpu_layers = settings.LLAMA_CPP_GPU_LAYERS
    
    def initialize(self) -> bool:
        """
        初始化Llama.cpp模型
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            from llama_cpp import Llama
            
            # 获取模型路径
            self.model_path = (
                self.config.get("model_path") or 
                self._find_model_file()
            )
            
            if not self.model_path or not Path(self.model_path).exists():
                logger.error(f"模型文件不存在: {self.model_path}")
                return False
            
            # 获取模型参数
            model_key = self.model_name.lower()
            model_config = self.SUPPORTED_MODELS.get(model_key, {})
            
            self.n_ctx = self.config.get("n_ctx") or model_config.get("context_length", 2048)
            self.n_threads = self.config.get("n_threads") or model_config.get("threads", settings.LLAMA_CPP_THREADS)
            self.n_gpu_layers = self.config.get("n_gpu_layers") or model_config.get("gpu_layers", settings.LLAMA_CPP_GPU_LAYERS)
            
            # 创建Llama实例
            self.llama = Llama(
                model_path=str(self.model_path),
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False,
            )
            
            self.is_initialized = True
            logger.info(f"Llama.cpp适配器初始化成功: {self.model_name}")
            logger.info(f"  模型路径: {self.model_path}")
            logger.info(f"  上下文长度: {self.n_ctx}")
            logger.info(f"  CPU线程数: {self.n_threads}")
            logger.info(f"  GPU层数: {self.n_gpu_layers}")
            return True
            
        except ImportError:
            logger.error("llama-cpp-python未安装，请运行: pip install llama-cpp-python")
            return False
        except Exception as e:
            logger.error(f"Llama.cpp适配器初始化失败: {e}")
            return False
    
    def _find_model_file(self) -> Optional[Path]:
        """
        自动查找模型文件
        
        Returns:
            Optional[Path]: 模型文件路径
        """
        model_dir = Path(settings.LOCAL_MODEL_DIR)
        
        if not model_dir.exists():
            logger.warning(f"本地模型目录不存在: {model_dir}")
            return None
        
        # 模型文件可能的后缀
        extensions = [".gguf", ".bin", ".ggml"]
        
        # 搜索匹配的模型文件
        for ext in extensions:
            pattern = f"*{self.model_name}*{ext}"
            matches = list(model_dir.glob(pattern))
            if matches:
                logger.info(f"找到模型文件: {matches[0]}")
                return matches[0]
        
        logger.warning(f"未找到模型文件: {self.model_name}")
        return None
    
    def _convert_messages_to_prompt(self, messages: List[Message]) -> str:
        """
        将消息列表转换为Llama.cpp格式的提示词
        
        Returns:
            str: 格式化的提示词
        """
        prompt_parts = []
        
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")
            elif msg.role == "tool":
                prompt_parts.append(f"Tool ({msg.name}): {msg.content}")
        
        prompt_parts.append("Assistant:")
        return "\n".join(prompt_parts)
    
    def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> ModelResponse:
        """
        生成响应
        
        Args:
            messages: 对话历史
            temperature: 温度参数
            max_tokens: 最大生成Token数
            tools: 可用工具列表（本地模型暂不支持Function Calling）
            stream: 是否流式输出
            
        Returns:
            ModelResponse: 模型响应
        """
        if not self.is_initialized:
            if not self.initialize():
                raise RuntimeError("Llama.cpp适配器未初始化")
        
        # 验证消息
        if not self.validate_messages(messages):
            raise ValueError("消息格式无效")
        
        # 转换消息为提示词
        prompt = self._convert_messages_to_prompt(messages)
        
        # 设置生成参数
        max_tokens = max_tokens or 2048
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 调用llama.cpp生成
            if stream:
                # 流式输出（简化版）
                response_stream = self.llama(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True
                )
                
                content_parts = []
                for output in response_stream:
                    content_parts.append(output['choices'][0]['text'])
                
                content = "".join(content_parts)
                
            else:
                # 非流式输出
                response = self.llama(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=False
                )
                
                content = response['choices'][0]['text']
            
            # 计算Token数（估算）
            input_tokens = self.count_tokens(prompt)
            output_tokens = self.count_tokens(content)
            
            # 计算延迟
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 构建响应
            model_response = ModelResponse(
                content=content,
                model=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                cost=0.0,  # 本地模型无API成本
                latency_ms=latency_ms,
                metadata={
                    "provider": "local",
                    "model_path": str(self.model_path),
                    "n_ctx": self.n_ctx,
                    "n_threads": self.n_threads,
                    "n_gpu_layers": self.n_gpu_layers,
                }
            )
            
            logger.info(
                f"Llama.cpp生成成功 | "
                f"模型: {self.model_name} | "
                f"输入: {input_tokens} | "
                f"输出: {output_tokens} | "
                f"延迟: {latency_ms}ms | "
                f"成本: $0.00 (本地)"
            )
            
            return model_response
            
        except Exception as e:
            logger.error(f"Llama.cpp生成失败: {e}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的Token数
        使用简单估算（llama.cpp有自己的tokenizer）
        
        Args:
            text: 输入文本
            
        Returns:
            int: Token数量
        """
        # 简单估算：1个Token ≈ 1.3个字符
        return len(text) // 1
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            Dict: 模型信息
        """
        model_key = self.model_name.lower()
        model_config = self.SUPPORTED_MODELS.get(model_key, {})
        
        return {
            "name": self.model_name,
            "provider": "local",
            "context_length": model_config.get("context_length", 2048),
            "pricing": {"input": 0.0, "output": 0.0},  # 本地模型免费
            "supports_tools": False,  # 本地模型暂不支持Function Calling
            "supports_streaming": True,
            "initialized": self.is_initialized,
            "model_path": str(self.model_path) if self.model_path else None,
            "n_threads": self.n_threads,
            "n_gpu_layers": self.n_gpu_layers,
        }
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        估算成本（本地模型为0）
        
        Returns:
            float: 0.0
        """
        return 0.0
    
    def unload_model(self):
        """
        卸载模型以释放内存
        """
        if self.llama is not None:
            del self.llama
            self.llama = None
            self.is_initialized = False
            logger.info(f"模型已卸载: {self.model_name}")
    
    @staticmethod
    def download_model(model_name: str, output_dir: Optional[str] = None) -> Path:
        """
        下载模型文件（辅助函数）
        使用huggingface_hub下载GGUF格式的模型
        
        Args:
            model_name: 模型名称（HuggingFace仓库名）
            output_dir: 输出目录
            
        Returns:
            Path: 下载的模型文件路径
        """
        try:
            from huggingface_hub import hf_hub_download
            
            output_dir = output_dir or settings.LOCAL_MODEL_DIR
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # 下载GGUF文件
            model_path = hf_hub_download(
                repo_id=model_name,
                filename="*.gguf",  # 自动匹配GGUF文件
                local_dir=output_dir,
                local_dir_use_symlinks=False
            )
            
            logger.info(f"模型下载成功: {model_path}")
            return Path(model_path)
            
        except ImportError:
            logger.error("huggingface_hub未安装，请运行: pip install huggingface_hub")
            raise
        except Exception as e:
            logger.error(f"模型下载失败: {e}")
            raise
