"""
SerpentAI 任务调度器
管理和调度智能体的任务
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import heapq
import uuid

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"     # 等待执行
    RUNNING = "running"     # 执行中
    COMPLETED = "completed" # 已完成
    FAILED = "failed"       # 执行失败
    CANCELLED = "cancelled" # 已取消
    PAUSED = "paused"       # 已暂停


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 1  # 最高优先级
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5  # 最低优先级


@dataclass
class Task:
    """任务对象"""
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 3  # 1-5, 1 最高
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parent_id: Optional[str] = None  # 父任务 ID
    subtasks: List[str] = field(default_factory=list)  # 子任务 ID 列表
    metadata: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: float = 0.0  # 0.0 - 1.0
    retry_count: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        """支持优先级队列排序"""
        return self.priority < other.priority
    
    @property
    def is_finished(self) -> bool:
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at:
            end = self.completed_at or datetime.now()
            return (end - self.started_at).total_seconds()
        return None


class TaskScheduler:
    """
    任务调度器
    
    功能：
    1. 任务创建、调度、执行
    2. 优先级队列管理
    3. 任务依赖管理
    4. 进度跟踪
    5. 重试机制
    """
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[Task] = []  # 优先级队列
        self.running_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        
        # 回调函数
        self.on_task_start: Optional[Callable] = None
        self.on_task_complete: Optional[Callable] = None
        self.on_task_fail: Optional[Callable] = None
        self.on_task_progress: Optional[Callable] = None
        
        # 调度锁
        self._lock = asyncio.Lock()
        
        # 调度循环
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
    
    def add_task(self, task: Task) -> str:
        """添加任务"""
        self.tasks[task.id] = task
        heapq.heappush(self.task_queue, task)
        logger.info(f"任务添加 | ID: {task.id} | 优先级: {task.priority} | 描述: {task.description[:50]}")
        return task.id
    
    def create_task(
        self,
        description: str,
        priority: int = 3,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """创建并添加任务"""
        task = Task(
            id=str(uuid.uuid4())[:8],
            description=description,
            priority=priority,
            parent_id=parent_id,
            metadata=metadata or {}
        )
        
        if parent_id and parent_id in self.tasks:
            self.tasks[parent_id].subtasks.append(task.id)
        
        return self.add_task(task)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_pending_tasks(self) -> List[Task]:
        """获取所有待执行任务（按优先级排序）"""
        return sorted(
            [t for t in self.tasks.values() if t.status == TaskStatus.PENDING],
            key=lambda x: x.priority
        )
    
    def get_running_tasks(self) -> List[Task]:
        """获取正在执行的任务"""
        return list(self.running_tasks.values())
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        if task.status == TaskStatus.RUNNING:
            return False  # 无法取消正在运行的任务
        
        task.status = TaskStatus.CANCELLED
        logger.info(f"任务取消 | ID: {task_id}")
        return True
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        task = self.get_task(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False
        
        task.status = TaskStatus.PAUSED
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
        
        logger.info(f"任务暂停 | ID: {task_id}")
        return True
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        task = self.get_task(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            return False
        
        task.status = TaskStatus.PENDING
        heapq.heappush(self.task_queue, task)
        
        logger.info(f"任务恢复 | ID: {task_id}")
        return True
    
    def update_progress(self, task_id: str, progress: float) -> bool:
        """更新任务进度"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.progress = max(0.0, min(1.0, progress))
        
        if self.on_task_progress:
            try:
                self.on_task_progress(task)
            except Exception as e:
                logger.error(f"进度回调失败: {e}")
        
        return True
    
    def complete_task(self, task_id: str, result: Any = None) -> bool:
        """完成任务"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.progress = 1.0
        task.result = result
        
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
        
        self.completed_tasks[task_id] = task
        
        # 检查父任务进度
        if task.parent_id:
            self._update_parent_progress(task.parent_id)
        
        logger.info(f"任务完成 | ID: {task_id} | 耗时: {task.duration_seconds:.2f}s" if task.duration_seconds is not None else f"任务完成 | ID: {task_id}")
        
        if self.on_task_complete:
            try:
                self.on_task_complete(task)
            except Exception as e:
                logger.error(f"完成回调失败: {e}")
        
        return True
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """标记任务失败"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.error = error
        task.retry_count += 1
        
        if task.retry_count < task.max_retries:
            # 重试
            task.status = TaskStatus.PENDING
            heapq.heappush(self.task_queue, task)
            logger.warning(f"任务重试 | ID: {task_id} | 重试次数: {task.retry_count}")
            return True
        
        # 达到最大重试次数
        task.status = TaskStatus.FAILED
        task.completed_at = datetime.now()
        
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
        
        logger.error(f"任务失败 | ID: {task_id} | 错误: {error}")
        
        if self.on_task_fail:
            try:
                self.on_task_fail(task)
            except Exception as e:
                logger.error(f"失败回调失败: {e}")
        
        return True
    
    def _update_parent_progress(self, parent_id: str):
        """更新父任务进度"""
        parent = self.get_task(parent_id)
        if not parent or not parent.subtasks:
            return
        
        completed = 0
        for subtask_id in parent.subtasks:
            subtask = self.get_task(subtask_id)
            if subtask and subtask.is_finished:
                completed += 1
        
        parent.progress = completed / len(parent.subtasks)
        
        if parent.progress >= 1.0:
            self.complete_task(parent_id)
    
    def clear_session(self, session_id: str):
        """清空会话相关的任务"""
        tasks_to_remove = [
            task_id for task_id, task in self.tasks.items()
            if task.metadata.get("session_id") == session_id
        ]
        
        for task_id in tasks_to_remove:
            self.cancel_task(task_id)
            del self.tasks[task_id]
        
        logger.info(f"清空会话任务 | session: {session_id} | 数量: {len(tasks_to_remove)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        return {
            "total_tasks": len(self.tasks),
            "pending_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED]),
            "queue_size": len(self.task_queue),
            "max_concurrent": self.max_concurrent
        }
    
    async def start(self):
        """启动调度循环"""
        if self._running:
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._schedule_loop())
        logger.info("任务调度器已启动")
    
    async def stop(self):
        """停止调度循环"""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("任务调度器已停止")
    
    async def _schedule_loop(self):
        """调度循环"""
        while self._running:
            try:
                await self._schedule_tasks()
                await asyncio.sleep(0.1)  # 避免过度占用 CPU
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"调度循环错误: {e}")
                await asyncio.sleep(1)
    
    async def _schedule_tasks(self):
        """调度待执行的任务"""
        async with self._lock:
            # 检查是否可以启动新任务
            available_slots = self.max_concurrent - len(self.running_tasks)
            
            while available_slots > 0 and self.task_queue:
                # 取出最高优先级任务
                task = heapq.heappop(self.task_queue)
                
                # 检查任务是否仍然有效
                if task.status != TaskStatus.PENDING:
                    continue
                
                # 检查依赖是否完成
                if task.parent_id:
                    parent = self.get_task(task.parent_id)
                    if parent and not parent.is_finished:
                        # 父任务未完成，放回队列
                        heapq.heappush(self.task_queue, task)
                        continue
                
                # 启动任务
                await self._start_task(task)
                available_slots -= 1
    
    async def _start_task(self, task: Task):
        """启动任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.running_tasks[task.id] = task
        
        logger.info(f"任务启动 | ID: {task.id}")
        
        if self.on_task_start:
            try:
                self.on_task_start(task)
            except Exception as e:
                logger.error(f"启动回调失败: {e}")
