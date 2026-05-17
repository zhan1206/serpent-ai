"""
SerpentAI Python SDK
终极自托管全功能AI智能体框架

pip install serpent-ai-sdk

快速开始:
    from serpent_sdk import SerpentAI
    
    client = SerpentAI("http://localhost:8000")
    
    # 聊天
    response = client.chat("你好，请介绍一下自己")
    print(response.text)
    
    # 使用智能体
    agent = client.agents.create(name="我的助手", model="gpt-4")
    result = agent.run("帮我写一封邮件")
    
    # 工作流
    workflow = client.workflows.execute("data-pipeline", {"input": "data.csv"})
"""

import os
import logging
from typing import Optional

from .client import SerpentAI
from .exceptions import (
    SerpentAIError,
    APIError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ValidationError,
    TimeoutError,
    NetworkError,
)
from .types import (
    ChatMessage,
    ChatResponse,
    ModelInfo,
    ToolInfo,
    WorkflowInfo,
    AgentInfo,
    MemoryStats,
)

__version__ = "0.1.0"

__all__ = [
    # 核心
    "SerpentAI",
    # 异常
    "SerpentAIError",
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "ValidationError",
    "TimeoutError",
    "NetworkError",
    # 类型
    "ChatMessage",
    "ChatResponse",
    "ModelInfo",
    "ToolInfo",
    "WorkflowInfo",
    "AgentInfo",
    "MemoryStats",
]

# SDK 级别日志配置
_log = logging.getLogger("serpent_sdk")
