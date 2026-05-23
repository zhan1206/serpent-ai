"""
SerpentAI 模型抽象层 - Anthropic适配器
支持所有Anthropic Claude模型（Claude 3 系列等）
"""
import json
import anthropic
from typing import List, Dict, Any, Optional, Generator
import logging
import time
from core.config import settings
from models.base_model import BaseModelAdapter, Message, ModelResponse, TokenUsage

logger = logging.getLogger(__name__)

class AnthropicAdapter(BaseModelAdapter):
    """
    Anthropic Claude模型适配器
    支持：Claude 3 Opus/Sonnet/Haiku, Claude 2.1等
    """
    
    # Anthropic模型定价（每1K tokens，2024年5月价格）
    PRICING = {
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "claude-2.1": {"input": 0.008, "output": 0.024},
        "claude-2.0": {"input": 0.008, "output": 0.024},
        "claude-instant-1.2": {"input": 0.0008, "output": 0.0024},
    }
    
    # 模型上下文长度
    CONTEXT_LENGTHS = {
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
        "claude-2.1": 200000,
        "claude-2.0": 100000,
        "claude-instant-1.2": 100000,
    }
    
    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化Anthropic适配器
        
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
        初始化Anthropic客户端
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 获取API密钥
            self.api_key = (
                self.config.get("api_key") or 
                settings.ANTHROPIC_API_KEY
            )
            
            if not self.api_key:
                logger.error("Anthropic API密钥未配置")
                return False
            
            # 获取Base URL（支持自定义端点）
            self.base_url = (
                self.config.get("base_url") or 
                settings.ANTHROPIC_API_BASE
            )
            
            # 创建客户端
            self.client = anthropic.Anthropic(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
            # 测试连接（获取模型列表）
            self.client.models.list(limit=1)
            
            self.is_initialized = True
            logger.info(f"Anthropic适配器初始化成功: {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Anthropic适配器初始化失败: {e}")
            return False
    
    def _convert_messages_to_anthropic_format(
        self, 
        messages: List[Message]
    ) -> tuple[List[Dict], str]:
        """
        将消息列表转换为Anthropic格式
        
        Anthropic API要求：
        - system消息单独传递
        - 用户和助手消息交替出现
        
        Returns:
            tuple: (messages, system_message)
        """
        anthropic_messages = []
        system_message = ""
        
        for msg in messages:
            if msg.role == "system":
                # system消息需要单独提取
                system_message = msg.content
            elif msg.role == "user":
                anthropic_messages.append({
                    "role": "user",
                    "content": msg.content
                })
            elif msg.role == "assistant":
                message_dict = {
                    "role": "assistant",
                    "content": msg.content
                }
                
                # 如果有tool calls，添加到消息中
                if msg.tool_calls:
                    message_dict["content"] = [
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": json.loads(tc["function"]["arguments"])
                        }
                        for tc in msg.tool_calls
                    ]
                
                anthropic_messages.append(message_dict)
            elif msg.role == "tool":
                # 工具响应消息
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content
                        }
                    ]
                })
        
        return anthropic_messages, system_message
    
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
        import json
        
        if not self.is_initialized:
            if not self.initialize():
                raise RuntimeError("Anthropic适配器未初始化")
        
        # 验证消息
        if not self.validate_messages(messages):
            raise ValueError("消息格式无效")
        
        # 转换消息格式
        anthropic_messages, system_message = self._convert_messages_to_anthropic_format(messages)
        
        # 构建请求参数
        params = {
            "model": self.model_name,
            "messages": anthropic_messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
        else:
            # Anthropic要求必须指定max_tokens
            params["max_tokens"] = 4096
        
        if system_message:
            params["system"] = system_message
        
        if tools:
            # 转换工具格式为Anthropic格式
            anthropic_tools = [
                {
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "input_schema": tool["function"]["parameters"]
                }
                for tool in tools
            ]
            params["tools"] = anthropic_tools
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 调用API
            if stream:
                # 流式输出（简化版：收集完整响应）
                response_stream = self.client.messages.create(
                    **params,
                    stream=True
                )
                
                content_parts = []
                for chunk in response_stream:
                    if chunk.type == "content_block_delta":
                        if hasattr(chunk.delta, 'text'):
                            content_parts.append(chunk.delta.text)
                
                content = "".join(content_parts)
                
                # 估算Token
                input_tokens = self.count_tokens(
                    " ".join([msg.content for msg in messages])
                )
                output_tokens = self.count_tokens(content)
                
            else:
                # 非流式输出
                response = self.client.messages.create(
                    **params,
                    stream=False
                )
                
                content = response.content[0].text if response.content else ""
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
            
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
                    "provider": "anthropic",
                    "temperature": temperature,
                    "stop_reason": response.stop_reason if not stream else None,
                }
            )
            
            logger.info(
                f"Anthropic生成成功 | "
                f"模型: {self.model_name} | "
                f"输入: {input_tokens} | "
                f"输出: {output_tokens} | "
                f"延迟: {latency_ms}ms | "
                f"成本: ${model_response.cost:.4f}"
            )
            
            return model_response
            
        except Exception as e:
            logger.error(f"Anthropic生成失败: {e}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的Token数
        使用Anthropic官方方法（如果有客户端）
        
        Args:
            text: 输入文本
            
        Returns:
            int: Token数量
        """
        try:
            # 使用Anthropic官方Token计数API
            if self.client:
                response = self.client.messages.count_tokens(
                    model=self.model_name,
                    messages=[{"role": "user", "content": text}]
                )
                return response.input_tokens
        except:
            pass
        
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
        context_length = 200000  # 默认200K
        for key, length in self.CONTEXT_LENGTHS.items():
            if key in model_key:
                context_length = length
                break
        
        return {
            "name": self.model_name,
            "provider": "anthropic",
            "context_length": context_length,
            "pricing": pricing,
            "supports_tools": True,
            "supports_streaming": True,
            "supports_vision": "claude-3" in model_key,  # Claude 3支持视觉
            "initialized": self.is_initialized,
        }
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        估算Anthropic API成本
        
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
