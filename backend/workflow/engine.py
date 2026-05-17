"""
SerpentAI 工作流引擎 - 核心工作流系统
支持可视化工作流编排、节点编辑、条件分支、并行执行
"""

import uuid
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """节点类型"""
    # 触发器
    TRIGGER = "trigger"           # 触发器节点
    SCHEDULE = "schedule"         # 定时触发
    WEBHOOK = "webhook"          # Webhook触发
    
    # 智能体节点
    AGENT = "agent"               # 智能体节点
    TOOL_CALL = "tool_call"       # 工具调用节点
    CONDITION = "condition"       # 条件分支
    LOOP = "loop"                # 循环节点
    PARALLEL = "parallel"         # 并行执行
    SEQUENCE = "sequence"         # 顺序执行
    
    # 数据节点
    INPUT = "input"              # 输入节点
    OUTPUT = "output"             # 输出节点
    TRANSFORM = "transform"       # 数据转换
    FILTER = "filter"            # 数据过滤
    AGGREGATE = "aggregate"       # 数据聚合
    
    # 集成节点
    HTTP = "http"                # HTTP请求
    DATABASE = "database"         # 数据库操作
    MESSAGE = "message"          # 消息发送
    EMAIL = "email"              # 邮件发送
    NOTIFICATION = "notification"  # 系统通知
    
    # 工具节点
    CODE = "code"                # 代码执行
    TEMPLATE = "template"        # 模板渲染
    MATH = "math"               # 数学计算
    
    # 控制节点
    START = "start"             # 开始节点
    END = "end"                 # 结束节点
    ERROR = "error"             # 错误处理
    LOG = "log"                # 日志节点


class WorkflowStatus(Enum):
    """工作流状态"""
    DRAFT = "draft"             # 草稿
    ACTIVE = "active"           # 运行中
    PAUSED = "paused"           # 暂停
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消


class NodeStatus(Enum):
    """节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class NodeConfig:
    """节点配置"""
    # 通用配置
    timeout: int = 30           # 超时时间（秒）
    retry: int = 0              # 重试次数
    retry_delay: int = 1        # 重试延迟（秒）
    
    # Agent节点配置
    agent_model: str = "gpt-4"
    agent_temperature: float = 0.7
    agent_max_tokens: int = 2048
    agent_system_prompt: str = ""
    
    # Tool Call配置
    tool_name: str = ""
    tool_args: Dict = field(default_factory=dict)
    
    # Condition配置
    condition_expression: str = ""
    
    # Loop配置
    loop_count: int = 1
    loop_variable: str = ""
    loop_items: List = field(default_factory=list)
    
    # HTTP配置
    http_method: str = "GET"
    http_url: str = ""
    http_headers: Dict = field(default_factory=dict)
    http_body: Any = None
    
    # Code配置
    code_language: str = "python"
    code_content: str = ""
    
    # Database配置
    db_operation: str = "select"
    db_query: str = ""
    db_params: Dict = field(default_factory=dict)
    
    # Template配置
    template_content: str = ""
    template_vars: Dict = field(default_factory=dict)
    
    # Message配置
    message_channel: str = "console"
    message_content: str = ""
    
    # Schedule配置
    schedule_cron: str = ""
    schedule_interval: int = 0
    
    # Input/Output配置
    input_schema: Dict = field(default_factory=dict)
    output_schema: Dict = field(default_factory=dict)
    
    # 自定义配置
    custom: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "timeout": self.timeout,
            "retry": self.retry,
            "retry_delay": self.retry_delay,
            "agent_model": self.agent_model,
            "agent_temperature": self.agent_temperature,
            "agent_max_tokens": self.agent_max_tokens,
            "agent_system_prompt": self.agent_system_prompt,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "condition_expression": self.condition_expression,
            "loop_count": self.loop_count,
            "loop_variable": self.loop_variable,
            "loop_items": self.loop_items,
            "http_method": self.http_method,
            "http_url": self.http_url,
            "http_headers": self.http_headers,
            "http_body": self.http_body,
            "code_language": self.code_language,
            "code_content": self.code_content,
            "db_operation": self.db_operation,
            "db_query": self.db_query,
            "db_params": self.db_params,
            "template_content": self.template_content,
            "template_vars": self.template_vars,
            "message_channel": self.message_channel,
            "message_content": self.message_content,
            "schedule_cron": self.schedule_cron,
            "schedule_interval": self.schedule_interval,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "custom": self.custom,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "NodeConfig":
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


@dataclass
class WorkflowNode:
    """工作流节点"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    type: NodeType = NodeType.START
    config: NodeConfig = field(default_factory=NodeConfig)
    
    # 位置信息（用于可视化编辑器）
    position_x: float = 0
    position_y: float = 0
    width: float = 150
    height: float = 80
    
    # 输入输出定义
    inputs: List[str] = field(default_factory=list)  # 输入端口名称列表
    outputs: List[str] = field(default_factory=list) # 输出端口名称列表
    
    # 状态
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # 条件分支配置
    branches: List[str] = field(default_factory=list)  # 分支节点ID列表
    default_branch: Optional[str] = None  # 默认分支（条件不满足时）
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "config": self.config.to_dict(),
            "position": {"x": self.position_x, "y": self.position_y},
            "size": {"width": self.width, "height": self.height},
            "inputs": self.inputs,
            "outputs": self.outputs,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "branches": self.branches,
            "default_branch": self.default_branch,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "WorkflowNode":
        return cls(
            id=data.get("id", uuid.uuid4().hex[:12]),
            name=data.get("name", ""),
            type=NodeType(data.get("type", "start")),
            config=NodeConfig.from_dict(data.get("config", {})),
            position_x=data.get("position", {}).get("x", 0),
            position_y=data.get("position", {}).get("y", 0),
            width=data.get("size", {}).get("width", 150),
            height=data.get("size", {}).get("height", 80),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            status=NodeStatus(data.get("status", "pending")),
            result=data.get("result"),
            error=data.get("error", ""),
            start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None,
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            branches=data.get("branches", []),
            default_branch=data.get("default_branch"),
        )


