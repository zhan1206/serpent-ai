"""
Mock 模型适配器
当没有可用模型时提供测试/演示功能
"""
import logging
import time
import json
from typing import List, Dict, Any, Optional, Generator

from models.base_model import BaseModelAdapter, ModelResponse, Message

logger = logging.getLogger(__name__)


class MockAdapter(BaseModelAdapter):
    """
    模拟模型适配器
    用于测试和演示（不需要真实模型或API密钥）
    """
    
    def __init__(self, model_name: str = "mock-model", config: Optional[Dict[str, Any]] = None):
        """
        初始化模拟适配器
        
        Args:
            model_name: 模型名称
            config: 配置字典
        """
        super().__init__(model_name, config)
        self.is_initialized = True  # 模拟适配器立即就绪
        logger.info(f"模拟适配器初始化: {model_name}")
    
    def initialize(self) -> bool:
        """
        初始化（模拟）
        
        Returns:
            bool: 始终返回 True
        """
        self.is_initialized = True
        logger.info("模拟适配器初始化完成")
        return True
    
    def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> ModelResponse:
        """
        生成响应（模拟）
        
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
            return self._generate_non_streaming(user_message, temperature, start_time)
    
    def _generate_non_streaming(
        self,
        user_message: str,
        temperature: float,
        start_time: float
    ) -> ModelResponse:
        """
        非流式生成（模拟）
        
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
        time.sleep(0.1)
        
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
                "note": "这是一个模拟响应，用于测试。请配置真实模型以获取实际响应。",
            }
        )
    
    def _generate_streaming(
        self,
        user_message: str,
        temperature: float
    ) -> Generator[str, None, None]:
        """
        流式生成（模拟）
        
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
            time.sleep(0.01)  # 模拟延迟
    
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
        
        if any(word in user_lower for word in ["你好", "hello", "hi", "嗨"]):
            return "你好！我是 SerpentAI 的模拟助手。这是一个测试响应。请配置真实模型（OpenAI/Anthropic/本地Llama）以获取实际响应。"
        
        elif any(word in user_lower for word in ["帮助", "help", "功能", "能做什么"]):
            return """SerpentAI 是一个功能强大的自托管 AI 智能体框架，支持：

1. 🧠 四层记忆系统（瞬时/短期/长期/归档）
2. 🔧 工具集成层（MCP协议、工具预编译）
3. ⚡ 效率引擎（Token优化、提示词蒸馏）
4. 🌐 多通道网关（Discord/Telegram/飞书）
5. 🎨 图形化工作流编辑器
6. 🔒 五层安全防御
7. 🖥️ 桌面客户端（Tauri）
8. 📱 移动PWA
9. 🎙️ 语音交互（STT/TTS）
10. 📦 Python SDK

目前您看到的是模拟响应。请配置真实模型以获取实际帮助。"""
        
        elif any(word in user_lower for word in ["模型", "model", "llm", "ai"]):
            return """要配置真实模型，请：

1. **OpenAI**: 设置环境变量 OPENAI_API_KEY
2. **Anthropic**: 设置环境变量 ANTHROPIC_API_KEY
3. **本地模型**: 安装 llama-cpp-python 并下载 GGUF 模型文件

配置完成后，重启服务器即可使用真实模型。

当前为模拟模式，响应为预设内容。"""
        
        elif any(word in user_lower for word in ["测试", "test", "ping"]):
            return f"✅ 测试成功！服务器运行正常。\n\n当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n模型: {self.model_name} (模拟)\nTemperature: {temperature}"
        
        else:
            return f"""感谢您的消息：「{user_message}】

这是 SerpentAI 的模拟响应。要获取真实的 AI 响应，请：

1. 配置模型 API 密钥，或
2. 安装本地模型（llama.cpp）

配置方法请参考 README.md。

---
当前模式：模拟（Mock）
模型：{self.model_name}"""
    
    def count_tokens(self, text: str) -> int:
        """
        计算Token数（模拟）
        
        Args:
            text: 输入文本
            
        Returns:
            int: 估算的Token数
        """
        # 简单估算：1个Token ≈ 2个字符
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
            "pricing": {"input": 0.0, "output": 0.0},
            "supports_tools": False,
            "supports_streaming": True,
            "initialized": self.is_initialized,
            "note": "这是一个模拟模型，用于测试。请配置真实模型以获取实际响应。"
        }
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        估算成本（模拟模型为0）
        
        Returns:
            float: 0.0
        """
        return 0.0
