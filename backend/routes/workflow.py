"""
SerpentAI 工作流 API 路由
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.workflow.engine import WorkflowEngine, Workflow, WorkflowNode, Edge, WorkflowStatus, NodeType, NodeStatus
from backend.workflow.executor import WorkflowExecutor
from backend.workflow.editor import WorkflowEditor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

# 全局实例
_engine = None
_executor = None
_editor = None


def get_engine() -> WorkflowEngine:
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine


def get_executor() -> WorkflowExecutor:
    global _executor
    if _executor is None:
        _executor = WorkflowExecutor(get_engine())
    return _executor


def get_editor() -> WorkflowEditor:
    global _editor
    if _editor is None:
        _editor = WorkflowEditor(get_engine())
    return _editor


# ==================== 请求/响应模型 ====================

class CreateWorkflowRequest(BaseModel):
    name: str
    description: str = ""
    created_by: str = ""


class UpdateWorkflowRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    variables: Optional[Dict[str, Any]] = None


class AddNodeRequest(BaseModel):
    workflow_id: str
    name: str
    type: str
    position_x: float = 0
    position_y: float = 0
    config: Dict[str, Any] = {}
    inputs: List[str] = []
    outputs: List[str] = []
    branches: List[str] = []


class UpdateNodeRequest(BaseModel):
    workflow_id: str
    node_id: str
    name: Optional[str] = None
    type: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    config: Optional[Dict[str, Any]] = None
    inputs: Optional[List[str]] = None
    outputs: Optional[List[str]] = None
    branches: Optional[List[str]] = None


class AddEdgeRequest(BaseModel):
    workflow_id: str
    source: str
    source_port: str = "out"
    target: str
    target_port: str = "in"
    label: str = ""
    condition: str = ""


class ExecuteWorkflowRequest(BaseModel):
    workflow_id: str
    input_data: Dict[str, Any] = {}
    user_id: str = ""


class ImportWorkflowRequest(BaseModel):
    json_data: str


# ==================== 工作流管理 API ====================

@router.post("/")
async def create_workflow(request: CreateWorkflowRequest) -> Dict:
    """创建工作流"""
    engine = get_engine()
    workflow = engine.create_workflow(
        name=request.name,
        description=request.description,
        created_by=request.created_by
    )
    return workflow.to_dict()


@router.get("/")
async def list_workflows(
    status: str = None,
    tags: str = None
) -> List[Dict]:
    """列出工作流"""
    engine = get_engine()
    
    status_filter = None
    if status:
        try:
            status_filter = WorkflowStatus(status)
        except ValueError:
            pass
    
    tag_list = tags.split(",") if tags else None
    
    workflows = engine.list_workflows(status=status_filter, tags=tag_list)
    return [w.to_dict() for w in workflows]


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str) -> Dict:
    """获取工作流"""
    engine = get_engine()
    workflow = engine.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    return workflow.to_dict()


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    request: UpdateWorkflowRequest
) -> Dict:
    """更新工作流"""
    engine = get_engine()
    workflow = engine.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    if request.name is not None:
        workflow.name = request.name
    if request.description is not None:
        workflow.description = request.description
    if request.tags is not None:
        workflow.tags = request.tags
    if request.variables is not None:
        workflow.variables = request.variables
    
    engine.update_workflow(workflow)
    
    return workflow.to_dict()


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str) -> Dict:
    """删除工作流"""
    engine = get_engine()
    
    if not engine.delete_workflow(workflow_id):
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    return {"deleted": True, "workflow_id": workflow_id}


@router.post("/{workflow_id}/validate")
async def validate_workflow(workflow_id: str) -> Dict:
    """验证工作流"""
    engine = get_engine()
    workflow = engine.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    is_valid, errors = engine.validate_workflow(workflow)
    
    return {
        "valid": is_valid,
        "errors": errors
    }


@router.post("/{workflow_id}/clone")
async def clone_workflow(workflow_id: str, new_name: str = None) -> Dict:
    """克隆工作流"""
    engine = get_engine()
    workflow = engine.clone_workflow(workflow_id, new_name)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    return workflow.to_dict()


# ==================== 节点管理 API ====================

@router.post("/nodes")
async def add_node(request: AddNodeRequest) -> Dict:
    """添加节点"""
    engine = get_engine()
    
    node = WorkflowNode(
        name=request.name,
        type=NodeType(request.type),
        position_x=request.position_x,
        position_y=request.position_y,
        inputs=request.inputs,
        outputs=request.outputs,
        branches=request.branches
    )
    
    # 设置配置
    from backend.workflow.engine import NodeConfig
    node.config = NodeConfig.from_dict(request.config)
    
    if not engine.add_node(request.workflow_id, node):
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    return node.to_dict()


@router.put("/nodes")
async def update_node(request: UpdateNodeRequest) -> Dict:
    """更新节点"""
    engine = get_engine()
    
    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.type is not None:
        updates["type"] = NodeType(request.type)
    if request.position_x is not None:
        updates["position_x"] = request.position_x
    if request.position_y is not None:
        updates["position_y"] = request.position_y
    if request.config is not None:
        from backend.workflow.engine import NodeConfig
        updates["config"] = NodeConfig.from_dict(request.config)
    if request.inputs is not None:
        updates["inputs"] = request.inputs
    if request.outputs is not None:
        updates["outputs"] = request.outputs
    if request.branches is not None:
        updates["branches"] = request.branches
    
    if not engine.update_node(request.workflow_id, request.node_id, updates):
        raise HTTPException(status_code=404, detail="工作流或节点不存在")
    
    workflow = engine.get_workflow(request.workflow_id)
    node = workflow.get_node(request.node_id)
    return node.to_dict()


@router.delete("/{workflow_id}/nodes/{node_id}")
async def delete_node(workflow_id: str, node_id: str) -> Dict:
    """删除节点"""
    engine = get_engine()
    
    if not engine.delete_node(workflow_id, node_id):
        raise HTTPException(status_code=404, detail="工作流或节点不存在")
    
    return {"deleted": True, "node_id": node_id}


# ==================== 边管理 API ====================

@router.post("/edges")
async def add_edge(request: AddEdgeRequest) -> Dict:
    """添加边"""
    engine = get_engine()
    
    edge = Edge(
        source=request.source,
        source_port=request.source_port,
        target=request.target,
        target_port=request.target_port,
        label=request.label,
        condition=request.condition
    )
    
    if not engine.add_edge(request.workflow_id, edge):
        raise HTTPException(status_code=400, detail="添加边失败")
    
    return edge.to_dict()


@router.delete("/{workflow_id}/edges/{edge_id}")
async def delete_edge(workflow_id: str, edge_id: str) -> Dict:
    """删除边"""
    engine = get_engine()
    
    if not engine.delete_edge(workflow_id, edge_id):
        raise HTTPException(status_code=404, detail="边不存在")
    
    return {"deleted": True, "edge_id": edge_id}


# ==================== 执行 API ====================

@router.post("/execute")
async def execute_workflow(request: ExecuteWorkflowRequest) -> Dict:
    """执行工作流"""
    engine = get_engine()
    executor = get_executor()
    
    workflow = engine.get_workflow(request.workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 异步执行
    result = await executor.execute(
        workflow,
        input_data=request.input_data,
        user_id=request.user_id
    )
    
    return result


@router.get("/{workflow_id}/executions")
async def get_workflow_executions(workflow_id: str) -> List[Dict]:
    """获取工作流的执行历史"""
    engine = get_engine()
    workflow = engine.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    return [{
        "execution_count": workflow.execution_count,
        "last_execution": workflow.last_execution.isoformat() if workflow.last_execution else None,
        "last_result": workflow.last_execution_result,
        "status": workflow.status.value
    }]


# ==================== 导入/导出 API ====================

@router.post("/import")
async def import_workflow(request: ImportWorkflowRequest) -> Dict:
    """导入工作流"""
    engine = get_engine()
    workflow = engine.import_workflow(request.json_data)
    
    if not workflow:
        raise HTTPException(status_code=400, detail="导入失败")
    
    return workflow.to_dict()


@router.get("/{workflow_id}/export")
async def export_workflow(workflow_id: str) -> Dict:
    """导出工作流"""
    engine = get_engine()
    json_str = engine.export_workflow(workflow_id)
    
    if not json_str:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    return {"json": json_str}


# ==================== 模板 API ====================

@router.get("/templates")
async def list_templates() -> List[Dict]:
    """获取工作流模板"""
    engine = get_engine()
    editor = get_editor()
    templates = editor.get_templates()
    
    return templates


@router.post("/templates/{template_id}")
async def create_from_template(
    template_id: str,
    name: str = None
) -> Dict:
    """从模板创建工作流"""
    engine = get_engine()
    editor = get_editor()
    
    workflow = editor.create_from_template(template_id, name)
    if not workflow:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    return workflow.to_dict()
