"""
SerpentAI 工作流编辑器
"""

import logging
from typing import Dict, List, Optional, Any

from .engine import WorkflowEngine, Workflow, WorkflowNode, Edge, NodeType

logger = logging.getLogger(__name__)


class WorkflowEditor:
    """
    工作流编辑器
    功能：
    1. 工作流模板管理
    2. 工作流复制和导入
    3. 可视化编辑辅助
    """
    
    def __init__(self, engine: WorkflowEngine):
        self.engine = engine
        
        # 预定义模板
        self._templates = self._load_default_templates()
    
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
    
    def create_from_template(self, template_id: str, name: str = None) -> Optional[Workflow]:
        """从模板创建工作流"""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        workflow = self.engine.create_workflow(
            name=name or template["name"],
            description=template["description"]
        )
        
        # 创建节点
        node_map = {}  # 模板节点索引 -> 实际节点ID
        workflow.nodes = []
        workflow.edges = []
        
        for node_data in template["nodes"]:
            node = WorkflowNode(
                name=node_data["name"],
                type=NodeType(node_data["type"]),
                position_x=node_data["position"]["x"],
                position_y=node_data["position"]["y"],
                inputs=node_data.get("inputs", []),
                outputs=node_data.get("outputs", [])
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
    
    def auto_layout(self, workflow: Workflow) -> Workflow:
        """自动布局节点"""
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
        
        return workflow
    
    def _calculate_node_layer(self, workflow: Workflow, node: WorkflowNode) -> int:
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
