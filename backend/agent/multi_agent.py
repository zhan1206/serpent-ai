"""
SerpentAI 多智能体协作系统
支持多个子智能体协同工作
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from .agent import SerpentAgent, AgentConfig, AgentMode
from .task_scheduler import TaskScheduler, Task, TaskStatus

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """智能体角色"""
    COORDINATOR = "coordinator"   # 协调者
    EXECUTOR = "executor"         # 执行者
    PLANNER = "planner"           # 规划者
    RESEARCHER = "researcher"     # 研究者
    CRITIC = "critic"             # 评论者
    REPORTER = "reporter"         # 报告者


@dataclass
class SubAgent:
    """子智能体"""
    id: str
    name: str
    role: AgentRole
    agent: SerpentAgent
    capabilities: List[str] = field(default_factory=list)
    status: str = "idle"  # idle, busy, offline
    tasks_completed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollaborationResult:
    """协作结果"""
    success: bool
    task_id: str
    sub_results: Dict[str, Any] = field(default_factory=dict)
    final_result: Optional[Any] = None
    duration: float = 0.0
    errors: List[str] = field(default_factory=list)


class MultiAgentCollaboration:
    """
    多智能体协作系统
    
    功能：
    1. 子智能体注册和管理
    2. 任务分解和分配
    3. 智能体间通信
    4. 结果汇总和协调
    5. 协作模式：并行、串行、投票、流水线
    """
    
    def __init__(self):
        self.sub_agents: Dict[str, SubAgent] = {}
        self.task_scheduler = TaskScheduler()
        self.coordinator: Optional[SubAgent] = None
        
        # 协作配置
        self.max_parallel_agents = 5
        self.result_aggregation = "last"  # last, vote, merge
        
        # 回调函数
        self.on_agent_start: Optional[Callable] = None
        self.on_agent_complete: Optional[Callable] = None
        self.on_collaboration_progress: Optional[Callable] = None
        
        logger.info("多智能体协作系统初始化完成")
    
    def register_agent(
        self,
        name: str,
        role: AgentRole,
        capabilities: List[str] = None,
        config: AgentConfig = None
    ) -> str:
        """
        注册子智能体
        
        Args:
            name: 智能体名称
            role: 智能体角色
            capabilities: 智能体能力列表
            config: 智能体配置
        
        Returns:
            str: 智能体 ID
        """
        agent_id = str(uuid.uuid4())[:8]
        
        # 创建智能体实例
        if config is None:
            config = AgentConfig(name=name)
        
        agent = SerpentAgent(config)
        
        sub_agent = SubAgent(
            id=agent_id,
            name=name,
            role=role,
            agent=agent,
            capabilities=capabilities or []
        )
        
        self.sub_agents[agent_id] = sub_agent
        
        # 如果是协调者角色，设置为主协调者
        if role == AgentRole.COORDINATOR and self.coordinator is None:
            self.coordinator = sub_agent
        
        logger.info(f"子智能体注册 | ID: {agent_id} | 名称: {name} | 角色: {role.value}")
        
        return agent_id
    
    def get_agent(self, agent_id: str) -> Optional[SubAgent]:
        """获取子智能体"""
        return self.sub_agents.get(agent_id)
    
    def list_agents(self, role: AgentRole = None) -> List[SubAgent]:
        """列出智能体"""
        agents = list(self.sub_agents.values())
        if role:
            agents = [a for a in agents if a.role == role]
        return agents
    
    async def collaborate(
        self,
        task: str,
        mode: str = "parallel",
        agent_ids: List[str] = None
    ) -> CollaborationResult:
        """
        多智能体协作
        
        Args:
            task: 协作任务描述
            mode: 协作模式
                - parallel: 并行执行
                - sequential: 串行执行
                - vote: 投票决策
                - pipeline: 流水线处理
            agent_ids: 指定参与的智能体 ID 列表
        
        Returns:
            CollaborationResult: 协作结果
        """
        start_time = datetime.now()
        task_id = str(uuid.uuid4())[:8]
        
        logger.info(f"多智能体协作开始 | 任务: {task[:50]}... | 模式: {mode}")
        
        # 获取参与智能体
        if agent_ids:
            agents = [self.sub_agents[aid] for aid in agent_ids if aid in self.sub_agents]
        else:
            agents = list(self.sub_agents.values())
        
        if not agents:
            return CollaborationResult(
                success=False,
                task_id=task_id,
                errors=["没有可用的智能体"]
            )
        
        # 根据模式执行协作
        if mode == "parallel":
            result = await self._parallel_execution(task, agents)
        elif mode == "sequential":
            result = await self._sequential_execution(task, agents)
        elif mode == "vote":
            result = await self._vote_execution(task, agents)
        elif mode == "pipeline":
            result = await self._pipeline_execution(task, agents)
        else:
            result = await self._parallel_execution(task, agents)
        
        result.task_id = task_id
        result.duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"多智能体协作完成 | 任务ID: {task_id} | 耗时: {result.duration:.2f}s")
        
        return result
    
    async def _parallel_execution(
        self,
        task: str,
        agents: List[SubAgent]
    ) -> CollaborationResult:
        """并行执行"""
        sub_results = {}
        errors = []
        
        # 限制并行数量
        agents = agents[:self.max_parallel_agents]
        
        # 并行执行所有智能体
        tasks = []
        for agent in agents:
            tasks.append(self._execute_agent_task(agent, task))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for agent, result in zip(agents, results):
            if isinstance(result, Exception):
                errors.append(f"{agent.name}: {str(result)}")
                sub_results[agent.id] = {"error": str(result)}
            else:
                sub_results[agent.id] = result
                agent.tasks_completed += 1
        
        # 汇总结果
        final_result = self._aggregate_results(sub_results)
        
        return CollaborationResult(
            success=len(errors) == 0,
            task_id="",
            sub_results=sub_results,
            final_result=final_result,
            duration=0.0,
            errors=errors
        )
    
    async def _sequential_execution(
        self,
        task: str,
        agents: List[SubAgent]
    ) -> CollaborationResult:
        """串行执行"""
        sub_results = {}
        errors = []
        context = task
        
        for agent in agents:
            try:
                result = await agent.agent.run(
                    session_id=f"multi_agent_{agent.id}",
                    user_message=f"基于以下上下文完成任务：\n{context}\n\n任务：{task}"
                )
                
                sub_results[agent.id] = result
                agent.tasks_completed += 1
                
                # 将结果作为上下文传递给下一个智能体
                context = result.get("response", "")
                
                # 进度回调
                if self.on_collaboration_progress:
                    self.on_collaboration_progress(agent, result)
                
            except Exception as e:
                errors.append(f"{agent.name}: {str(e)}")
                sub_results[agent.id] = {"error": str(e)}
        
        return CollaborationResult(
            success=len(errors) == 0,
            task_id="",
            sub_results=sub_results,
            final_result=context,
            duration=0.0,
            errors=errors
        )
    
    async def _vote_execution(
        self,
        task: str,
        agents: List[SubAgent]
    ) -> CollaborationResult:
        """投票决策"""
        # 先并行收集各智能体的意见
        parallel_result = await self._parallel_execution(task, agents)
        
        # 汇总意见
        votes = {}
        for agent_id, result in parallel_result.sub_results.items():
            response = result.get("response", "")
            # 简单统计（实际应该用 NLP 分析）
            if response not in votes:
                votes[response] = []
            votes[response].append(agent_id)
        
        # 多数票
        winner = max(votes.items(), key=lambda x: len(x[1]))
        final_result = {
            "winner": winner[0],
            "votes": {k: len(v) for k, v in votes.items()},
            "details": parallel_result.sub_results
        }
        
        return CollaborationResult(
            success=True,
            task_id="",
            sub_results=parallel_result.sub_results,
            final_result=final_result,
            duration=0.0,
            errors=parallel_result.errors
        )
    
    async def _pipeline_execution(
        self,
        task: str,
        agents: List[SubAgent]
    ) -> CollaborationResult:
        """流水线执行（每个智能体处理一个阶段）"""
        # 定义流水线阶段
        stages = [
            ("分解任务", AgentRole.PLANNER),
            ("研究", AgentRole.RESEARCHER),
            ("执行", AgentRole.EXECUTOR),
            ("评审", AgentRole.CRITIC),
            ("报告", AgentRole.REPORTER),
        ]
        
        current_task = task
        sub_results = {}
        
        for stage_name, stage_role in stages:
            # 找到对应角色的智能体
            stage_agents = [a for a in agents if a.role == stage_role]
            
            if not stage_agents:
                continue
            
            # 使用第一个匹配的智能体
            agent = stage_agents[0]
            
            try:
                result = await agent.agent.run(
                    session_id=f"pipeline_{agent.id}",
                    user_message=f"【{stage_name}】{current_task}"
                )
                
                sub_results[stage_name] = {
                    "agent": agent.name,
                    "result": result
                }
                
                current_task = result.get("response", "")
                agent.tasks_completed += 1
                
            except Exception as e:
                sub_results[stage_name] = {"error": str(e)}
        
        return CollaborationResult(
            success=True,
            task_id="",
            sub_results=sub_results,
            final_result=current_task,
            duration=0.0,
            errors=[]
        )
    
    async def _execute_agent_task(
        self,
        agent: SubAgent,
        task: str
    ) -> Dict[str, Any]:
        """执行单个智能体任务"""
        agent.status = "busy"
        
        if self.on_agent_start:
            self.on_agent_start(agent)
        
        try:
            result = await agent.agent.run(
                session_id=f"multi_agent_{agent.id}",
                user_message=task
            )
            
            agent.status = "idle"
            
            if self.on_agent_complete:
                self.on_agent_complete(agent, result)
            
            return result
        
        except Exception as e:
            agent.status = "idle"
            raise
    
    def _aggregate_results(self, sub_results: Dict[str, Any]) -> Any:
        """汇总结果"""
        if self.result_aggregation == "last":
            # 返回最后一个结果
            return list(sub_results.values())[-1] if sub_results else None
        
        elif self.result_aggregation == "merge":
            # 合并所有结果
            return {"combined_results": list(sub_results.values())}
        
        elif self.result_aggregation == "vote":
            # 投票结果
            return sub_results
        
        return sub_results
    
    def create_default_team(self) -> List[str]:
        """创建默认团队（协调者 + 执行者 + 评论者）"""
        agent_ids = []
        
        # 协调者
        coordinator_id = self.register_agent(
            name="Coordinator",
            role=AgentRole.COORDINATOR,
            capabilities=["task_planning", "resource_allocation", "result_aggregation"]
        )
        agent_ids.append(coordinator_id)
        
        # 执行者
        executor_id = self.register_agent(
            name="Executor",
            role=AgentRole.EXECUTOR,
            capabilities=["code_execution", "tool_usage", "problem_solving"]
        )
        agent_ids.append(executor_id)
        
        # 评论者
        critic_id = self.register_agent(
            name="Critic",
            role=AgentRole.CRITIC,
            capabilities=["quality_check", "error_detection", "improvement_suggestion"]
        )
        agent_ids.append(critic_id)
        
        logger.info(f"默认团队创建完成 | 成员数: {len(agent_ids)}")
        
        return agent_ids
    
    def get_team_stats(self) -> Dict[str, Any]:
        """获取团队统计"""
        return {
            "total_agents": len(self.sub_agents),
            "busy_agents": sum(1 for a in self.sub_agents.values() if a.status == "busy"),
            "idle_agents": sum(1 for a in self.sub_agents.values() if a.status == "idle"),
            "roles": {
                role.value: len([a for a in self.sub_agents.values() if a.role == role])
                for role in AgentRole
            },
            "total_tasks_completed": sum(a.tasks_completed for a in self.sub_agents.values())
        }
