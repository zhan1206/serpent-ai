"""
SerpentAI 工作流执行器
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from .engine import WorkflowEngine, Workflow, WorkflowNode, NodeType, Edge, WorkflowStatus, NodeStatus

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """
    工作流执行器
    功能：
    1. 工作流执行
    2. 节点执行
    3. 条件分支处理
    4. 并行执行
    5. 执行状态追踪
    """
    
    def __init__(self, engine: WorkflowEngine):
        self.engine = engine
        self._running_executions: Dict[str, Dict] = {}  # execution_id -> execution_state
    
    async def execute(
        self,
        workflow: Workflow,
        input_data: Dict[str, Any] = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        执行工作流
        
        Args:
            workflow: 工作流
            input_data: 输入数据
            user_id: 执行用户ID
        
        Returns:
            执行结果
        """
        execution_id = f"exec_{workflow.id}_{int(time.time())}"
        
        execution_state = {
            "id": execution_id,
            "workflow_id": workflow.id,
            "status": "running",
            "started_at": datetime.now(),
            "input": input_data or {},
            "context": {**(input_data or {}), "user_id": user_id},
            "node_results": {},
            "current_node": None,
            "error": None,
        }
        
        self._running_executions[execution_id] = execution_state
        
        try:
            # 验证工作流
            is_valid, errors = self.engine.validate_workflow(workflow)
            if not is_valid:
                raise ValueError(f"工作流验证失败: {errors}")
            
            # 更新工作流状态
            workflow.status = WorkflowStatus.ACTIVE
            workflow.execution_count += 1
            workflow.last_execution = datetime.now()
            
            # 获取拓扑排序的节点
            sorted_nodes = workflow.topological_sort()
            
            # 执行每个节点
            for node in sorted_nodes:
                execution_state["current_node"] = node.id
                
                # 检查是否应该跳过节点
                if not self._should_execute_node(workflow, node, execution_state["node_results"]):
                    node.status = NodeStatus.SKIPPED
                    continue
                
                # 执行节点
                node.start_time = datetime.now()
                node.status = NodeStatus.RUNNING
                
                try:
                    result = await self.engine.execute_node(
                        workflow,
                        node,
                        execution_state["context"]
                    )
                    
                    execution_state["node_results"][node.id] = result
                    
                    # 更新上下文
                    execution_state["context"][f"node_{node.id}_result"] = result
                    if isinstance(result, dict):
                        execution_state["context"].update(result)
                    
                except Exception as e:
                    logger.error(f"节点执行失败: {node.id}, {e}")
                    node.status = NodeStatus.FAILED
                    node.error = str(e)
                    
                    # 检查是否应该继续执行
                    if node.type != NodeType.ERROR:
                        # 如果不是错误处理节点，抛出异常
                        raise
                
                node.end_time = datetime.now()
            
            # 执行完成
            execution_state["status"] = "completed"
            execution_state["completed_at"] = datetime.now()
            workflow.status = WorkflowStatus.COMPLETED
            
            result = {
                "execution_id": execution_id,
                "workflow_id": workflow.id,
                "status": "completed",
                "results": execution_state["node_results"],
                "context": execution_state["context"],
                "started_at": execution_state["started_at"].isoformat(),
                "completed_at": execution_state["completed_at"].isoformat(),
            }
            
            workflow.last_execution_result = result
            return result
            
        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            execution_state["status"] = "failed"
            execution_state["error"] = str(e)
            execution_state["completed_at"] = datetime.now()
            workflow.status = WorkflowStatus.FAILED
            
            return {
                "execution_id": execution_id,
                "workflow_id": workflow.id,
                "status": "failed",
                "error": str(e),
                "started_at": execution_state["started_at"].isoformat(),
                "completed_at": execution_state["completed_at"].isoformat(),
            }
        
        finally:
            # 清理运行状态
            if execution_id in self._running_executions:
                del self._running_executions[execution_id]
    
    def _should_execute_node(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        node_results: Dict[str, Any]
    ) -> bool:
        """检查节点是否应该执行"""
        # 获取指向此节点的边
        incoming_edges = workflow.get_incoming_edges(node.id)
        
        # 如果没有输入边，跳过（除了START节点）
        if not incoming_edges and node.type != NodeType.START:
            return False
        
        # 检查前置节点是否都成功
        for edge in incoming_edges:
            if edge.source in node_results:
                source_result = node_results.get(edge.source, {})
                
                # 检查边的条件
                if edge.condition:
                    # 评估边的条件
                    try:
                        context = {"result": source_result}
                        if not eval(edge.condition, {"__builtins__": __builtins__}, context):
                            return False
                    except Exception:
                        pass
        
        return True
    
    async def execute_node_step(
        self,
        workflow: Workflow,
        node_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """单步执行节点"""
        node = workflow.get_node(node_id)
        if not node:
            raise ValueError(f"节点不存在: {node_id}")
        
        return await self.engine.execute_node(workflow, node, context)
    
    def get_execution_state(self, execution_id: str) -> Optional[Dict]:
        """获取执行状态"""
        return self._running_executions.get(execution_id)
    
    def pause_execution(self, execution_id: str) -> bool:
        """暂停执行（标记，异步执行需要支持）"""
        if execution_id in self._running_executions:
            self._running_executions[execution_id]["status"] = "paused"
            return True
        return False
    
    def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        if execution_id in self._running_executions:
            self._running_executions[execution_id]["status"] = "cancelled"
            return True
        return False