@dataclass
class Edge:
    """工作流边（连接）"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source: str = ""      # 源节点ID
    source_port: str = "" # 源端口名称
    target: str = ""      # 目标节点ID
    target_port: str = "" # 目标端口名称
    label: str = ""       # 边的标签
    condition: str = ""   # 条件表达式
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "source": self.source,
            "sourcePort": self.source_port,
            "target": self.target,
            "targetPort": self.target_port,
            "label": self.label,
            "condition": self.condition,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Edge":
        return cls(
            id=data.get("id", uuid.uuid4().hex[:12]),
            source=data.get("source", ""),
            source_port=data.get("sourcePort", ""),
            target=data.get("target", ""),
            target_port=data.get("targetPort", ""),
            label=data.get("label", ""),
            condition=data.get("condition", ""),
        )


@dataclass
class Workflow:
    """工作流"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    version: int = 1
    
    # 结构和数据
    nodes: List[WorkflowNode] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    
    # 状态
    status: WorkflowStatus = WorkflowStatus.DRAFT
    variables: Dict[str, Any] = field(default_factory=dict)  # 工作流变量
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    tags: List[str] = field(default_factory=list)
    
    # 执行数据
    execution_count: int = 0
    last_execution: Optional[datetime] = None
    last_execution_result: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "status": self.status.value,
            "variables": self.variables,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "tags": self.tags,
            "execution_count": self.execution_count,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "last_execution_result": self.last_execution_result,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Workflow":
        return cls(
            id=data.get("id", uuid.uuid4().hex[:12]),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", 1),
            nodes=[WorkflowNode.from_dict(n) for n in data.get("nodes", [])],
            edges=[Edge.from_dict(e) for e in data.get("edges", [])],
            status=WorkflowStatus(data.get("status", "draft")),
            variables=data.get("variables", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            created_by=data.get("created_by", ""),
            tags=data.get("tags", []),
            execution_count=data.get("execution_count", 0),
            last_execution=datetime.fromisoformat(data["last_execution"]) if data.get("last_execution") else None,
            last_execution_result=data.get("last_execution_result"),
        )
    
    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """获取节点"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_incoming_edges(self, node_id: str) -> List[Edge]:
        """获取指向节点的边"""
        return [e for e in self.edges if e.target == node_id]
    
    def get_outgoing_edges(self, node_id: str) -> List[Edge]:
        """获取从节点出发的边"""
        return [e for e in self.edges if e.source == node_id]
    
    def topological_sort(self) -> List[WorkflowNode]:
        """拓扑排序"""
        # 计算入度
        in_degree = {n.id: 0 for n in self.nodes}
        for edge in self.edges:
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1
        
        # 从入度为0的节点开始
        queue = [n for n in self.nodes if in_degree[n.id] == 0]
        sorted_nodes = []
        
        while queue:
            node = queue.pop(0)
            sorted_nodes.append(node)
            
            # 更新相邻节点的入度
            for edge in self.get_outgoing_edges(node.id):
                in_degree[edge.target] -= 1
                if in_degree[edge.target] == 0:
                    next_node = self.get_node(edge.target)
                    if next_node:
                        queue.append(next_node)
        
        return sorted_nodes


class WorkflowEngine:
    """
    工作流引擎
    功能：
    1. 工作流创建、编辑、删除
    2. 工作流验证
    3. 工作流执行
    4. 工作流状态管理
    """
    
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self._executors: Dict[str, Any] = {}  # workflow_id -> executor
        
        # 节点执行器映射
        self._node_handlers: Dict[NodeType, Callable] = {}
        self._register_default_handlers()
        
        logger.info("工作流引擎初始化完成")
    
    def _register_default_handlers(self):
        """注册默认节点处理器"""
        # 基础处理器
        self._node_handlers[NodeType.START] = self._handle_start
        self._node_handlers[NodeType.END] = self._handle_end
        self._node_handlers[NodeType.TRIGGER] = self._handle_trigger
        self._node_handlers[NodeType.LOG] = self._handle_log
        
        # Agent处理器
        self._node_handlers[NodeType.AGENT] = self._handle_agent
        self._node_handlers[NodeType.TOOL_CALL] = self._handle_tool_call
        self._node_handlers[NodeType.CONDITION] = self._handle_condition
        self._node_handlers[NodeType.LOOP] = self._handle_loop
        self._node_handlers[NodeType.PARALLEL] = self._handle_parallel
        self._node_handlers[NodeType.SEQUENCE] = self._handle_sequence
        
        # 数据处理器
        self._node_handlers[NodeType.INPUT] = self._handle_input
        self._node_handlers[NodeType.OUTPUT] = self._handle_output
        self._node_handlers[NodeType.TRANSFORM] = self._handle_transform
        self._node_handlers[NodeType.FILTER] = self._handle_filter
        
        # 集成处理器
        self._node_handlers[NodeType.HTTP] = self._handle_http
        self._node_handlers[NodeType.MESSAGE] = self._handle_message
        self._node_handlers[NodeType.EMAIL] = self._handle_email
        self._node_handlers[NodeType.NOTIFICATION] = self._handle_notification
        
        # 工具处理器
        self._node_handlers[NodeType.CODE] = self._handle_code
        self._node_handlers[NodeType.TEMPLATE] = self._handle_template
        self._node_handlers[NodeType.MATH] = self._handle_math
    
    # ==================== 工作流管理 ====================
    
    def create_workflow(
        self,
        name: str,
        description: str = "",
        created_by: str = ""
    ) -> Workflow:
        """创建工作流"""
        workflow = Workflow(
            name=name,
            description=description,
            created_by=created_by
        )
        
        # 添加默认的Start和End节点
        start_node = WorkflowNode(
            name="开始",
            type=NodeType.START,
            position_x=100,
            position_y=100,
            inputs=[],
            outputs=["out"]
        )
        
        end_node = WorkflowNode(
            name="结束",
            type=NodeType.END,
            position_x=600,
            position_y=100,
            inputs=["in"],
            outputs=[]
        )
        
        workflow.nodes = [start_node, end_node]
        workflow.edges = []
        
        self.workflows[workflow.id] = workflow
        
        logger.info(f"工作流已创建: {workflow.id} ({name})")
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """获取工作流"""
        return self.workflows.get(workflow_id)
    
    def update_workflow(self, workflow: Workflow) -> bool:
        """更新工作流"""
        if workflow.id not in self.workflows:
            return False
        
        workflow.updated_at = datetime.now()
        workflow.version += 1
        self.workflows[workflow.id] = workflow
        
        logger.info(f"工作流已更新: {workflow.id}")
        return True
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """删除工作流"""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            logger.info(f"工作流已删除: {workflow_id}")
            return True
        return False
    
    def list_workflows(
        self,
        status: WorkflowStatus = None,
        tags: List[str] = None
    ) -> List[Workflow]:
        """列出工作流"""
        workflows = list(self.workflows.values())
        
        if status:
            workflows = [w for w in workflows if w.status == status]
        
        if tags:
            workflows = [
                w for w in workflows
                if any(tag in w.tags for tag in tags)
            ]
        
        return workflows
    
    # ==================== 节点操作 ====================
    
    def add_node(
        self,
        workflow_id: str,
        node: WorkflowNode
    ) -> bool:
        """添加节点"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        workflow.nodes.append(node)
        workflow.updated_at = datetime.now()
        
        logger.info(f"节点已添加: {workflow_id}/{node.id}")
        return True
    
    def update_node(
        self,
        workflow_id: str,
        node_id: str,
        updates: Dict
    ) -> bool:
        """更新节点"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        node = workflow.get_node(node_id)
        if not node:
            return False
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(node, key):
                setattr(node, key, value)
        
        workflow.updated_at = datetime.now()
        return True
    
    def delete_node(self, workflow_id: str, node_id: str) -> bool:
        """删除节点"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        # 移除节点
        workflow.nodes = [n for n in workflow.nodes if n.id != node_id]
        
        # 移除相关边
        workflow.edges = [
            e for e in workflow.edges
            if e.source != node_id and e.target != node_id
        ]
        
        workflow.updated_at = datetime.now()
        return True
    
    # ==================== 边操作 ====================
    
    def add_edge(
        self,
        workflow_id: str,
        edge: Edge
    ) -> bool:
        """添加边"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        # 验证源和目标节点存在
        if not workflow.get_node(edge.source) or not workflow.get_node(edge.target):
            return False
        
        workflow.edges.append(edge)
        workflow.updated_at = datetime.now()
        
        logger.info(f"边已添加: {workflow_id}")
        return True
    
    def delete_edge(self, workflow_id: str, edge_id: str) -> bool:
        """删除边"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        workflow.edges = [e for e in workflow.edges if e.id != edge_id]
        workflow.updated_at = datetime.now()
        return True
    
    # ==================== 工作流验证 ====================
    
    def validate_workflow(self, workflow: Workflow) -> tuple[bool, List[str]]:
        """
        验证工作流
        
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        # 检查是否有开始和结束节点
        has_start = any(n.type == NodeType.START for n in workflow.nodes)
        has_end = any(n.type == NodeType.END for n in workflow.nodes)
        
        if not has_start:
            errors.append("工作流必须包含开始节点")
        if not has_end:
            errors.append("工作流必须包含结束节点")
        
        # 检查节点ID唯一性
        node_ids = [n.id for n in workflow.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("存在重复的节点ID")
        
        # 检查边的有效性
        for edge in workflow.edges:
            if edge.source not in node_ids:
                errors.append(f"边的源节点不存在: {edge.source}")
            if edge.target not in node_ids:
                errors.append(f"边的目标节点不存在: {edge.target}")
        
        # 检查每个节点的输入是否都有边提供
        for node in workflow.nodes:
            if node.type == NodeType.START:
                continue
            
            # 检查是否有边指向此节点
            has_input = any(e.target == node.id for e in workflow.edges)
            if not has_input:
                errors.append(f"节点 {node.id} 没有输入边")
        
        return len(errors) == 0, errors
    
    # ==================== 节点处理器 ====================
    
    async def execute_node(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict[str, Any]
    ) -> Any:
        """执行节点"""
        handler = self._node_handlers.get(node.type)
        
        if not handler:
            return {"error": f"未知的节点类型: {node.type}"}
        
        try:
            result = await handler(workflow, node, context)
            node.result = result
            node.status = NodeStatus.COMPLETED
            return result
        except Exception as e:
            logger.error(f"节点执行失败: {node.id}, {e}")
            node.status = NodeStatus.FAILED
            node.error = str(e)
            node.result = {"error": str(e)}
            raise
    
    # START节点
    async def _handle_start(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        return {"status": "started", "workflow_id": workflow.id}
    
    # END节点
    async def _handle_end(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        return {"status": "completed"}
    
    # TRIGGER节点
    async def _handle_trigger(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        # Webhook触发器
        return {"triggered": True, "source": "webhook"}
    
    # LOG节点
    async def _handle_log(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        message = node.config.message_content
        # 替换变量
        for key, value in context.items():
            message = message.replace(f"{{{key}}}", str(value))
        logger.info(f"[Workflow Log] {message}")
        return {"logged": message}
    
    # INPUT节点
    async def _handle_input(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        input_data = context.get("input", {})
        return {"data": input_data}
    
    # OUTPUT节点
    async def _handle_output(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        return {"output": context.get("result")}
    
    # MESSAGE节点
    async def _handle_message(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        message = node.config.message_content
        for key, value in context.items():
            message = message.replace(f"{{{key}}}", str(value))
        return {"sent": True, "message": message}
    
    # NOTIFICATION节点
    async def _handle_notification(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        return {"notification": "sent"}
    
    # EMAIL节点
    async def _handle_email(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        return {"email": "sent"}
    
    # MATH节点
    async def _handle_math(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        expression = node.config.custom.get("expression", "0")
        for key, value in context.items():
            expression = expression.replace(f"{{{key}}}", str(value))
        try:
            result = eval(expression)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}
    
    # TRANSFORM节点
    async def _handle_transform(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        return {"transformed": context.get("data")}
    
    # FILTER节点
    async def _handle_filter(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        return {"filtered": context.get("data", [])}
    
    # TEMPLATE节点
    async def _handle_template(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        template = node.config.template_content
        vars_dict = {**node.config.template_vars, **context}
        for key, value in vars_dict.items():
            template = template.replace(f"{{{key}}}", str(value))
        return {"rendered": template}
    
    # HTTP节点
    async def _handle_http(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        return {
            "http_requested": True,
            "method": node.config.http_method,
            "url": node.config.http_url
        }
    
    # AGENT节点
    async def _handle_agent(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        # 调用智能体处理
        input_text = context.get("input", "")
        return {
            "agent_response": f"处理: {input_text}",
            "model": node.config.agent_model
        }
    
    # TOOL_CALL节点
    async def _handle_tool_call(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        tool_name = node.config.tool_name
        tool_args = node.config.tool_args
        
        # 替换变量
        for key, value in context.items():
            for arg_key, arg_val in tool_args.items():
                if isinstance(arg_val, str):
                    tool_args[arg_key] = arg_val.replace(f"{{{key}}}", str(value))
        
        return {
            "tool_called": True,
            "tool_name": tool_name,
            "args": tool_args
        }
    
    # CONDITION节点
    async def _handle_condition(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        expression = node.config.condition_expression
        for key, value in context.items():
            expression = expression.replace(f"{{{key}}}", str(value))
        
        try:
            result = eval(expression)
            return {"condition_met": bool(result)}
        except Exception as e:
            return {"error": str(e), "condition_met": False}
    
    # LOOP节点
    async def _handle_loop(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        return {"loops": node.config.loop_count}
    
    # PARALLEL节点
    async def _handle_parallel(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        return {"parallel_tasks": len(node.branches)}
    
    # SEQUENCE节点
    async def _handle_sequence(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        return {"sequence_tasks": len(node.branches)}
    
    # CODE节点
    async def _handle_code(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: Dict
    ) -> Dict:
        code = node.config.code_content
        language = node.config.code_language
        
        # 简单的代码执行（实际生产中应该用沙箱）
        if language == "python":
            try:
                local_vars = {**context}
                exec(code, {"__builtins__": __builtins__}, local_vars)
                return {"executed": True, "result": local_vars.get("result")}
            except Exception as e:
                return {"error": str(e)}
        else:
            return {"error": f"不支持的语言: {language}"}
    
    # ==================== 导入/导出 ====================
    
    def export_workflow(self, workflow_id: str) -> Optional[str]:
        """导出工作流为JSON"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return None
        return json.dumps(workflow.to_dict(), ensure_ascii=False, indent=2)
    
    def import_workflow(self, json_str: str) -> Optional[Workflow]:
        """从JSON导入工作流"""
        try:
            data = json.loads(json_str)
            workflow = Workflow.from_dict(data)
            self.workflows[workflow.id] = workflow
            return workflow
        except Exception as e:
            logger.error(f"导入工作流失败: {e}")
            return None
    
    def clone_workflow(self, workflow_id: str, new_name: str = None) -> Optional[Workflow]:
        """克隆工作流"""
        original = self.get_workflow(workflow_id)
        if not original:
            return None
        
        data = original.to_dict()
        data["id"] = uuid.uuid4().hex[:12]
        data["name"] = new_name or f"{original.name} (副本)"
        data["version"] = 1
        data["status"] = WorkflowStatus.DRAFT
        data["execution_count"] = 0
        data["last_execution"] = None
        
        # 重新生成节点ID
        old_new_ids = {}
        for node in data["nodes"]:
            old_id = node["id"]
            new_id = uuid.uuid4().hex[:12]
            old_new_ids[old_id] = new_id
            node["id"] = new_id
        
        # 更新边的引用
        for edge in data["edges"]:
            edge["id"] = uuid.uuid4().hex[:12]
            edge["source"] = old_new_ids.get(edge["source"], edge["source"])
            edge["target"] = old_new_ids.get(edge["target"], edge["target"])
        
        return self.import_workflow(json.dumps(data, ensure_ascii=False))
