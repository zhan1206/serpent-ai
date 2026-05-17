"""
SerpentAI SDK - 工作流管理模块
"""

from typing import Optional, Dict, Any, List, TYPE_CHECKING

from .types import WorkflowInfo, ExecutionResult
if TYPE_CHECKING:
    from .client import SerpentAI


class WorkflowManager:
    """工作流管理器"""
    
    def __init__(self, client: "SerpentAI"):
        self._client = client
    
    def create(
        self,
        name: str,
        description: str = "",
        nodes: Optional[List[Dict]] = None,
        edges: Optional[List[Dict]] = None,
    ) -> WorkflowInfo:
        """
        创建工作流
        
        Args:
            name: 工作流名称
            description: 工作流描述
            nodes: 节点列表
            edges: 边列表
        
        Returns:
            WorkflowInfo: 工作流信息
        """
        payload = {
            "name": name,
            "description": description,
            "nodes": nodes or [],
            "edges": edges or [],
        }
        
        result = self._client.post("/api/workflow", json=payload)
        return WorkflowInfo.from_dict(result)
    
    def get(self, workflow_id: str) -> WorkflowInfo:
        """获取工作流信息"""
        result = self._client.get(f"/api/workflow/{workflow_id}")
        return WorkflowInfo.from_dict(result)
    
    def list(self) -> List[WorkflowInfo]:
        """列出所有工作流"""
        result = self._client.get("/api/workflow")
        return [WorkflowInfo.from_dict(w) for w in result.get("workflows", [])]
    
    def update(self, workflow_id: str, **updates) -> WorkflowInfo:
        """更新工作流"""
        result = self._client.put(f"/api/workflow/{workflow_id}", json=updates)
        return WorkflowInfo.from_dict(result)
    
    def execute(
        self,
        workflow_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        wait: bool = True,
    ) -> ExecutionResult:
        """
        执行工作流
        
        Args:
            workflow_id: 工作流ID
            input_data: 输入数据
            wait: 是否等待完成
        
        Returns:
            ExecutionResult: 执行结果
        """
        payload = {
            "workflow_id": workflow_id,
            "input_data": input_data or {},
            "wait": wait,
        }
        
        result = self._client.post("/api/workflow/execute", json=payload)
        return ExecutionResult.from_dict(result)
    
    def execute_async(self, workflow_id: str, input_data: Optional[Dict] = None) -> str:
        """
        异步执行工作流（不等待结果）
        
        Returns:
            execution_id: 执行ID
        """
        payload = {
            "workflow_id": workflow_id,
            "input_data": input_data or {},
        }
        
        result = self._client.post("/api/workflow/execute-async", json=payload)
        return result.get("execution_id", "")
    
    def get_execution(self, execution_id: str) -> ExecutionResult:
        """获取执行结果"""
        result = self._client.get(f"/api/workflow/execution/{execution_id}")
        return ExecutionResult.from_dict(result)
    
    def validate(self, workflow_id: str) -> Dict[str, Any]:
        """验证工作流"""
        result = self._client.post(f"/api/workflow/{workflow_id}/validate")
        return result
    
    def list_executions(self, workflow_id: str) -> List[Dict[str, Any]]:
        """列出工作流的执行历史"""
        result = self._client.get(f"/api/workflow/{workflow_id}/executions")
        return result.get("executions", [])
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """列出内置模板"""
        result = self._client.get("/api/workflow/templates")
        return result.get("templates", [])
    
    def create_from_template(self, template_id: str) -> WorkflowInfo:
        """从模板创建工作流"""
        result = self._client.post(f"/api/workflow/templates/{template_id}")
        return WorkflowInfo.from_dict(result)
    
    def add_node(self, workflow_id: str, node: Dict[str, Any]) -> WorkflowInfo:
        """添加节点"""
        result = self._client.post(f"/api/workflow/{workflow_id}/nodes", json=node)
        return WorkflowInfo.from_dict(result)
    
    def add_edge(self, workflow_id: str, edge: Dict[str, Any]) -> WorkflowInfo:
        """添加边"""
        result = self._client.post(f"/api/workflow/{workflow_id}/edges", json=edge)
        return WorkflowInfo.from_dict(result)
    
    def delete(self, workflow_id: str) -> bool:
        """删除工作流"""
        result = self._client.delete(f"/api/workflow/{workflow_id}")
        return result.get("deleted", False)
    
    # 调度管理
    def add_schedule(
        self,
        workflow_id: str,
        trigger_type: str,
        expression: str,
        input_data: Optional[Dict] = None,
    ) -> str:
        """
        添加调度任务
        
        Args:
            workflow_id: 工作流ID
            trigger_type: 触发类型 (cron/interval/webhook)
            expression: Cron表达式或间隔秒数
            input_data: 定时输入数据
        
        Returns:
            task_id: 调度任务ID
        """
        payload = {
            "workflow_id": workflow_id,
            "trigger_type": trigger_type,
            "expression": expression,
        }
        if input_data:
            payload["input_data"] = input_data
        
        result = self._client.post("/api/workflow/schedules", json=payload)
        return result.get("task_id", "")
    
    def list_schedules(self, workflow_id: str) -> List[Dict[str, Any]]:
        """列出调度任务"""
        result = self._client.get(f"/api/workflow/{workflow_id}/schedules")
        return result.get("schedules", [])
    
    def delete_schedule(self, workflow_id: str, task_id: str) -> bool:
        """删除调度任务"""
        result = self._client.delete(f"/api/workflow/{workflow_id}/schedules/{task_id}")
        return result.get("deleted", False)


class AsyncWorkflowManager:
    """异步工作流管理器"""
    
    def __init__(self, client):
        self._client = client
    
    async def execute(self, workflow_id: str, input_data: Optional[Dict] = None) -> ExecutionResult:
        payload = {"workflow_id": workflow_id, "input_data": input_data or {}}
        result = await self._client.post("/api/workflow/execute", json=payload)
        return ExecutionResult.from_dict(result)
    
    async def create(self, name: str, **kwargs) -> WorkflowInfo:
        result = await self._client.post("/api/workflow", json={"name": name, **kwargs})
        return WorkflowInfo.from_dict(result)
