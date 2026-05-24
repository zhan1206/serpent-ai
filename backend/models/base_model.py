"""
SerpentAI 模型抽象层 - 基础接口定义
所有模型适配器的基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Generator, Union
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

class Message(BaseModel):
    """统一消息格式"""
    role: str = Field(..., description="消息角色: system, user, assistant, tool")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(None, description="工具调用名称（可选）")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="工具调用信息")
    tool_call_id: Optional[str] = Field(None, description="工具调用ID")

class ModelResponse(BaseModel):
    """统一模型响应格式"""
    content: str = Field(..., description="生成的文本")
    model: str = Field(..., description="使用的模型名称")
    input_tokens: int = Field(0, description="输入Token数")
    output_tokens: int = Field(0, description="输出Token数")
    total_tokens: int = Field(0, description="总Token数")
    cost: float = Field(0.0, description="估算成本（美元）")
    latency_ms: int = Field(0, description="延迟（毫秒）")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")

class TokenUsage(BaseModel):
    """Token使用统计"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens
        }

class BaseModelAdapter(ABC):
    """
    模型适配器基类（抽象类）
    所有具体的模型适配器必须继承此类并实现抽象方法
    """
    
    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化模型适配器
        
        Args:
            model_name: 模型名称（如 gpt-4o, claude-3-opus）
            config: 配置字典（API密钥、base URL等）
        """
        self.model_name = model_name
        self.config = config or {}
        self.is_initialized = False
        logger.info(f"模型适配器已创建: {model_name}")
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化模型（验证连接、加载模型等）
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> Union[ModelResponse, Generator[ModelResponse, None, None]]:
        """
        生成响应（核心方法）
        
        Args:
            messages: 对话历史
            temperature: 温度参数（创造性）
            max_tokens: 最大生成Token数
            tools: 可用工具列表（Function Calling）
            stream: 是否流式输出
            
        Returns:
            ModelResponse 或 Generator[ModelResponse]
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        计算文本的Token数
        
        Args:
            text: 输入文本
            
        Returns:
            int: Token数量
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            Dict: 模型信息（名称、上下文长度、价格等）
        """
        pass
    
    def validate_messages(self, messages: List[Message]) -> bool:
        """
        验证消息格式
        
        Args:
            messages: 消息列表
            
        Returns:
            bool: 是否有效
        """
        if not messages:
            logger.warning("消息列表为空")
            return False
        
        valid_roles = {"system", "user", "assistant", "tool"}
        
        for i, msg in enumerate(messages):
            if msg.role not in valid_roles:
                logger.error(f"消息 {i} 角色无效: {msg.role}")
                return False
            
            if not msg.content and msg.role != "tool":
                logger.warning(f"消息 {i} 内容为空")
        
        logger.debug(f"消息验证通过: {len(messages)} 条消息")
        return True
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        估算成本（美元）
        子类可以重写此方法以提供准确的定价
        
        Args:
            input_tokens: 输入Token数
            output_tokens: 输出Token数
            
        Returns:
            float: 估算成本（美元）
        """
        # 默认价格（每1K tokens）
        default_pricing = {
            "input": 0.01,
            "output": 0.03
        }
        
        input_cost = (input_tokens / 1000) * default_pricing["input"]
        output_cost = (output_tokens / 1000) * default_pricing["output"]
        total_cost = input_cost + output_cost
        
        logger.debug(f"成本估算: 输入${input_cost:.4f} + 输出${output_cost:.4f} = ${total_cost:.4f}")
        return total_cost
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_name}, initialized={self.is_initialized})"

# ==================== 模型路由器的辅助函数 ====================

def create_adapter(model_name: str, config: Optional[Dict[str, Any]] = None) -> BaseModelAdapter:
    """
    根据模型名称创建对应的适配器
    
    Args:
        model_name: 模型名称
        config: 配置字典
        
    Returns:
        BaseModelAdapter: 模型适配器实例
        
    Raises:
        ValueError: 不支持的模型
    """
    from backend.models.openai_adapter import OpenAIAdapter
    from backend.models.anthropic_adapter import AnthropicAdapter
    from backend.models.llama_adapter import LlamaAdapter
    
    model_name_lower = model_name.lower()
    
    # OpenAI模型
    if any(name in model_name_lower for name in ["gpt-4", "gpt-3.5", "o1"]):
        return OpenAIAdapter(model_name, config)
    
    # Anthropic模型
    elif any(name in model_name_lower for name in ["claude"]):
        return AnthropicAdapter(model_name, config)
    
    # 本地Llama模型
    elif any(name in model_name_lower for name in ["llama", "mistral", "qwen", "gemma"]):
        return LlamaAdapter(model_name, config)
    
    else:
        logger.error(f"不支持的模型: {model_name}")
        raise ValueError(f"不支持的模型: {model_name}")

def list_supported_models() -> List[str]:
    """
    列出所有支持的模型
    
    Returns:
        List[str]: 支持的模型列表
    """
    return [
        # OpenAI
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        # Anthropic
        "claude-3-opus",
        "claude-3-sonnet",
        "claude-3-haiku",
        "claude-2.1",
        # 本地模型（需要llama.cpp）
        "llama-3-8b",
        "llama-3-70b",
        "mistral-7b",
        "qwen-7b",
        "gemma-7b",
    ]

# ==================== Token计算辅助函数 ====================

def estimate_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    估算Token数（简单方法，不使用tiktoken）
    中文约1.5-2字符/token，英文约4字符/token
    
    Args:
        text: 输入文本
        model: 模型名称（影响Token计算方式）
        
    Returns:
        int: 估算的Token数
    """
    # 简单估算：平均1.3字符/Token（中英文混合）
    estimated = len(text) // 1.3
    logger.debug(f"Token估算: {len(text)} 字符 ≈ {estimated} tokens")
    return estimated

def truncate_messages(
    messages: List[Message],
    max_tokens: int,
    reserve_tokens: int = 500
) -> List[Message]:
    """
    截断消息以符合Token限制
    
    Args:
        messages: 消息列表
        max_tokens: 最大Token数
        reserve_tokens: 为响应预留的Token数
        
    Returns:
        List[Message]: 截断后的消息列表
    """
    if not messages:
        return messages
    
    # 从最新的消息开始保留
    truncated = []
    total_tokens = 0
    available_tokens = max_tokens - reserve_tokens
    
    for msg in reversed(messages):
        msg_tokens = estimate_tokens(msg.content)
        
        if total_tokens + msg_tokens > available_tokens:
            logger.warning(f"消息截断: 已达到Token限制 ({available_tokens})")
            break
        
        truncated.insert(0, msg)
        total_tokens += msg_tokens
    
    logger.info(f"消息截断完成: {len(messages)} -> {len(truncated)} 条")
    return truncated
