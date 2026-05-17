"""
SerpentAI Python SDK - 主客户端
"""

import os
import logging
import httpx
from typing import Optional, List, Dict, Any, Union
from urllib.parse import urljoin

from .types import (
    ChatMessage, ChatResponse, ModelInfo, ToolInfo,
    WorkflowInfo, AgentInfo, MemoryStats, HealthStatus,
    VoiceSession, PluginInfo, SkillInfo, ExecutionResult,
    TokenUsage,
)
from .exceptions import (
    SerpentAIError, APIError, AuthenticationError,
    RateLimitError, NotFoundError, ValidationError,
    TimeoutError, NetworkError, InitializationError,
)
from . import agent as agent_module
from . import workflow as workflow_module
from . import voice as voice_module
from . import plugin as plugin_module
from . import skill as skill_module
from . import memory as memory_module


_logger = logging.getLogger(__name__)


class SerpentAI:
    """
    SerpentAI Python SDK 主客户端
    
    快速开始:
        from serpent_sdk import SerpentAI
        
        client = SerpentAI("http://localhost:8000")
        
        # 聊天
        response = client.chat("你好")
        print(response.text)
        
        # 使用智能体
        result = client.agents.run("my-agent", "帮我写代码")
        
        # 工作流
        result = client.workflows.execute("data-pipeline", {"input": "data.csv"})
    
    支持的模型:
        - OpenAI: gpt-4, gpt-3.5-turbo
        - Anthropic: claude-3-opus, claude-3-sonnet
        - 本地: llama-3-8b, mistral-7b, qwen-7b
    """
    
    DEFAULT_TIMEOUT = 120  # 默认超时120秒
    MAX_RETRIES = 3       # 最大重试次数
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        verify_ssl: bool = True,
        **httpx_kwargs
    ):
        """
        初始化 SerpentAI 客户端
        
        Args:
            base_url: SerpentAI 服务地址
            api_key: API密钥（可选，用于认证）
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            verify_ssl: 是否验证SSL证书
            **httpx_kwargs: 传递给 httpx.Client 的其他参数
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("SERPENT_API_KEY", "")
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        
        # HTTP客户端
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            verify=verify_ssl,
            **httpx_kwargs
        )
        
        # 初始化子模块
        self.agents = agent_module.AgentManager(self)
        self.workflows = workflow_module.WorkflowManager(self)
        self.voice = voice_module.VoiceManager(self)
        self.plugins = plugin_module.PluginManager(self)
        self.skills = skill_module.SkillManager(self)
        self.memory = memory_module.MemoryManager(self)
        
        _logger.info(f"SerpentAI SDK initialized: {base_url}")
    
    # ==================== 底层请求方法 ====================
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"serpent-sdk/0.1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        data: Optional[Dict] = None,
        stream: bool = False,
    ) -> Union[Dict, httpx.Response]:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE, PATCH)
            path: API路径
            params: URL参数
            json: JSON请求体
            data: 表单数据
            stream: 是否流式响应
        
        Returns:
            响应JSON数据或httpx.Response（流式）
        
        Raises:
            APIError: 服务器返回错误
            NetworkError: 网络错误
            TimeoutError: 超时
            AuthenticationError: 认证失败
        """
        url = path
        headers = self._get_headers()
        
        # 如果使用表单数据（文件上传等），不设置Content-Type
        if data is not None:
            headers.pop("Content-Type", None)
        
        try:
            response = self._client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=headers,
                timeout=self.timeout,
            )
            
            if stream:
                return response
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise AuthenticationError("认证失败，请检查API密钥", response=response.json())
            elif response.status_code == 403:
                raise AuthenticationError("权限不足", response=response.json())
            elif response.status_code == 404:
                raise NotFoundError(f"资源不存在: {path}", response=response.json())
            elif response.status_code == 422:
                raise ValidationError("参数验证失败", response=response.json())
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(
                    "请求频率超限",
                    retry_after=int(retry_after) if retry_after else None
                )
            else:
                try:
                    error_data = response.json()
                except Exception:
                    error_data = {"message": response.text}
                raise APIError(
                    error_data.get("message", "API请求失败"),
                    status_code=response.status_code,
                    response=error_data
                )
                
        except httpx.TimeoutException:
            raise TimeoutError(f"请求超时 ({self.timeout}s)", timeout_seconds=self.timeout)
        except httpx.ConnectError as e:
            raise NetworkError(f"连接失败: {e}")
        except httpx.HTTPError as e:
            raise NetworkError(f"HTTP错误: {e}")
    
    def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET请求"""
        return self._request("GET", path, params=params)
    
    def post(self, path: str, json: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """POST请求"""
        return self._request("POST", path, json=json, data=data)
    
    def put(self, path: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        """PUT请求"""
        return self._request("PUT", path, json=json)
    
    def delete(self, path: str) -> Dict[str, Any]:
        """DELETE请求"""
        return self._request("DELETE", path)
    
    def patch(self, path: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        """PATCH请求"""
        return self._request("PATCH", path, json=json)
    
    # ==================== 核心API ====================
    
    def chat(
        self,
        message: str,
        model: str = "gpt-4",
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
    ) -> ChatResponse:
        """
        发送聊天消息
        
        Args:
            message: 用户消息
            model: 模型名称 (gpt-4, gpt-3.5-turbo, llama-3-8b, etc.)
            session_id: 会话ID（用于记忆系统）
            system_prompt: 系统提示词
            temperature: 温度参数 (0.0-2.0)
            max_tokens: 最大输出Token数
            tools: 工具列表
        
        Returns:
            ChatResponse: 聊天响应
        
        Example:
            client = SerpentAI()
            response = client.chat("你好", model="gpt-4")
            print(response.text)
        """
        messages = [{"role": "user", "content": message}]
        
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
        if session_id:
            payload["session_id"] = session_id
        
        result = self.post("/api/chat", json=payload)
        
        return ChatResponse.from_dict(result)
    
    def chat_stream(
        self,
        message: str,
        model: str = "gpt-4",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ):
        """
        流式聊天（生成器）
        
        Args:
            message: 用户消息
            model: 模型名称
            system_prompt: 系统提示词
            temperature: 温度参数
        
        Yields:
            str: 增量文本片段
        
        Example:
            for text in client.chat_stream("给我讲个故事"):
                print(text, end="", flush=True)
        """
        messages = [{"role": "user", "content": message}]
        
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "stream": True,
        }
        
        with self._request("POST", "/api/chat", json=payload, stream=True) as response:
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    import json as json_module
                    try:
                        chunk = json_module.loads(data)
                        if "content" in chunk:
                            yield chunk["content"]
                    except Exception:
                        pass
    
    def list_models(self) -> List[ModelInfo]:
        """列出所有可用的模型"""
        result = self.get("/api/models")
        return [ModelInfo.from_dict(m) for m in result.get("models", [])]
    
    def list_tools(
        self,
        category: Optional[str] = None,
        tool_type: Optional[str] = None,
    ) -> List[ToolInfo]:
        """
        列出所有工具
        
        Args:
            category: 按分类过滤
            tool_type: 按类型过滤 (mcp/builtin/custom)
        
        Returns:
            List[ToolInfo]: 工具列表
        """
        params = {}
        if category:
            params["category"] = category
        if tool_type:
            params["tool_type"] = tool_type
        
        result = self.get("/api/tools", params=params)
        return [ToolInfo.from_dict(t) for t in result.get("tools", [])]
    
    def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
        
        Returns:
            工具执行结果
        """
        payload = {
            "tool_name": tool_name,
            "arguments": arguments or {},
        }
        
        result = self.post("/api/tools/call", json=payload)
        return result.get("result")
    
    def get_optimized_tools_prompt(self) -> Dict[str, str]:
        """
        获取Token优化的工具提示词
        使用预编译+蒸馏技术，减少80% Token消耗
        
        Returns:
            包含 precompiled_prompt 和 distilled_prompt 的字典
        """
        result = self.get("/api/tools/optimized-prompt")
        return {
            "precompiled": result.get("precompiled_prompt", ""),
            "distilled": result.get("distilled_prompt", ""),
        }
    
    # ==================== 记忆系统 ====================
    
    def add_memory(
        self,
        content: str,
        session_id: str,
        role: str = "user",
    ) -> bool:
        """
        添加内容到记忆系统
        
        Args:
            content: 内容
            session_id: 会话ID
            role: 角色 (user/assistant/system)
        
        Returns:
            是否成功
        """
        payload = {"content": content, "role": role}
        result = self.post(f"/api/memory/add?session_id={session_id}", json=payload)
        return result.get("status") == "success"
    
    def recall_memory(
        self,
        query: str,
        session_id: str,
        limit: int = 10,
        include_instant: bool = True,
        include_short_term: bool = True,
        include_long_term: bool = True,
        include_archive: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        从记忆系统召回相关内容
        
        Args:
            query: 查询内容
            session_id: 会话ID
            limit: 返回数量限制
            include_*: 是否包含各层记忆
        
        Returns:
            召回的记忆列表
        """
        payload = {
            "query": query,
            "limit": limit,
            "include_instant": include_instant,
            "include_short_term": include_short_term,
            "include_long_term": include_long_term,
            "include_archive": include_archive,
        }
        
        result = self.post(f"/api/memory/recall?session_id={session_id}", json=payload)
        return result.get("results", [])
    
    def clear_memory(self, session_id: Optional[str] = None) -> bool:
        """
        清空记忆
        
        Args:
            session_id: 会话ID（不提供则清空所有）
        
        Returns:
            是否成功
        """
        if session_id:
            result = self.delete(f"/api/memory/clear?session_id={session_id}")
        else:
            result = self.delete("/api/memory/clear")
        return result.get("status") == "success"
    
    def get_memory_stats(self) -> MemoryStats:
        """获取记忆系统统计"""
        result = self.get("/api/memory/stats")
        return MemoryStats.from_dict(result)
    
    # ==================== 系统状态 ====================
    
    def health(self) -> HealthStatus:
        """获取系统健康状态"""
        result = self.get("/health")
        return HealthStatus.from_dict(result)
    
    def get_version(self) -> str:
        """获取服务器版本"""
        result = self.get("/")
        return result.get("version", "unknown")
    
    # ==================== 上下文管理器 ====================
    
    def __enter__(self) -> "SerpentAI":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """关闭客户端连接"""
        self._client.close()
        _logger.info("SerpentAI SDK client closed")


class AsyncSerpentAI:
    """
    SerpentAI Python SDK 异步客户端
    
    Example:
        import asyncio
        from serpent_sdk import AsyncSerpentAI
        
        async def main():
            async with AsyncSerpentAI() as client:
                response = await client.chat("你好")
                print(response.text)
        
        asyncio.run(main())
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: int = 120,
    ):
        import httpx
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("SERPENT_API_KEY", "")
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
        )
        
        self.agents = agent_module.AsyncAgentManager(self)
        self.workflows = workflow_module.AsyncWorkflowManager(self)
        self.voice = voice_module.AsyncVoiceManager(self)
    
    async def chat(self, message: str, **kwargs) -> ChatResponse:
        import json
        messages = [{"role": "user", "content": message}]
        payload = {"messages": messages, **kwargs}
        
        response = await self._client.post("/api/chat", json=payload)
        result = response.json()
        return ChatResponse.from_dict(result)
    
    async def get(self, path: str) -> Dict[str, Any]:
        response = await self._client.get(path)
        return response.json()
    
    async def post(self, path: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        response = await self._client.post(path, json=json)
        return response.json()
    
    async def __aenter__(self) -> "AsyncSerpentAI":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()
    
    async def aclose(self):
        await self._client.aclose()
