"""
SerpentAI 工作流执行器
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import time
import uuid

from .engine import WorkflowEngine, Workflow, WorkflowNode, NodeType, Edge, WorkflowStatus, NodeStatus

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """
    工作流执行器
    功能：
    1. 工作流执行
    2. 节点执行
    3. 条件分支处理
    4. 循环处理
    5. 并行执行
    6. 错误处理
    7. 执行状态追踪
    8. 变量传递
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
            "variables": {},  # 工作流级别的变量存储
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
                if not self._should_execute_node(workflow, node, execution_state):
                    node.status = NodeStatus.SKIPPED
                    continue
                
                # 判断节点类型并执行
                if node.type == NodeType.CONDITION:
                    # 条件分支节点
                    result = await self._execute_condition_node(workflow, node, execution_state)
                elif node.type == NodeType.LOOP:
                    # 循环节点
                    result = await self._execute_loop_node(workflow, node, sorted_nodes, execution_state)
                elif node.type == NodeType.PARALLEL:
                    # 并行节点
                    result = await self._execute_parallel_node(workflow, node, sorted_nodes, execution_state)
                elif node.type == NodeType.ERROR:
                    # 错误处理节点
                    result = await self._execute_error_node(workflow, node, execution_state)
                else:
                    # 普通节点
                    node.start_time = datetime.now()
                    node.status = NodeStatus.RUNNING
                    
                    result = await self.engine.execute_node(
                        workflow,
                        node,
                        execution_state["context"]
                    )
                
                # 记录结果
                execution_state["node_results"][node.id] = result
                
                # 更新变量传递
                self._update_variables(workflow, node, result, execution_state)
                
                # 检查节点执行是否失败（如果不是错误处理类型）
                if node.type != NodeType.ERROR and node.type != NodeType.LOOP and node.type != NodeType.PARALLEL:
                    if isinstance(result, dict) and result.get("error"):
                        node.status = NodeStatus.FAILED
                        node.error = result.get("error")
                        
                        # 检查是否有错误处理分支
                        error_handler = self._find_error_handler(workflow, node)
                        if error_handler:
                            # 执行错误处理
                            await self._execute_error_handler(
                                workflow, error_handler, execution_state
                            )
                        else:
                            raise Exception(result.get("error"))
                
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
                "variables": execution_state["variables"],
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
                "context": execution_state["context"],
                "started_at": execution_state["started_at"].isoformat(),
                "completed_at": execution_state["completed_at"].isoformat(),
            }
        
        finally:
            # 清理运行状态
            if execution_id in self._running_executions:
                del self._running_executions[execution_id]
    
    # ==================== 条件分支执行 ====================
    
    async def _execute_condition_node(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        execution_state: Dict
    ) -> Dict[str, Any]:
        """执行条件分支节点"""
        node.start_time = datetime.now()
        node.status = NodeStatus.RUNNING
        
        # 评估条件
        context = execution_state["context"]
        expression = node.config.condition_expression
        
        # 替换变量
        for key, value in context.items():
            if isinstance(value, str):
                expression = expression.replace(f"{{{key}}}", value)
            elif isinstance(value, (int, float)):
                expression = expression.replace(f"{{{key}}}", str(value))
        
        try:
            condition_met = bool(eval(expression, {"__builtins__": __builtins__}, {}))
        except Exception as e:
            logger.error(f"条件评估失败: {e}")
            condition_met = False
        
        # 确定执行的分支
        branch_to_execute = None
        if condition_met:
            # 检查条件为true的分支
            for i, branch_id in enumerate(node.branches):
                if i == 0:  # 第一个分支为条件满足时执行
                    branch_to_execute = branch_id
                    break
        else:
            # 使用默认分支
            if node.default_branch:
                branch_to_execute = node.default_branch
        
        result = {
            "condition_met": condition_met,
            "branch_executed": branch_to_execute,
            "expression": expression
        }
        
        node.status = NodeStatus.COMPLETED
        node.result = result
        
        return result
    
    # ==================== 循环执行 ====================
    
    async def _execute_loop_node(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        all_nodes: List[WorkflowNode],
        execution_state: Dict
    ) -> Dict[str, Any]:
        """执行循环节点"""
        node.start_time = datetime.now()
        node.status = NodeStatus.RUNNING
        
        loop_count = node.config.loop_count
        loop_items = node.config.loop_items or []
        loop_variable = node.config.loop_variable
        
        context = execution_state["context"]
        iteration_results = []
        
        # 确定循环次数
        max_iterations = loop_count
        if loop_items:
            max_iterations = len(loop_items)
        
        # 执行循环
        for i in range(max_iterations):
            iteration_context = context.copy()
            
            # 设置循环变量
            if loop_items and i < len(loop_items):
                iteration_context[loop_variable] = loop_items[i]
            elif loop_variable:
                iteration_context[loop_variable] = i
            
            iteration_context["loop_index"] = i
            iteration_context["loop_total"] = max_iterations
            
            # 创建临时执行上下文
            temp_state = {
                "context": iteration_context,
                "node_results": execution_state["node_results"],
                "variables": execution_state["variables"]
            }
            
            # 执行分支节点（在循环节点中定义的子节点）
            for branch_id in node.branches:
                branch_node = workflow.get_node(branch_id)
                if not branch_node:
                    continue
                
                try:
                    result = await self.engine.execute_node(
                        workflow,
                        branch_node,
                        iteration_context
                    )
                    iteration_results.append(result)
                except Exception as e:
                    logger.warning(f"循环迭代 {i} 失败: {e}")
                    if node.config.custom.get("continue_on_error"):
                        continue
                    raise
        
        result = {
            "iterations": max_iterations,
            "iteration_results": iteration_results,
            "loop_variable": loop_variable
        }
        
        node.status = NodeStatus.COMPLETED
        node.result = result
        
        return result
    
    # ==================== 并行执行 ====================
    
    async def _execute_parallel_node(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        all_nodes: List[WorkflowNode],
        execution_state: Dict
    ) -> Dict[str, Any]:
        """执行并行节点"""
        node.start_time = datetime.now()
        node.status = NodeStatus.RUNNING
        
        context = execution_state["context"]
        
        # 收集要并行执行的分支节点
        branch_tasks = []
        branch_names = []
        
        for branch_id in node.branches:
            branch_node = workflow.get_node(branch_id)
            if branch_node:
                branch_tasks.append(
                    self.engine.execute_node(workflow, branch_node, context)
                )
                branch_names.append(branch_node.name)
        
        # 并行执行所有分支
        if branch_tasks:
            results = await asyncio.gather(*branch_tasks, return_exceptions=True)
        else:
            results = []
        
        # 整理结果
        parallel_results = {}
        for name, result in zip(branch_names, results):
            if isinstance(result, Exception):
                parallel_results[name] = {"error": str(result)}
            else:
                parallel_results[name] = result
        
        result = {
            "parallel_tasks": len(branch_tasks),
            "results": parallel_results
        }
        
        node.status = NodeStatus.COMPLETED
        node.result = result
        
        return result
    
    # ==================== 错误处理 ====================
    
    async def _execute_error_node(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        execution_state: Dict
    ) -> Dict[str, Any]:
        """执行错误处理节点"""
        node.status = NodeStatus.RUNNING
        
        # 获取上一个错误
        error = execution_state.get("error")
        
        context = execution_state["context"]
        context["error"] = error
        
        result = await self.engine.execute_node(workflow, node, context)
        
        node.status = NodeStatus.COMPLETED
        return result
    
    async def _execute_error_handler(
        self,
        workflow: Workflow,
        error_handler: WorkflowNode,
        execution_state: Dict
    ):
        """执行错误处理"""
        error_handler.status = NodeStatus.RUNNING
        error_handler.start_time = datetime.now()
        
        try:
            result = await self.engine.execute_node(
                workflow,
                error_handler,
                execution_state["context"]
            )
            execution_state["node_results"][error_handler.id] = result
        except Exception as e:
            logger.error(f"错误处理执行失败: {e}")
        
        error_handler.end_time = datetime.now()
    
    def _find_error_handler(
        self,
        workflow: Workflow,
        failed_node: WorkflowNode
    ) -> Optional[WorkflowNode]:
        """查找错误处理节点"""
        # 查找连接到失败节点的错误处理类型节点
        for edge in workflow.edges:
            if edge.source == failed_node.id:
                target_node = workflow.get_node(edge.target)
                if target_node and target_node.type == NodeType.ERROR:
                    return target_node
        return None
    
    # ==================== 辅助方法 ====================
    
    def _should_execute_node(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        execution_state: Dict
    ) -> bool:
        """检查节点是否应该执行"""
        # START节点总是执行
        if node.type == NodeType.START:
            return True
        
        # 获取指向此节点的边
        incoming_edges = workflow.get_incoming_edges(node.id)
        
        # 如果没有输入边，跳过（除了START节点）
        if not incoming_edges:
            return False
        
        # 获取前置节点的结果
        context = execution_state["context"]
        node_results = execution_state["node_results"]
        
        # 简化检查：如果有前置节点成功完成，则认为可以执行
        for edge in incoming_edges:
            if edge.source in node_results:
                return True
        
        # 检查边条件
        for edge in incoming_edges:
            if not edge.condition:
                continue
            
            # 评估边的条件
            source_result = node_results.get(edge.source, {})
            eval_context = {"__builtins__": __builtins__}
            eval_context.update(source_result)
            eval_context.update(context)
            
            try:
                if not eval(edge.condition, eval_context, {}):
                    return False
            except Exception as e:
                logger.warning(f"边条件评估失败: {e}")
        
        return True
    
    def _update_variables(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        result: Any,
        execution_state: Dict
    ):
        """更新执行上下文变量"""
        context = execution_state["context"]
        
        # 为节点输出创建变量名
        var_name = f"{node.name}_result"
        context[var_name] = result
        
        # 如果结果包含特定字段，也创建变量
        if isinstance(result, dict):
            for key, value in result.items():
                safe_key = key.replace(" ", "_").replace("-", "_")
                var_name = f"node_{safe_key}"
                if var_name not in context:
                    context[var_name] = value
        
        # 处理AGENT节点的响应
        if node.type == NodeType.AGENT and isinstance(result, dict):
            if "agent_response" in result:
                context["agent_response"] = result["agent_response"]
        
        # 更新工作流级别变量（如果节点配置了变量名）
        if hasattr(node.config, 'custom') and node.config.custom:
            var_output = node.config.custom.get("variable_output")
            if var_output:
                execution_state["variables"][var_output] = result
    
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
    
    def list_running_executions(self) -> List[Dict]:
        """列出所有运行中的执行"""
        return list(self._running_executions.values())
    
    def pause_execution(self, execution_id: str) -> bool:
        """暂停执行"""
        if execution_id in self._running_executions:
            self._running_executions[execution_id]["status"] = "paused"
            return True
        return False
    
    def resume_execution(self, execution_id: str) -> bool:
        """恢复执行"""
        if execution_id in self._running_executions:
            if self._running_executions[execution_id]["status"] == "paused":
                self._running_executions[execution_id]["status"] = "running"
                return True
        return False
    
    def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        if execution_id in self._running_executions:
            self._running_executions[execution_id]["status"] = "cancelled"
            return True
        return False
    
    def get_execution_history(
        self,
        workflow_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """获取工作流的执行历史"""
        workflow = self.engine.get_workflow(workflow_id)
        if not workflow:
            return []
        
        if workflow.last_execution_result:
            return [workflow.last_execution_result]
        return []