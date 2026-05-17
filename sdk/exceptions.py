"""
SerpentAI SDK 异常定义
"""

from typing import Optional, Dict, Any


class SerpentAIError(Exception):
    """SerpentAI SDK 基础异常"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class APIError(SerpentAIError):
    """API错误（服务器返回错误状态码）"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
    
    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class AuthenticationError(SerpentAIError):
    """认证失败（API Key无效或过期）"""
    pass


class RateLimitError(SerpentAIError):
    """请求频率超限"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after
    
    def __str__(self) -> str:
        if self.retry_after:
            return f"{self.message} (retry after {self.retry_after}s)"
        return self.message


class NotFoundError(SerpentAIError):
    """资源不存在"""
    pass


class ValidationError(SerpentAIError):
    """请求参数验证失败"""
    pass


class TimeoutError(SerpentAIError):
    """请求超时"""
    
    def __init__(self, message: str = "Request timed out", timeout_seconds: Optional[int] = None):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds
    
    def __str__(self) -> str:
        if self.timeout_seconds:
            return f"{self.message} ({self.timeout_seconds}s)"
        return self.message


class NetworkError(SerpentAIError):
    """网络错误（连接失败、DNS错误等）"""
    pass


class InitializationError(SerpentAIError):
    """SDK初始化失败"""
    pass


class ModelNotSupportedError(SerpentAIError):
    """不支持的模型"""
    
    def __init__(self, model_name: str, supported_models: Optional[list] = None):
        message = f"Model '{model_name}' is not supported"
        super().__init__(message)
        self.model_name = model_name
        self.supported_models = supported_models or []
    
    def __str__(self) -> str:
        if self.supported_models:
            return f"{self.message}. Supported models: {', '.join(self.supported_models)}"
        return self.message


class ToolNotFoundError(SerpentAIError):
    """工具不存在"""
    
    def __init__(self, tool_name: str):
        super().__init__(f"Tool '{tool_name}' not found")
        self.tool_name = tool_name


class WorkflowError(SerpentAIError):
    """工作流执行错误"""
    
    def __init__(self, message: str, workflow_id: Optional[str] = None, node_id: Optional[str] = None):
        super().__init__(message)
        self.workflow_id = workflow_id
        self.node_id = node_id
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.workflow_id:
            parts.append(f"workflow_id={self.workflow_id}")
        if self.node_id:
            parts.append(f"node_id={self.node_id}")
        return " | ".join(parts)
