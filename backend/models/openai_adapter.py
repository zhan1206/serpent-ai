"""
SerpentAI 模型抽象层 - OpenAI适配器
支持所有OpenAI API兼容的模型（GPT-4o, GPT-3.5-turbo等）
"""
try:
    import openai
except ImportError:
    openai = None
from typing import List, Dict, Any, Optional, Generator
import logging
import time
from backend.core.config import settings
from backend.models.base_model import BaseModelAdapter, Message, ModelResponse, TokenUsage

logger = logging.getLogger(__name__)

class OpenAIAdapter(BaseModelAdapter):
    """
    OpenAI模型适配器
    支持：GPT-4o, GPT-4-turbo, GPT-3.5-turbo等
    """
    
    # OpenAI模型定价（每1K tokens，2024年5月价格）
    PRICING = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "o1-preview": {"input": 0.015, "output": 0.06},
        "o1-mini": {"input": 0.0003, "output": 0.0012},
    }
    
    # 模型上下文长度
    CONTEXT_LENGTHS = {
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-4-turbo": 128000,
        "gpt-4": 8192,
        "gpt-3.5-turbo": 16385,
        "o1-preview": 128000,
        "o1-mini": 128000,
    }
    
    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化OpenAI适配器
        
        Args:
            model_name: 模型名称
            config: 配置字典（api_key, base_url等）
        """
        super().__init__(model_name, config)
        self.client = None
        self.api_key = None
        self.base_url = None
    
    def initialize(self) -> bool:
        """
        初始化OpenAI客户端
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 获取API密钥
            self.api_key = (
                self.config.get("api_key") or 
                settings.OPENAI_API_KEY or 
                openai.api_key
            )
            
            if not self.api_key:
                logger.error("OpenAI API密钥未配置")
                return False
            
            # 获取Base URL（支持自定义端点）
            self.base_url = (
                self.config.get("base_url") or 
                settings.OPENAI_API_BASE
            )
            
            # 创建客户端
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
            # 测试连接
            self.client.models.list(limit=1)
            
            self.is_initialized = True
            logger.info(f"OpenAI适配器初始化成功: {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"OpenAI适配器初始化失败: {e}")
            return False
    
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
            tools: 可用工具列表
            stream: 是否流式输出（当前返回完整响应）
            
        Returns:
            ModelResponse: 模型响应
        """
        if not self.is_initialized:
            if not self.initialize():
                raise RuntimeError("OpenAI适配器未初始化")
        
        # 验证消息
        if not self.validate_messages(messages):
            raise ValueError("消息格式无效")
        
        # 转换消息格式
        openai_messages = [
            {
                "role": msg.role,
                "content": msg.content,
                **({"name": msg.name} if msg.name else {}),
                **({"tool_calls": msg.tool_calls} if msg.tool_calls else {}),
                **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {})
            }
            for msg in messages
        ]
        
        # 构建请求参数
        params = {
            "model": self.model_name,
            "messages": openai_messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
        
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 调用API
            if stream:
                # 流式输出（简化版：收集完整响应）
                response_stream = self.client.chat.completions.create(
                    **params,
                    stream=True
                )
                
                content_parts = []
                for chunk in response_stream:
                    if chunk.choices[0].delta.content:
                        content_parts.append(chunk.choices[0].delta.content)
                
                content = "".join(content_parts)
                
                # 估算Token（流式无法准确获取）
                input_tokens = self.count_tokens(
                    " ".join([msg.content for msg in messages])
                )
                output_tokens = self.count_tokens(content)
                
            else:
                # 非流式输出
                response = self.client.chat.completions.create(
                    **params,
                    stream=False
                )
                
                content = response.choices[0].message.content or ""
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
            
            # 计算延迟
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 构建响应
            model_response = ModelResponse(
                content=content,
                model=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                cost=self.estimate_cost(input_tokens, output_tokens),
                latency_ms=latency_ms,
                metadata={
                    "provider": "openai",
                    "temperature": temperature,
                }
            )
            
            logger.info(
                f"OpenAI生成成功 | "
                f"模型: {self.model_name} | "
                f"输入: {input_tokens} | "
                f"输出: {output_tokens} | "
                f"延迟: {latency_ms}ms | "
                f"成本: ${model_response.cost:.4f}"
            )
            
            return model_response
            
        except Exception as e:
            logger.error(f"OpenAI生成失败: {e}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的Token数
        使用简单估算（实际应使用tiktoken库）
        
        Args:
            text: 输入文本
            
        Returns:
            int: Token数量
        """
        # 简单估算：1个Token ≈ 1.3个字符（中英文混合）
        return len(text) // 1
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            Dict: 模型信息
        """
        model_key = self.model_name.lower()
        
        # 查找匹配的定价
        pricing = {"input": 0.01, "output": 0.03}  # 默认价格
        for key, price in self.PRICING.items():
            if key in model_key:
                pricing = price
                break
        
        # 查找上下文长度
        context_length = 8192  # 默认
        for key, length in self.CONTEXT_LENGTHS.items():
            if key in model_key:
                context_length = length
                break
        
        return {
            "name": self.model_name,
            "provider": "openai",
            "context_length": context_length,
            "pricing": pricing,
            "supports_tools": True,
            "supports_streaming": True,
            "initialized": self.is_initialized,
        }
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        估算OpenAI API成本
        
        Args:
            input_tokens: 输入Token数
            output_tokens: 输出Token数
            
        Returns:
            float: 估算成本（美元）
        """
        model_key = self.model_name.lower()
        
        # 查找匹配的定价
        pricing = {"input": 0.01, "output": 0.03}  # 默认价格
        for key, price in self.PRICING.items():
            if key in model_key:
                pricing = price
                break
        
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        logger.debug(
            f"成本估算 [{self.model_name}] | "
            f"输入: ${input_cost:.4f} | "
            f"输出: ${output_cost:.4f} | "
            f"总计: ${total_cost:.4f}"
        )
        
        return total_cost
