"""
Mock 模型适配器 - 用于测试/演示（无需真实模型或API密钥）
"""

import time
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from models.base_model import BaseModelAdapter, ModelResponse, Message

logger = logging.getLogger(__name__)


class MockAdapter(BaseModelAdapter):
    """
    模拟模型适配器
    
    用于:
    - 开发和测试（无需API密钥）
    - 演示系统功能
    - 作为降级方案（当真实模型不可用时）
    
    特性:
    - 根据用户输入返回预设响应
    - 模拟延迟（可配置）
    - 生成符合 ModelResponse 格式的响应
    """
    
    def __init__(self, model_name: str = "mock-model", config: Optional[Dict[str, Any]] = None):
        """
        初始化模拟适配器
        
        Args:
            model_name: 模型名称（默认: mock-model）
            config: 配置字典（可选）
        """
        super().__init__(model_name, config)
        self.response_delay = 0.1  # 模拟延迟（秒）
        logger.info(f"模拟适配器已创建: {model_name}")
    
    def initialize(self) -> bool:
        """
        初始化模拟适配器（无需加载模型）
        
        Returns:
            bool: 始终返回 True
        """
        self.is_initialized = True
        logger.info("模拟适配器初始化完成")
        return True
    
    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> ModelResponse:
        """
        生成响应（模拟，异步实现）
        
        Args:
            messages: 对话历史
            temperature: 温度参数
            max_tokens: 最大生成Token数
            tools: 可用工具列表
            stream: 是否流式输出
            
        Returns:
            ModelResponse: 模拟响应
        """
        if not self.is_initialized:
            self.initialize()
        
        # 获取最后一条用户消息
        user_message = ""
        for msg in reversed(messages):
            if msg.role == "user":
                user_message = msg.content
                break
        
        # 记录开始时间
        start_time = time.time()
        
        # 生成模拟响应
        if stream:
            return self._generate_streaming(user_message, temperature)
        else:
            return await self._generate_non_streaming(user_message, temperature, start_time)
    
    async def _generate_non_streaming(
        self,
        user_message: str,
        temperature: float,
        start_time: float
    ) -> ModelResponse:
        """
        非流式生成（模拟，异步）
        
        Args:
            user_message: 用户消息
            temperature: 温度参数
            start_time: 开始时间
            
        Returns:
            ModelResponse: 模拟响应
        """
        # 模拟响应内容
        response_content = self._generate_mock_response(user_message)
        
        # 模拟延迟
        await asyncio.sleep(self.response_delay)
        
        # 计算Token数（估算）
        input_tokens = len(user_message) // 2
        output_tokens = len(response_content) // 2
        
        # 计算延迟
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 构建响应
        return ModelResponse(
            content=response_content,
            model=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=0.0,  # 模拟模型无成本
            latency_ms=latency_ms,
            metadata={
                "provider": "mock",
                "temperature": temperature,
                "note": "This is a mock response for testing. Configure a real model for actual responses.",
            }
        )
    
    async def _generate_streaming(
        self,
        user_message: str,
        temperature: float
    ) -> AsyncGenerator[str, None]:
        """
        流式生成（模拟，异步生成器）
        
        Args:
            user_message: 用户消息
            temperature: 温度参数
            
        Yields:
            str: 响应片段
        """
        # 生成模拟响应
        response_content = self._generate_mock_response(user_message)
        
        # 按字符流式输出
        for char in response_content:
            yield char
            await asyncio.sleep(0.01)  # 模拟延迟
    
    def _generate_mock_response(self, user_message: str) -> str:
        """
        生成模拟响应内容
        
        Args:
            user_message: 用户消息
            
        Returns:
            str: 模拟响应内容
        """
        # 根据用户输入生成不同的模拟响应
        user_lower = user_message.lower()
        
        if any(word in user_lower for word in ["hello", "hi", "你好", "嗨"]):
            return "Hello! I'm SerpentAI's mock assistant. This is a test response. Please configure a real model (OpenAI/Anthropic/Llama) for actual responses."
        
        elif any(word in user_lower for word in ["help", "帮助", "功能", "能做什么"]):
            return """SerpentAI is a powerful self-hosted AI agent framework supporting:

1. 4-layer memory system (instant/short-term/long-term/archive)
2. Tool integration layer (MCP protocol, tool pre-compilation)
3. Efficiency engine (Token optimization, prompt distillation)
4. Multi-channel gateway (Discord/Telegram/Feishu)
5. Graphical workflow editor
6. 5-layer security defense
7. Desktop client (Tauri)
8. Mobile PWA
9. Voice interaction (STT/TTS)
10. Python SDK

Currently you're seeing a mock response. Please configure a real model for actual help."""
        
        elif any(word in user_lower for word in ["model", "模型", "llm", "ai"]):
            return """To configure a real model, please:

1. OpenAI: Set OPENAI_API_KEY environment variable
2. Anthropic: Set ANTHROPIC_API_KEY environment variable
3. Local Llama: Install llama-cpp-python

See README.md for details.

Current mode: Mock (for testing only)"""
        
        elif any(word in user_lower for word in ["test", "测试", "ping"]):
            return f"Test successful! Server is running normally.\n\nCurrent time: {time.strftime('%Y-%m-%d %H:%M:%S')}\nModel: {self.model_name} (Mock)\nTemperature: {temperature}"
        
        else:
            return f"""Thank you for your message: "{user_message}"

This is a mock response from SerpentAI. To get real AI responses, please:

1. Configure model API keys, or
2. Install local models (llama.cpp)

See README.md for configuration methods.

---
Current mode: Mock
Model: {self.model_name}"""
    
    def count_tokens(self, text: str) -> int:
        """
        计算Token数（模拟，简单估算）
        
        Args:
            text: 输入文本
            
        Returns:
            int: 估算的Token数
        """
        # 简单估算: 1个Token ≈ 2个字符（英文）或1个字符（中文）
        return len(text) // 2
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            Dict: 模型信息
        """
        return {
            "name": self.model_name,
            "provider": "mock",
            "context_length": 4096,
            "is_mock": True,
            "supports_streaming": True,
            "supports_tools": True,
            "cost_per_1k_tokens": 0.0,
            "note": "This is a mock model for testing only."
        }
