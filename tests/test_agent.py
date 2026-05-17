"""
SerpentAI 智能体核心测试
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch


class TestAgentConfig:
    """测试 AgentConfig"""
    
    def test_default_config(self):
        from backend.agent import AgentConfig
        
        config = AgentConfig()
        
        assert config.name == "Serpent"
        assert config.model == "gpt-4o"
        assert config.max_iterations == 10
        assert config.max_thinking_steps == 5
        assert config.temperature == 0.7
        assert config.timeout_seconds == 120
        assert config.enable_self_evolution == True
        assert config.mode.value == "auto"
    
    def test_custom_config(self):
        from backend.agent import AgentConfig, AgentMode
        
        config = AgentConfig(
            name="CustomAgent",
            model="claude-3",
            max_iterations=20,
            mode=AgentMode.ASSISTED
        )
        
        assert config.name == "CustomAgent"
        assert config.model == "claude-3"
        assert config.max_iterations == 20
        assert config.mode == AgentMode.ASSISTED


class TestSerpentAgent:
    """测试 SerpentAgent 主智能体"""
    
    def test_agent_initialization(self):
        from backend.agent import SerpentAgent, AgentConfig
        
        config = AgentConfig()
        agent = SerpentAgent(config)
        
        assert agent.config.name == "Serpent"
        assert agent.config.model == "gpt-4o"
        assert agent.reasoning_engine is not None
        assert agent.task_scheduler is not None
        assert agent.tool_coordinator is not None
        assert agent.self_evolution is not None
    
    def test_get_context(self):
        from backend.agent import SerpentAgent, ConversationContext
        
        agent = SerpentAgent()
        context = agent.get_context("test_session")
        
        assert isinstance(context, ConversationContext)
        assert context.session_id == "test_session"
    
    def test_context_isolation(self):
        from backend.agent import SerpentAgent
        
        agent = SerpentAgent()
        
        ctx1 = agent.get_context("session_1")
        ctx2 = agent.get_context("session_2")
        
        assert ctx1.session_id == "session_1"
        assert ctx2.session_id == "session_2"
        assert ctx1 != ctx2
    
    def test_reset_context(self):
        from backend.agent import SerpentAgent
        
        agent = SerpentAgent()
        agent.get_context("test_session")
        
        assert "test_session" in agent.contexts
        
        agent.reset_context("test_session")
        
        assert "test_session" not in agent.contexts
    
    def test_get_stats(self):
        from backend.agent import SerpentAgent
        
        agent = SerpentAgent()
        stats = agent.get_stats()
        
        assert "name" in stats
        assert "model" in stats
        assert "mode" in stats
        assert "active_sessions" in stats
        assert stats["name"] == "Serpent"


class TestReasoningEngine:
    """测试推理引擎"""
    
    def test_engine_initialization(self):
        from backend.agent import ReasoningEngine, AgentConfig
        
        config = AgentConfig()
        engine = ReasoningEngine(config)
        
        assert engine.config == config
        assert engine.max_steps == config.max_thinking_steps
    
    def test_format_tools(self):
        from backend.agent import ReasoningEngine, AgentConfig
        
        engine = ReasoningEngine(AgentConfig())
        
        tools = [
            {"name": "fs_read", "description": "Read a file", "parameters": {"path": {}}},
            {"name": "shell_exec", "description": "Execute shell", "parameters": {}}
        ]
        
        formatted = engine._format_tools(tools)
        
        assert "fs_read" in formatted
        assert "shell_exec" in formatted
        assert "Read a file" in formatted
    
    def test_format_empty_tools(self):
        from backend.agent import ReasoningEngine, AgentConfig
        
        engine = ReasoningEngine(AgentConfig())
        
        formatted = engine._format_tools([])
        
        assert "无可用工具" in formatted


class TestTaskScheduler:
    """测试任务调度器"""
    
    def test_scheduler_initialization(self):
        from backend.agent import TaskScheduler
        
        scheduler = TaskScheduler(max_concurrent=3)
        
        assert scheduler.max_concurrent == 3
        assert len(scheduler.tasks) == 0
        assert len(scheduler.task_queue) == 0
    
    def test_create_task(self):
        from backend.agent import TaskScheduler, TaskStatus
        
        scheduler = TaskScheduler()
        
        task_id = scheduler.create_task(
            description="Test task",
            priority=2
        )
        
        assert task_id is not None
        assert task_id in scheduler.tasks
        assert scheduler.tasks[task_id].description == "Test task"
        assert scheduler.tasks[task_id].priority == 2
        assert scheduler.tasks[task_id].status == TaskStatus.PENDING
    
    def test_get_task(self):
        from backend.agent import TaskScheduler
        
        scheduler = TaskScheduler()
        task_id = scheduler.create_task("Test task")
        
        task = scheduler.get_task(task_id)
        
        assert task is not None
        assert task.description == "Test task"
    
    def test_get_nonexistent_task(self):
        from backend.agent import TaskScheduler
        
        scheduler = TaskScheduler()
        
        task = scheduler.get_task("nonexistent")
        
        assert task is None
    
    def test_cancel_task(self):
        from backend.agent import TaskScheduler, TaskStatus
        
        scheduler = TaskScheduler()
        task_id = scheduler.create_task("Test task")
        
        success = scheduler.cancel_task(task_id)
        
        assert success == True
        assert scheduler.tasks[task_id].status == TaskStatus.CANCELLED
    
    def test_pause_resume_task(self):
        from backend.agent import TaskScheduler, TaskStatus
        
        scheduler = TaskScheduler()
        task_id = scheduler.create_task("Test task")
        
        # 模拟任务开始
        scheduler.tasks[task_id].status = TaskStatus.RUNNING
        scheduler.running_tasks[task_id] = scheduler.tasks[task_id]
        
        # 暂停
        success = scheduler.pause_task(task_id)
        assert success == True
        assert scheduler.tasks[task_id].status == TaskStatus.PAUSED
        
        # 恢复
        success = scheduler.resume_task(task_id)
        assert success == True
        assert scheduler.tasks[task_id].status == TaskStatus.PENDING
    
    def test_complete_task(self):
        from backend.agent import TaskScheduler, TaskStatus
        
        scheduler = TaskScheduler()
        task_id = scheduler.create_task("Test task")
        
        scheduler.complete_task(task_id, result={"done": True})
        
        assert scheduler.tasks[task_id].status == TaskStatus.COMPLETED
        assert scheduler.tasks[task_id].result == {"done": True}
        assert scheduler.tasks[task_id].progress == 1.0
    
    def test_update_progress(self):
        from backend.agent import TaskScheduler
        
        scheduler = TaskScheduler()
        task_id = scheduler.create_task("Test task")
        
        scheduler.update_progress(task_id, 0.5)
        
        assert scheduler.tasks[task_id].progress == 0.5
        
        # 测试边界
        scheduler.update_progress(task_id, 1.5)
        assert scheduler.tasks[task_id].progress == 1.0
        
        scheduler.update_progress(task_id, -0.5)
        assert scheduler.tasks[task_id].progress == 0.0
    
    def test_get_stats(self):
        from backend.agent import TaskScheduler
        
        scheduler = TaskScheduler()
        
        # 创建一些任务
        scheduler.create_task("Task 1", priority=1)
        scheduler.create_task("Task 2", priority=2)
        
        stats = scheduler.get_stats()
        
        assert "total_tasks" in stats
        assert stats["total_tasks"] == 2
        assert stats["pending_tasks"] == 2


class TestTask:
    """测试 Task 对象"""
    
    def test_task_creation(self):
        from backend.agent import Task, TaskStatus
        
        task = Task(id="test_1", description="Test task")
        
        assert task.id == "test_1"
        assert task.description == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == 3
        assert task.progress == 0.0
    
    def test_task_priority_ordering(self):
        from backend.agent import Task
        
        task1 = Task(id="t1", description="Task 1", priority=3)
        task2 = Task(id="t2", description="Task 2", priority=1)
        task3 = Task(id="t3", description="Task 3", priority=5)
        
        # 优先级队列排序（数字小的先出队）
        import heapq
        queue = [task1, task2, task3]
        heapq.heapify(queue)
        
        first = heapq.heappop(queue)
        assert first.id == "t2"  # priority=1 最高


class TestToolCoordinator:
    """测试工具协调器"""
    
    def test_coordinator_initialization(self):
        from backend.agent import ToolCoordinator
        
        coordinator = ToolCoordinator()
        
        assert coordinator.default_timeout == 30
        assert coordinator.max_retries == 2
        assert len(coordinator.cache) == 0
        assert len(coordinator.call_history) == 0
    
    def test_cache_key_generation(self):
        from backend.agent import ToolCoordinator
        
        coordinator = ToolCoordinator()
        
        key1 = coordinator._generate_cache_key("fs_read", {"path": "/test"})
        key2 = coordinator._generate_cache_key("fs_read", {"path": "/test"})
        key3 = coordinator._generate_cache_key("fs_read", {"path": "/other"})
        
        assert key1 == key2  # 相同参数
        assert key1 != key3  # 不同参数
    
    def test_is_cacheable(self):
        from backend.agent import ToolCoordinator
        
        coordinator = ToolCoordinator()
        
        assert coordinator._is_cacheable("fs_read") == True
        assert coordinator._is_cacheable("fs_exists") == True
        assert coordinator._is_cacheable("system_info") == True
        assert coordinator._is_cacheable("shell_exec") == False  # 不缓存写操作
    
    def test_clear_cache(self):
        from backend.agent import ToolCoordinator
        
        coordinator = ToolCoordinator()
        coordinator.cache["test"] = "value"
        
        coordinator.clear_cache()
        
        assert len(coordinator.cache) == 0
    
    def test_get_stats(self):
        from backend.agent import ToolCoordinator
        
        coordinator = ToolCoordinator()
        stats = coordinator.get_stats()
        
        assert "total_calls" in stats
        assert "successful_calls" in stats
        assert "cache_size" in stats
        assert stats["total_calls"] == 0


class TestSelfEvolution:
    """测试自进化系统"""
    
    def test_evolution_initialization(self):
        from backend.agent import SelfEvolution
        
        evolution = SelfEvolution()
        
        assert evolution.auto_fix == True
        assert evolution.auto_optimize == False
        assert evolution.learn_from_errors == True
        assert len(evolution.evolution_log) == 0
    
    def test_get_stats(self):
        from backend.agent import SelfEvolution
        
        evolution = SelfEvolution()
        stats = evolution.get_stats()
        
        assert "total_evolutions" in stats
        assert "fixes_applied" in stats
        assert "auto_fix_enabled" in stats


class TestMultiAgent:
    """测试多智能体协作"""
    
    def test_multi_agent_initialization(self):
        from backend.agent import MultiAgentCollaboration
        
        multi = MultiAgentCollaboration()
        
        assert len(multi.sub_agents) == 0
        assert multi.coordinator is None
        assert multi.max_parallel_agents == 5
    
    def test_register_agent(self):
        from backend.agent import MultiAgentCollaboration, AgentRole
        
        multi = MultiAgentCollaboration()
        
        agent_id = multi.register_agent(
            name="TestAgent",
            role=AgentRole.EXECUTOR,
            capabilities=["coding", "testing"]
        )
        
        assert agent_id in multi.sub_agents
        assert multi.sub_agents[agent_id].name == "TestAgent"
        assert multi.sub_agents[agent_id].role == AgentRole.EXECUTOR
    
    def test_register_coordinator(self):
        from backend.agent import MultiAgentCollaboration, AgentRole
        
        multi = MultiAgentCollaboration()
        
        # 注册第一个协调者
        coord_id = multi.register_agent(
            name="Coordinator",
            role=AgentRole.COORDINATOR,
            capabilities=["planning"]
        )
        
        assert multi.coordinator is not None
        assert multi.coordinator.id == coord_id
        
        # 注册另一个协调者（第一个保留）
        coord_id2 = multi.register_agent(
            name="Coordinator2",
            role=AgentRole.COORDINATOR,
            capabilities=["planning"]
        )
        
        # 第一个协调者保持不变
        assert multi.coordinator.id == coord_id
        # 第二个协调者也被注册了
        assert coord_id2 in multi.sub_agents
        assert multi.sub_agents[coord_id2].name == "Coordinator2"
    
    def test_list_agents(self):
        from backend.agent import MultiAgentCollaboration, AgentRole
        
        multi = MultiAgentCollaboration()
        
        multi.register_agent("Agent1", AgentRole.EXECUTOR)
        multi.register_agent("Agent2", AgentRole.PLANNER)
        multi.register_agent("Agent3", AgentRole.EXECUTOR)
        
        all_agents = multi.list_agents()
        executors = multi.list_agents(AgentRole.EXECUTOR)
        
        assert len(all_agents) == 3
        assert len(executors) == 2
    
    def test_create_default_team(self):
        from backend.agent import MultiAgentCollaboration, AgentRole
        
        multi = MultiAgentCollaboration()
        agent_ids = multi.create_default_team()
        
        assert len(agent_ids) == 3  # Coordinator + Executor + Critic
        
        agents = multi.list_agents()
        roles = {a.role for a in agents}
        
        assert AgentRole.COORDINATOR in roles
        assert AgentRole.EXECUTOR in roles
        assert AgentRole.CRITIC in roles
    
    def test_get_team_stats(self):
        from backend.agent import MultiAgentCollaboration
        
        multi = MultiAgentCollaboration()
        multi.create_default_team()
        
        stats = multi.get_team_stats()
        
        assert stats["total_agents"] == 3
        assert "busy_agents" in stats
        assert "idle_agents" in stats
        assert "roles" in stats
