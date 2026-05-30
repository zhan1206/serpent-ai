"""
SerpentAI 主智能体核心
实现自主推理、决策、执行、反馈的智能体循环
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import json

from .reasoning_engine import ReasoningEngine, ReasoningResult
from .task_scheduler import TaskScheduler, Task, TaskStatus
from .tool_coordinator import ToolCoordinator, ToolCallResult
from .self_evolution import SelfEvolution, EvolutionResult

from backend.models.base_model import Message, create_adapter
from backend.memory import get_memory_manager

logger = logging.getLogger(__name__)


class AgentMode(Enum):
    """智能体运行模式"""
    AUTO = "auto"           # 完全自主推理
    ASSISTED = "assisted"  # 辅助模式，需要用户确认
    LEARN = "learn"        # 学习模式，记录所有决策


@dataclass
class AgentConfig:
    """智能体配置"""
    name: str = "Serpent"
    model: str = "gpt-4o"
    max_iterations: int = 10
    max_thinking_steps: int = 5
    temperature: float = 0.7
    timeout_seconds: int = 120
    enable_self_evolution: bool = True
    enable_tool_learning: bool = True
    mode: AgentMode = AgentMode.AUTO
    system_prompt: str = """你是一个名为 Serpent 的 AI 智能体。
你有以下核心能力：
1. 记忆系统：可以记住对话内容和重要信息
2. 工具系统：可以使用各种工具来完成复杂任务
3. 自进化：可以从错误中学习，不断优化自己

你的目标是：
- 准确理解用户意图
- 高效完成任务
- 持续学习和改进
- 保持诚实和透明

