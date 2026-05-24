"""
SerpentAI 工作流编辑器
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .engine import WorkflowEngine, Workflow, WorkflowNode, Edge, NodeType, NodeStatus, WorkflowStatus

logger = logging.getLogger(__name__)


class WorkflowEditor:
    """
    工作流编辑器
    功能：
    1. 工作流模板管理
    2. 节点CRUD操作
    3. 连线管理
    4. 工作流验证
    5. 工作流导入/导出
    6. 可视化编辑辅助
    """
    
    def __init__(self, engine: WorkflowEngine):
        self.engine = engine
        
        # 预定义模板
        self._templates = self._load_default_templates()
    
    # ==================== 节点CRUD ====================
    
    def create_node(
        self,
        workflow_id: str,
        name: str,
        node_type: str,
        position: Dict[str, float] = None,
        inputs: List[str] = None,
        outputs: List[str] = None,
        config: Dict = None
    ) -> Optional[WorkflowNode]:
        """
        创建节点
        
        Args:
            workflow_id: 工作流ID
            name: 节点名称
            node_type: 节点类型
            position: 位置 {"x": x, "y": y}
            inputs: 输入端口列表
            outputs: 输出端口列表
            config: 节点配置
        
        Returns:
            创建的节点，如果失败返回None
        """
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            logger.warning(f"工作流不存在: {workflow_id}")
            return None
        
        try:
            node_type_enum = NodeType(node_type)
        except ValueError:
            logger.warning(f"未知的节点类型: {node_type}")
            node_type_enum = NodeType.START
        
        # 设置默认的输入输出端口
        if inputs is None:
            if node_type_enum == NodeType.START:
                inputs = []
            else:
                inputs = ["in"]
        
        if outputs is None:
            if node_type_enum == NodeType.END:
                outputs = []
            else:
                outputs = ["out"]
        
        node = WorkflowNode(
            name=name,
            type=node_type_enum,
            position_x=position.get("x", 100) if position else 100,
            position_y=position.get("y", 100) if position else 100,
            inputs=inputs,
            outputs=outputs
        )
        
        # 应用配置
        if config:
            if "config" in config:
                    node.config = NodeConfig.from_dict(config["config"])
            else:
                    node.config = NodeConfig.from_dict(config)
        
        workflow.nodes.append(node)
        workflow.updated_at = datetime.now()
        
        logger.info(f"节点已创建: {workflow_id}/{node.id}")
        return node
    
    def get_node(
        self,
        workflow_id: str,
        node_id: str
    ) -> Optional[WorkflowNode]:
        """获取节点"""
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return None
        return workflow.get_node(node_id)
    
    def list_nodes(
        self,
        workflow_id: str,
        node_type: str = None,
        include_disconnected: bool = False
    ) -> List[WorkflowNode]:
        """
        列出节点
        
        Args:
            workflow_id: 工作流ID
            node_type: 可选的节点类型过滤
            include_disconnected: 是否包含孤立节点
        
        Returns:
            节点列表
        """
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return []
        
        nodes = workflow.nodes.copy()
        
        if node_type:
            try:
                node_type_enum = NodeType(node_type)
                nodes = [n for n in nodes if n.type == node_type_enum]
            except ValueError:
                pass
        
        if not include_disconnected:
            # 过滤掉孤立节点（无入边且非START类型）
            connected_targets = {e.target for e in workflow.edges}
            connected_sources = {e.source for e in workflow.edges}
            nodes = [
                n for n in nodes 
                if n.type == NodeType.START 
                or n.id in connected_targets 
                or n.id in connected_sources
            ]
        
        return nodes
    
    def update_node(
        self,
        workflow_id: str,
        node_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        更新节点
        
        Args:
            workflow_id: 工作流ID
            node_id: 节点ID
            updates:更新的字段 {"name": ..., "position": {"x":, "y":}, ...}
        
        Returns:
            是否成功
        """
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return False
        
        node = workflow.get_node(node_id)
        if not node:
            return False
        
        # 处理特殊字段
        if "position" in updates:
            node.position_x = updates["position"].get("x", node.position_x)
            node.position_y = updates["position"].get("y", node.position_y)
            updates = {k: v for k, v in updates.items() if k != "position"}
        
        if "config" in updates:
            node.config = NodeConfig.from_dict(updates["config"])
            updates = {k: v for k, v in updates.items() if k != "config"}
        
        # 更新普通字段
        for key, value in updates.items():
            if hasattr(node, key):
                setattr(node, key, value)
        workflow.updated_at = datetime.now()
        logger.info(f"节点已更新: {workflow_id}/{node_id}")
        return True
    
    def delete_node(
        self,
        workflow_id: str,
        node_id: str,
        delete_connected_edges: bool = True
    ) -> bool:
        """
        删除节点
        
        Args:
            workflow_id: 工作流ID
            node_id: 节点ID
            delete_connected_edges: 是否同时删除关联的边
        
        Returns:
            是否成功
        """
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return False
        
        node = workflow.get_node(node_id)
        if not node:
            return False
        
        if delete_connected_edges:
            # 删除关联边
            workflow.edges = [
                e for e in workflow.edges
                if e.source != node_id and e.target != node_id
            ]
        
        # 删除节点
        workflow.nodes = [n for n in workflow.nodes if n.id != node_id]
        workflow.updated_at = datetime.now()
        
        logger.info(f"节点已删除: {workflow_id}/{node_id}")
        return True
    
    # ==================== 连线管理 ====================
    
    def create_edge(
        self,
        workflow_id: str,
        source_id: str,
        target_id: str,
        source_port: str = "out",
        target_port: str = "in",
        label: str = None,
        condition: str = None
    ) -> Optional[Edge]:
        """
        创建边（连接两个节点）
        
        Args:
            workflow_id: 工作流ID
            source_id: 源节点ID
            target_id: 目标节点ID
            source_port: 源端口名称
            target_port: 目标端口名称
            label: 边标签
            condition: 条件表达式
        
        Returns:
            创建的边，如果失败返回None
        """
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            logger.warning(f"工作流不存在: {workflow_id}")
            return None
        
        # 验证节点存在
        source_node = workflow.get_node(source_id)
        target_node = workflow.get_node(target_id)
        
        if not source_node:
            logger.warning(f"源节点不存在: {source_id}")
            return None
        if not target_node:
            logger.warning(f"目标节点不存在: {target_id}")
            return None
        
        # 检查端口是否存在
        if source_port and source_port not in source_node.outputs:
            logger.warning(f"源节点没有端口: {source_port}")
            return None
        if target_port and target_port not in target_node.inputs:
            logger.warning(f"目标节点没有端口: {target_port}")
            return None
        
        # 检查是否会形成循环依赖
        if self._would_create_cycle(workflow, source_id, target_id):
            logger.warning("不能创建会导致循环依赖的边")
            return None
        
        edge = Edge(
            source=source_id,
            source_port=source_port,
            target=target_id,
            target_port=target_port,
            label=label or "",
            condition=condition or ""
        )
        
        workflow.edges.append(edge)
        workflow.updated_at = datetime.now()
        
        logger.info(f"边已创建: {workflow_id}")
        return edge
    
    def get_edge(
        self,
        workflow_id: str,
        edge_id: str
    ) -> Optional[Edge]:
        """获取边"""
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return None
        
        for edge in workflow.edges:
            if edge.id == edge_id:
                return edge
        return None
    
    def list_edges(
        self,
        workflow_id: str,
        node_id: str = None
    ) -> List[Edge]:
        """
        列出边
        
        Args:
            workflow_id: 工作流ID
            node_id: 可选，用于过滤与特定节点相关的边
        
        Returns:
            边列表
        """
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return []
        
        edges = workflow.edges.copy()
        
        if node_id:
            edges = [
                e for e in edges
                if e.source == node_id or e.target == node_id
            ]
        
        return edges
    
    def update_edge(
        self,
        workflow_id: str,
        edge_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        更新边
        
        Args:
            workflow_id: 工作流ID
            edge_id: 边ID
            updates: 更新的字段
        
        Returns:
            是否成功
        """
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return False
        
        edge = self.get_edge(workflow_id, edge_id)
        if not edge:
            return False
        
        for key, value in updates.items():
            if hasattr(edge, key):
                setattr(edge, key, value)
        
        workflow.updated_at = datetime.now()
        logger.info(f"边已更新: {workflow_id}/{edge_id}")
        return True
    
    def delete_edge(
        self,
        workflow_id: str,
        edge_id: str
    ) -> bool:
        """删除边"""
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return False
        
        workflow.edges = [e for e in workflow.edges if e.id != edge_id]
        workflow.updated_at = datetime.now()
        
        logger.info(f"边已删除: {workflow_id}/{edge_id}")
        return True
    
    def _would_create_cycle(
        self,
        workflow: Workflow,
        source_id: str,
        target_id: str
    ) -> bool:
        """检查是否会创建循环依赖"""
        # 深度优先搜索，从目标节点出发是否能回到源节点
        visited = set()
        stack = [source_id]
        
        while stack:
            current = stack.pop()
            if current == target_id:
                return True
            
            if current in visited:
                continue
            visited.add(current)
            
            # 找到所有从当前节点出发的边
            for edge in workflow.edges:
                if edge.source == current:
                    stack.append(edge.target)
        
        return False
    
    # ==================== 工作流验证 ====================
    
    def validate_workflow(
        self,
        workflow_id: str,
        detailed: bool = False
    ) -> Dict[str, Any]:
        """
        验证工作流
        
        Args:
            workflow_id: 工作流ID
            detailed: 是否返回详细错误信息
        
        Returns:
            {"valid": bool, "errors": [...], "warnings": [...]}
        """
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return {"valid": False, "errors": ["工作流不存在"], "warnings": []}
        
        errors = []
        warnings = []
        
        # 1. 检查必须的节点
        has_start = any(n.type == NodeType.START for n in workflow.nodes)
        has_end = any(n.type == NodeType.END for n in workflow.nodes)
        
        if not has_start:
            errors.append("工作流必须包含开始节点")
        if not has_end:
            errors.append("工作流必须包含结束节点")
        
        # 2. 检查节点ID唯一性
        node_ids = [n.id for n in workflow.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("存在重复的节点ID")
        
        # 3. 检查边的有效性
        valid_node_ids = set(node_ids)
        for edge in workflow.edges:
            if edge.source not in valid_node_ids:
                errors.append(f"边的源节点不存在: {edge.source}")
            if edge.target not in valid_node_ids:
                errors.append(f"边的目标节点不存在: {edge.target}")
        
        # 4. 检查孤立节点
        connected_targets = {e.target for e in workflow.edges}
        connected_sources = {e.source for e in workflow.edges}
        
        for node in workflow.nodes:
            if node.type == NodeType.START:
                continue
            if node.type == NodeType.END:
                continue
            if node.id not in connected_targets:
                warnings.append(f"节点 '{node.name}' 没有输入连接（可能不会被执行）")
        
        # 5. 检查未被连接的END节点
        for node in workflow.nodes:
            if node.type == NodeType.END and node.id not in connected_targets:
                errors.append(f"结束节点 '{node.name}' 没有输入连接")
        
        # 6. 检查循环依赖（如果还没检查过）
        is_dag, cycle_path = self._check_cycle(workflow)
        if not is_dag:
            errors.append(f"工作流存在循环依赖: {' -> '.join([workflow.get_node(n).name for n in cycle_path])}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "node_count": len(workflow.nodes),
            "edge_count": len(workflow.edges)
        }
    
    def _check_cycle(self, workflow: Workflow) -> tuple[bool, List[str]]:
        """检查是否存在循环，返回 (是否有环, 环路径)"""
        # 使用 DFS 检测环
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n.id: WHITE for n in workflow.nodes}
        parent = {n.id: None for n in workflow.nodes}
        
        def dfs(node_id: str) -> tuple[bool, List[str]]:
            color[node_id] = GRAY
            
            for edge in workflow.edges:
                if edge.source != node_id:
                    continue
                
                target = edge.target
                if color[target] == WHITE:
                    parent[target] = node_id
                    has_cycle, path = dfs(target)
                    if has_cycle:
                        return True, [node_id] + path
                elif color[target] == GRAY:
                    # 找到环
                    path = [node_id, target]
                    current = node_id
                    while parent.get(current) and parent[current] != target:
                        current = parent[current]
                        path.append(parent[current])
                    return True, path[::-1]
            
            color[node_id] = BLACK
            return False, []
        
        for node in workflow.nodes:
            if color[node.id] == WHITE:
                has_cycle, path = dfs(node.id)
                if has_cycle:
                    return True, path
        
        return False, []
    
    # ==================== 导入/导出 ====================
    
    def export_workflow(
        self,
        workflow_id: str,
        include_metadata: bool = True
    ) -> Optional[str]:
        """
        导出工作流为JSON
        
        Args:
            workflow_id: 工作流ID
            include_metadata: 是否包含元数据
        
        Returns:
            JSON字符串，失败返回None
        """
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return None
        
        data = workflow.to_dict()
        
        if not include_metadata:
            # 移除元数据
            keys_to_remove = [
                "created_at", "updated_at", "created_by",
                "execution_count", "last_execution", "last_execution_result"
            ]
            for key in keys_to_remove:
                if key in data:
                    del data[key]
        
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def import_workflow(
        self,
        json_str: str,
        new_workflow_id: str = None,
        new_name: str = None
    ) -> Optional[Workflow]:
        """
        从JSON导入工作流
        
        Args:
            json_str: JSON字符串
            new_workflow_id: 新的工作流ID（可选，默认生成新的ID）
            new_name: 新的工作流名称（可选）
        
        Returns:
            工作流对象，失败返回None
        """
        try:
            data = json.loads(json_str)
            
            # 生成新的ID或使用提供的ID
            import uuid
            if new_workflow_id:
                data["id"] = new_workflow_id
            else:
                data["id"] = uuid.uuid4().hex[:12]
            
            if new_name:
                data["name"] = new_name
            
            # 重置状态
            if "status" in data:
                data["status"] = "draft"
            if "version" in data:
                data["version"] = 1
            
            # 创建工作流
            workflow = Workflow.from_dict(data)
            self.engine.workflows[workflow.id] = workflow
            
            logger.info(f"工作流已导入: {workflow.id}")
            return workflow
            
        except Exception as e:
            logger.error(f"导入工作流失败: {e}")
            return None
    
    def export_workflow_diagram(
        self,
        workflow_id: str
    ) -> Optional[Dict]:
        """
        导出为可视化图表格式（适合前端渲染）
        
        返回:
            {
                "nodes": [...],
                "edges": [...],
                "metadata": {...}
            }
        """
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return None
        
        nodes = []
        for node in workflow.nodes:
            nodes.append({
                "id": node.id,
                "name": node.name,
                "type": node.type.value,
                "position": {"x": node.position_x, "y": node.position_y},
                "data": {
                    "config": node.config.to_dict(),
                    "inputs": node.inputs,
                    "outputs": node.outputs
                }
            })
        
        edges = []
        for edge in workflow.edges:
            edges.append({
                "id": edge.id,
                "source": edge.source,
                "target": edge.target,
                "sourcePort": edge.source_port,
                "targetPort": edge.target_port,
                "label": edge.label,
                "condition": edge.condition
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "version": workflow.version,
                "status": workflow.status.value
            }
        }
    
    # ==================== 模板管理 ====================
    
    def _load_default_templates(self) -> Dict[str, Dict]:
        """加载默认模板"""
        return {
            "chatbot": {
                "name": "智能客服机器人",
                "description": "基于AI的智能客服工作流，支持多轮对话和转人工",
                "category": "客服",
                "nodes": [
                    {
                        "name": "开始",
                        "type": "start",
                        "position": {"x": 50, "y": 200},
                        "inputs": [],
                        "outputs": ["out"]
                    },
                    {
                        "name": "用户输入",
                        "type": "input",
                        "position": {"x": 200, "y": 200},
                        "inputs": ["in"],
                        "outputs": ["out"]
                    },
                    {
                        "name": "意图识别",
                        "type": "agent",
                        "position": {"x": 400, "y": 200},
                        "inputs": ["in"],
                        "outputs": ["out"]
                    },
                    {
                        "name": "知识库检索",
                        "type": "tool_call",
                        "position": {"x": 600, "y": 200},
                        "inputs": ["in"],
                        "outputs": ["out"]
                    },
                    {
                        "name": "生成回复",
                        "type": "agent",
                        "position": {"x": 800, "y": 200},
                        "inputs": ["in"],
                        "outputs": ["out"]
                    },
                    {
                        "name": "结束",
                        "type": "end",
                        "position": {"x": 1000, "y": 200},
                        "inputs": ["in"],
                        "outputs": []
                    }
                ],
                "edges": []
            },
            "data_pipeline": {
                "name": "数据处理流水线",
                "description": "从HTTP/API获取数据，处理后存储或转发",
                "category": "数据",
                "nodes": [
                    {"name": "开始", "type": "start", "position": {"x": 50, "y": 200}, "inputs": [], "outputs": ["out"]},
                    {"name": "HTTP请求", "type": "http", "position": {"x": 200, "y": 200}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "数据转换", "type": "transform", "position": {"x": 400, "y": 200}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "数据过滤", "type": "filter", "position": {"x": 600, "y": 200}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "数据库写入", "type": "database", "position": {"x": 800, "y": 200}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "结束", "type": "end", "position": {"x": 1000, "y": 200}, "inputs": ["in"], "outputs": []}
                ],
                "edges": []
            },
            "auto_researcher": {
                "name": "自动研究助手",
                "description": "自动化网络研究，定期收集信息并生成报告",
                "category": "研究",
                "nodes": [
                    {"name": "开始", "type": "start", "position": {"x": 50, "y": 200}, "inputs": [], "outputs": ["out"]},
                    {"name": "搜索关键词", "type": "input", "position": {"x": 200, "y": 200}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "网络搜索", "type": "http", "position": {"x": 400, "y": 200}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "分析结果", "type": "agent", "position": {"x": 600, "y": 200}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "生成报告", "type": "template", "position": {"x": 800, "y": 200}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "发送通知", "type": "notification", "position": {"x": 800, "y": 320}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "结束", "type": "end", "position": {"x": 1000, "y": 200}, "inputs": ["in"], "outputs": []}
                ],
                "edges": []
            },
            "multi_agent_team": {
                "name": "多智能体团队",
                "description": "Coordinator-Executor-Critic 协作模式",
                "category": "智能体",
                "nodes": [
                    {"name": "开始", "type": "start", "position": {"x": 50, "y": 200}, "inputs": [], "outputs": ["out"]},
                    {"name": "任务输入", "type": "input", "position": {"x": 200, "y": 200}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "Coordinator", "type": "agent", "position": {"x": 400, "y": 200}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "并行执行", "type": "parallel", "position": {"x": 600, "y": 200}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "子任务1", "type": "tool_call", "position": {"x": 800, "y": 100}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "子任务2", "type": "tool_call", "position": {"x": 800, "y": 200}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "子任务3", "type": "tool_call", "position": {"x": 800, "y": 300}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "汇总结果", "type": "agent", "position": {"x": 1000, "y": 200}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "Critic评审", "type": "agent", "position": {"x": 1000, "y": 350}, "inputs": ["in"], "outputs": ["out"]},
                    {"name": "结束", "type": "end", "position": {"x": 1200, "y": 200}, "inputs": ["in"], "outputs": []}
                ],
                "edges": []
            }
        }
    
    def get_templates(self) -> List[Dict]:
        """获取所有模板"""
        return [
            {
                "id": template_id,
                "name": template["name"],
                "description": template["description"],
                "category": template["category"],
                "node_count": len(template["nodes"])
            }
            for template_id, template in self._templates.items()
        ]
    
    def create_from_template(
        self,
        template_id: str,
        name: str = None,
        workflow_id: str = None
    ) -> Optional[Workflow]:
        """从模板创建工作流"""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        workflow = self.engine.create_workflow(
            name=name or template["name"],
            description=template["description"]
        )
        
        if workflow_id:
            workflow.id = workflow_id
        
        # 清除默认节点
        workflow.nodes = []
        workflow.edges = []
        
        # 创建节点
        node_map = {}  # 模板节点索引 -> 实际节点ID
        
        for node_data in template["nodes"]:
            import uuid
            node_id = uuid.uuid4().hex[:12]
            node_map[len(node_map)] = node_id
            
            try:
                node_type = NodeType(node_data["type"])
            except ValueError:
                node_type = NodeType.START
            
            node = WorkflowNode(
                id=node_id,
                name=node_data["name"],
                type=node_type,
                position_x=node_data["position"]["x"],
                position_y=node_data["position"]["y"],
                inputs=node_data.get("inputs", ["in"]) if node_type != NodeType.START else [],
                outputs=node_data.get("outputs", ["out"]) if node_type != NodeType.END else []
            )
            workflow.nodes.append(node)
        
        # 创建边（按顺序连接）
        for i in range(len(workflow.nodes) - 1):
            edge = Edge(
                source=workflow.nodes[i].id,
                source_port="out" if workflow.nodes[i].outputs else "",
                target=workflow.nodes[i + 1].id,
                target_port="in" if workflow.nodes[i + 1].inputs else ""
            )
            workflow.edges.append(edge)
        
        self.engine.workflows[workflow.id] = workflow
        return workflow
    
    # ==================== 布局辅助 ====================
    
    def auto_layout(self, workflow_id: str) -> Optional[Workflow]:
        """自动布局节点"""
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return None
        
        # 简单的层次布局算法
        layers = {}
        
        # 找出每层的节点
        for node in workflow.nodes:
            layer = self._calculate_node_layer(workflow, node)
            if layer not in layers:
                layers[layer] = []
            layers[layer].append(node)
        
        # 计算位置
        for layer, nodes in layers.items():
            y_offset = 200
            for i, node in enumerate(nodes):
                node.position_x = layer * 200 + 50
                node.position_y = y_offset + i * 120
        
        workflow.updated_at = datetime.now()
        return workflow
    
    def _calculate_node_layer(
        self,
        workflow: Workflow,
        node: WorkflowNode
    ) -> int:
        """计算节点所在层次"""
        if node.type == NodeType.START:
            return 0
        
        incoming = workflow.get_incoming_edges(node.id)
        if not incoming:
            return 0
        
        max_layer = 0
        for edge in incoming:
            source_node = workflow.get_node(edge.source)
            if source_node:
                max_layer = max(max_layer, self._calculate_node_layer(workflow, source_node))
        
        return max_layer + 1
    
    # ==================== 批量操作 ====================
    
    def duplicate_nodes(
        self,
        workflow_id: str,
        node_ids: List[str],
        offset_x: float = 50,
        offset_y: float = 50
    ) -> List[WorkflowNode]:
        """
        复制节点
        
        Args:
            workflow_id: 工作流ID
            node_ids: 要复制的节点ID列表
            offset_x: X轴偏移
            offset_y: Y轴偏移
        
        Returns:
            新创建的节点列表
        """
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return []
        
        import uuid
        new_nodes = []
        id_mapping = {}
        
        # 复制节点
        for node_id in node_ids:
            node = workflow.get_node(node_id)
            if not node:
                continue
            
            new_node = WorkflowNode(
                id=uuid.uuid4().hex[:12],
                name=node.name,
                type=node.type,
                position_x=node.position_x + offset_x,
                position_y=node.position_y + offset_y,
                width=node.width,
                height=node.height,
                inputs=node.inputs.copy(),
                outputs=node.outputs.copy()
            )
            
            # 复制配置
            import copy
            new_node.config = copy.copy(node.config)
            
            workflow.nodes.append(new_node)
            new_nodes.append(new_node)
            id_mapping[node_id] = new_node.id
        
        return new_nodes
    
    def move_nodes(
        self,
        workflow_id: str,
        node_ids: List[str],
        delta_x: float,
        delta_y: float
    ) -> bool:
        """移动节点"""
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return False
        
        for node_id in node_ids:
            node = workflow.get_node(node_id)
            if node:
                node.position_x += delta_x
                node.position_y += delta_y
        
        workflow.updated_at = datetime.now()
        return True