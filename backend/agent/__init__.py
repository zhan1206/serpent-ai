"""
SerpentAI Agent Core - 智能体核心模块
包含主智能体、推理引擎、任务调度器、工具协调器、自进化系统、多智能体协作
"""

from .agent import SerpentAgent, AgentConfig, AgentMode, ConversationContext
from .reasoning_engine import ReasoningEngine, ReasoningResult, ActionType
from .task_scheduler import TaskScheduler, Task, TaskStatus, TaskPriority
from .tool_coordinator import ToolCoordinator, ToolCallResult
from .self_evolution import SelfEvolution, EvolutionResult
from .multi_agent import MultiAgentCollaboration, SubAgent, AgentRole, CollaborationResult

__all__ = [
    # 主智能体
    "SerpentAgent",
    "AgentConfig",
    "AgentMode",
    "ConversationContext",
    
    # 推理引擎
    "ReasoningEngine",
    "ReasoningResult",
    "ActionType",
    
    # 任务调度
    "TaskScheduler",
    "Task",
    "TaskStatus",
    "TaskPriority",
    
    # 工具协调
    "ToolCoordinator",
    "ToolCallResult",
    
    # 自进化
    "SelfEvolution",
    "EvolutionResult",
    
    # 多智能体
    "MultiAgentCollaboration",
    "SubAgent",
    "AgentRole",
    "CollaborationResult",
]


# 全局实例
_agent_instance = None
_multi_agent_instance = None


def get_agent(config: "AgentConfig" = None) -> "SerpentAgent":
    """获取全局智能体实例（单例）"""
    global _agent_instance
    if _agent_instance is None:
        if config is None:
            config = AgentConfig()
        _agent_instance = SerpentAgent(config)
    return _agent_instance


def get_multi_agent() -> "MultiAgentCollaboration":
    """获取全局多智能体协作实例（单例）"""
    global _multi_agent_instance
    if _multi_agent_instance is None:
        _multi_agent_instance = MultiAgentCollaboration()
    return _multi_agent_instance