当你不确定时，承认不确定性并寻求帮助。"""


@dataclass
class ConversationContext:
    """对话上下文"""
    session_id: str
    messages: List[Message] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    reasoning_history: List[ReasoningResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SerpentAgent:
    """
    SerpentAI 主智能体
    
    实现 ReAct (Reasoning + Acting) 范式：
    1. 思考 (Think): 分析当前状态，决定下一步行动
    2. 行动 (Act): 执行工具调用或生成响应
    3. 观察 (Observe): 获取行动结果，更新状态
    4. 反思 (Reflect): 评估结果，决定是否继续或结束
    """
    
    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.reasoning_engine = ReasoningEngine(self.config)
        self.task_scheduler = TaskScheduler()
        self.tool_coordinator = ToolCoordinator()
        self.self_evolution = SelfEvolution()
        self.memory_manager = get_memory_manager()
        
        # 会话上下文缓存
        self.contexts: Dict[str, ConversationContext] = {}
        
        # 回调函数
        self.callbacks: Dict[str, Callable] = {}
        
        logger.info(f"SerpentAgent 初始化完成 | 模型: {self.config.model} | 模式: {self.config.mode.value}")
    
    def get_context(self, session_id: str) -> ConversationContext:
        """获取或创建会话上下文"""
        if session_id not in self.contexts:
            self.contexts[session_id] = ConversationContext(session_id=session_id)
        return self.contexts[session_id]
    
    async def think(self, session_id: str) -> ReasoningResult:
        """思考阶段：分析当前状态，决定下一步"""
        context = self.get_context(session_id)
        
        # 构建思考上下文
        context_prompt = self._build_context_prompt(context)
        
        # 调用推理引擎
        reasoning = await self.reasoning_engine.reason(
            context_prompt=context_prompt,
            max_steps=self.config.max_thinking_steps
        )
        
        context.reasoning_history.append(reasoning)
        return reasoning
    
    def _build_context_prompt(self, context: ConversationContext) -> str:
        """构建上下文提示词"""
        parts = []
        
        # 当前任务状态
        if context.tasks:
            parts.append("【当前任务】")
            for task in context.tasks:
                if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                    parts.append(f"- {task.id}: {task.description} ({task.status.value})")
        
        # 最近的工具调用
        if context.tools_used:
            parts.append(f"\n【最近使用的工具】: {', '.join(context.tools_used[-5:])}")
        
        # 待完成的任务列表
        pending_tasks = [t for t in context.tasks if t.status == TaskStatus.PENDING]
        if pending_tasks:
            parts.append(f"\n【待完成任务】: {len(pending_tasks)} 个")
        
        return "\n".join(parts) if parts else "无特殊上下文"
    
    async def act(self, session_id: str, reasoning: ReasoningResult) -> ToolCallResult:
        """行动阶段：根据推理结果执行工具或生成响应"""
        context = self.get_context(session_id)
        
        if reasoning.action_type == "tool":
            # 执行工具调用
            result = await self.tool_coordinator.execute(
                tool_name=reasoning.tool_name,
                arguments=reasoning.arguments,
                session_id=session_id
            )
            
            # 记录使用的工具
            if reasoning.tool_name:
                context.tools_used.append(reasoning.tool_name)
            
            return result
        
        elif reasoning.action_type == "response":
            # 生成文本响应
            return ToolCallResult(
                success=True,
                tool_name="response",
                result={"content": reasoning.response_content}
            )
        
        elif reasoning.action_type == "task":
            # 创建/更新任务
            if reasoning.task_action == "create":
                task = Task(
                    id=self._generate_id(),
                    description=reasoning.task_description,
                    priority=reasoning.task_priority or 5
                )
                self.task_scheduler.add_task(task)
                context.tasks.append(task)
            elif reasoning.task_action == "complete":
                task = self.task_scheduler.get_task(reasoning.task_id)
                if task:
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now()
            
            return ToolCallResult(
                success=True,
                tool_name="task_manager",
                result={"action": reasoning.task_action, "task_id": reasoning.task_id}
            )
        
        return ToolCallResult(success=False, tool_name="unknown", result={"error": "Unknown action type"})
    
    async def observe(self, session_id: str, result: ToolCallResult) -> Dict[str, Any]:
        """观察阶段：处理行动结果"""
        context = self.get_context(session_id)
        
        observation = {
            "success": result.success,
            "tool_name": result.tool_name,
            "result": result.result,
            "error": result.error,
            "execution_time": result.execution_time
        }
        
        # 如果失败且启用自进化，记录错误
        if not result.success and self.config.enable_self_evolution:
            await self._learn_from_error(session_id, result)
        
        return observation
    
    async def reflect(self, session_id: str, observation: Dict[str, Any], 
                      iteration: int) -> bool:
        """反思阶段：评估结果，决定是否继续"""
        context = self.get_context(session_id)
        
        # 检查是否达到最大迭代次数
        if iteration >= self.config.max_iterations:
            logger.warning(f"达到最大迭代次数 {self.config.max_iterations}")
            return False
        
        # 检查是否成功完成任务
        # success=True + tool_name="response" → Agent 已返回最终响应，停止推理
        if observation.get("success") and observation.get("tool_name") == "response":
            return False
        # 工具调用失败 → 让 Agent 感知失败并做决策，不静默吞掉
        if observation.get("tool_name") and observation.get("tool_name") != "response":
            if not observation.get("success"):
                logger.warning(f"工具调用失败 | tool={observation.get('tool_name')} | "
                               f"error={observation.get('error', 'unknown')}")
                return False  # 让 Agent 重试或选择其他工具

        # 检查是否有未完成的任务
        pending_tasks = [t for t in context.tasks if t.status == TaskStatus.PENDING]
        if not pending_tasks:
            return False
        
        return True
    
    async def run(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """
        运行智能体主循环 (ReAct 范式)
        
        Args:
            session_id: 会话 ID
            user_message: 用户消息
        
        Returns:
            Dict 包含:
                - response: 智能体响应
                - iterations: 迭代次数
                - tools_used: 使用的工具列表
                - tasks: 任务状态
        """
        context = self.get_context(session_id)
        
        # 添加用户消息到上下文
        context.messages.append(Message(role="user", content=user_message))
        
        # 保存到记忆系统
        self.memory_manager.add_message(session_id, Message(role="user", content=user_message))
        
        logger.info(f"智能体开始处理 | session: {session_id} | 消息长度: {len(user_message)}")
        
        # ReAct 主循环
        iterations = 0
        final_response = None
        
        while iterations < self.config.max_iterations:
            iterations += 1
            logger.debug(f"智能体迭代 {iterations}/{self.config.max_iterations}")
            
            # 1. 思考
            reasoning = await self.think(session_id)
            
            # 2. 行动
            result = await self.act(session_id, reasoning)
            
            # 3. 观察
            observation = await self.observe(session_id, result)
            
            # 4. 反思
            should_continue = await self.reflect(session_id, observation, iterations)
            
            if not should_continue:
                if reasoning.action_type == "response":
                    final_response = reasoning.response_content
                break
            
            # 添加观察结果到消息历史
            context.messages.append(Message(
                role="system",
                content=f"观察: {json.dumps(observation, ensure_ascii=False)}"
            ))
        
        # 如果没有生成响应，使用默认响应
        if final_response is None:
            final_response = "我需要更多时间来处理这个请求。"
        
        # 添加助手响应到上下文和记忆
        context.messages.append(Message(role="assistant", content=final_response))
        self.memory_manager.add_message(session_id, Message(role="assistant", content=final_response))
        
        logger.info(f"智能体处理完成 | session: {session_id} | 迭代: {iterations}")
        
        return {
            "response": final_response,
            "iterations": iterations,
            "tools_used": context.tools_used,
            "tasks": [{"id": t.id, "description": t.description, "status": t.status.value} 
                      for t in context.tasks],
            "session_id": session_id
        }
    
    async def _learn_from_error(self, session_id: str, error: ToolCallResult):
        """从错误中学习"""
        try:
            evolution = await self.self_evolution.analyze_and_fix(
                tool_name=error.tool_name,
                error_message=error.error,
                context=error.result
            )
            
            if evolution.fixed:
                logger.info(f"从错误中学习成功 | 工具: {error.tool_name} | 修复: {evolution.fix_description}")
            else:
                logger.debug(f"分析错误 | 工具: {error.tool_name} | 建议: {evolution.suggestion}")
        except Exception as e:
            logger.error(f"自进化学习失败: {e}")
    
    def _generate_id(self) -> str:
        """生成唯一 ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def register_callback(self, event: str, callback: Callable):
        """注册事件回调"""
        self.callbacks[event] = callback
    
    async def trigger_callback(self, event: str, *args, **kwargs):
        """触发事件回调"""
        if event in self.callbacks:
            try:
                await self.callbacks[event](*args, **kwargs)
            except Exception as e:
                logger.error(f"回调执行失败 | 事件: {event} | 错误: {e}")
    
    def reset_context(self, session_id: str):
        """重置会话上下文"""
        if session_id in self.contexts:
            del self.contexts[session_id]
        self.task_scheduler.clear_session(session_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取智能体统计信息"""
        total_tasks = len(self.task_scheduler.tasks)
        completed_tasks = len([t for t in self.task_scheduler.tasks if t.status == TaskStatus.COMPLETED])
        
        return {
            "name": self.config.name,
            "model": self.config.model,
            "mode": self.config.mode.value,
            "active_sessions": len(self.contexts),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "self_evolution_enabled": self.config.enable_self_evolution,
            "config": {
                "max_iterations": self.config.max_iterations,
                "max_thinking_steps": self.config.max_thinking_steps,
                "temperature": self.config.temperature
            }
        }
