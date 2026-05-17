"""
SerpentAI SDK - 智能体管理模块
"""

from typing import Optional, Dict, Any, List, TYPE_CHECKING

from .types import AgentInfo, ChatResponse
if TYPE_CHECKING:
    from .client import SerpentAI


class AgentManager:
    """智能体管理器"""
    
    def __init__(self, client: "SerpentAI"):
        self._client = client
    
    def create(
        self,
        name: str,
        model: str = "gpt-4",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AgentInfo:
        """
        创建智能体
        
        Args:
            name: 智能体名称
            model: 模型 (gpt-4, gpt-3.5-turbo, llama-3-8b, etc.)
            system_prompt: 系统提示词
            temperature: 温度
            max_tokens: 最大Token数
        
        Returns:
            AgentInfo: 智能体信息
        """
        payload = {
            "name": name,
            "model": model,
            "temperature": temperature,
        }
        if system_prompt:
            payload["system_prompt"] = system_prompt
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        result = self._client.post("/api/agent/create", json=payload)
        return AgentInfo.from_dict(result)
    
    def get(self, agent_id: str) -> AgentInfo:
        """获取智能体信息"""
        result = self._client.get(f"/api/agent/{agent_id}")
        return AgentInfo.from_dict(result)
    
    def list(self) -> List[AgentInfo]:
        """列出所有智能体"""
        result = self._client.get("/api/agent/list")
        return [AgentInfo.from_dict(a) for a in result.get("agents", [])]
    
    def run(
        self,
        agent_id: str,
        message: str,
        session_id: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
    ) -> ChatResponse:
        """
        运行智能体
        
        Args:
            agent_id: 智能体ID
            message: 输入消息
            session_id: 会话ID
            tools: 可用工具列表
        
        Returns:
            ChatResponse: 智能体响应
        """
        payload = {
            "message": message,
        }
        if session_id:
            payload["session_id"] = session_id
        if tools:
            payload["tools"] = tools
        
        result = self._client.post(f"/api/agent/{agent_id}/chat", json=payload)
        return ChatResponse.from_dict(result)
    
    def run_task(
        self,
        agent_id: str,
        task: str,
        priority: int = 5,
        background: bool = False,
    ) -> Dict[str, Any]:
        """
        创建任务
        
        Args:
            agent_id: 智能体ID
            task: 任务描述
            priority: 优先级 (1-10)
            background: 是否后台执行
        
        Returns:
            任务信息
        """
        payload = {
            "task": task,
            "priority": priority,
            "background": background,
        }
        
        result = self._client.post(f"/api/agent/{agent_id}/task", json=payload)
        return result
    
    def evolve(
        self,
        agent_id: str,
        evolution_type: str = "optimize",
        target: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        触发智能体自进化
        
        Args:
            agent_id: 智能体ID
            evolution_type: 进化类型 (fix/optimize/generate/distill)
            target: 进化目标（技能名或错误描述）
        
        Returns:
            进化结果
        """
        payload = {
            "evolution_type": evolution_type,
        }
        if target:
            payload["target"] = target
        
        result = self._client.post(f"/api/agent/{agent_id}/evolve", json=payload)
        return result
    
    def delete(self, agent_id: str) -> bool:
        """删除智能体"""
        result = self._client.delete(f"/api/agent/{agent_id}")
        return result.get("deleted", False)
    
    def get_stats(self, agent_id: str) -> Dict[str, Any]:
        """获取智能体统计"""
        return self._client.get(f"/api/agent/{agent_id}/stats")


class AsyncAgentManager:
    """异步智能体管理器"""
    
    def __init__(self, client):
        self._client = client
    
    async def create(self, name: str, **kwargs) -> AgentInfo:
        result = await self._client.post("/api/agent/create", json={"name": name, **kwargs})
        return AgentInfo.from_dict(result)
    
    async def run(self, agent_id: str, message: str, **kwargs) -> ChatResponse:
        result = await self._client.post(f"/api/agent/{agent_id}/chat", json={"message": message, **kwargs})
        return ChatResponse.from_dict(result)
