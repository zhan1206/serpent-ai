"""
SerpentAI SDK 类型定义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            name=data.get("name"),
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id"),
        )
    
    @classmethod
    def user(cls, content: str) -> "ChatMessage":
        return cls(role="user", content=content)
    
    @classmethod
    def assistant(cls, content: str) -> "ChatMessage":
        return cls(role="assistant", content=content)
    
    @classmethod
    def system(cls, content: str) -> "ChatMessage":
        return cls(role="system", content=content)


@dataclass
class TokenUsage:
    """Token使用量"""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenUsage":
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
        )


@dataclass
class ChatResponse:
    """聊天响应"""
    text: str
    model: str
    usage: TokenUsage
    cost: float
    latency_ms: int
    context_used: int = 0
    finish_reason: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatResponse":
        return cls(
            text=data.get("text", data.get("response", "")),
            model=data.get("model", "unknown"),
            usage=TokenUsage.from_dict(data.get("usage", {})),
            cost=data.get("cost", 0.0),
            latency_ms=data.get("latency_ms", 0),
            context_used=data.get("context_used", 0),
            finish_reason=data.get("finish_reason"),
        )


@dataclass 
class ModelInfo:
    """模型信息"""
    id: str
    name: str
    provider: str
    context_length: int
    supports_functions: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelInfo":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            provider=data.get("provider", "openai"),
            context_length=data.get("context_length", 8192),
            supports_functions=data.get("supports_functions", False),
        )


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    description: str
    category: str
    parameters: Dict[str, Any]
    tool_type: str = "builtin"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolInfo":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            parameters=data.get("parameters", {}),
            tool_type=data.get("type", "builtin"),
        )


@dataclass
class AgentInfo:
    """智能体信息"""
    id: str
    name: str
    model: str
    status: str
    created_at: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentInfo":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            model=data.get("model", "gpt-4"),
            status=data.get("status", "idle"),
            created_at=data.get("created_at"),
        )


@dataclass
class WorkflowInfo:
    """工作流信息"""
    id: str
    name: str
    description: str
    node_count: int
    status: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowInfo":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            node_count=data.get("node_count", 0),
            status=data.get("status", "draft"),
        )


@dataclass
class MemoryStats:
    """记忆系统统计"""
    instant_count: int
    short_term_count: int
    long_term_count: int
    archive_count: int
    
    @property
    def total(self) -> int:
        return self.instant_count + self.short_term_count + self.long_term_count + self.archive_count
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryStats":
        return cls(
            instant_count=data.get("instant_count", 0),
            short_term_count=data.get("short_term_count", 0),
            long_term_count=data.get("long_term_count", 0),
            archive_count=data.get("archive_count", 0),
        )


@dataclass
class ExecutionResult:
    """工作流执行结果"""
    execution_id: str
    status: str
    results: Dict[str, Any]
    duration_ms: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionResult":
        return cls(
            execution_id=data.get("execution_id", ""),
            status=data.get("status", "unknown"),
            results=data.get("results", {}),
            duration_ms=data.get("duration_ms", 0),
        )


@dataclass
class VoiceSession:
    """语音会话"""
    id: str
    language: str
    status: str
    created_at: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoiceSession":
        return cls(
            id=data.get("id", ""),
            language=data.get("language", "zh-CN"),
            status=data.get("status", "idle"),
            created_at=data.get("created_at"),
        )


@dataclass
class PluginInfo:
    """插件信息"""
    id: str
    name: str
    version: str
    author: str
    description: str
    enabled: bool = True
    dependencies: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginInfo":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            dependencies=data.get("dependencies", []),
        )


@dataclass
class SkillInfo:
    """技能信息"""
    id: str
    name: str
    description: str
    category: str
    rating: float = 0.0
    install_count: int = 0
    author: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillInfo":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            rating=data.get("rating", 0.0),
            install_count=data.get("install_count", 0),
            author=data.get("author", ""),
        )


@dataclass
class HealthStatus:
    """健康状态"""
    status: str
    database: Dict[str, bool]
    memory: Dict[str, Any]
    version: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HealthStatus":
        return cls(
            status=data.get("status", "unknown"),
            database=data.get("database", {}),
            memory=data.get("memory", {}),
            version=data.get("version", ""),
        )
