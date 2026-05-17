"""
SerpentAI 工作流调度器
定时任务和事件驱动的工作流调度
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import threading
import time

from .engine import WorkflowEngine, Workflow, WorkflowStatus

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """触发器类型"""
    CRON = "cron"           # Cron表达式
    INTERVAL = "interval"   # 固定间隔
    WEBHOOK = "webhook"     # Webhook触发
    EVENT = "event"         # 事件触发


class WorkflowScheduler:
    """
    工作流调度器
    功能：
    1. Cron定时调度
    2. 固定间隔调度
    3. Webhook触发
    4. 事件触发
    """
    
    def __init__(self, engine: WorkflowEngine):
        self.engine = engine
        
        # 调度任务: task_id -> task_info
        self._tasks: Dict[str, Dict] = {}
        
        # 调度线程
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        
        # Webhook回调
        self._webhook_handlers: Dict[str, Callable] = {}
        
        # 事件监听器
        self._event_listeners: Dict[str, List[Callable]] = {}
        
        # 执行器
        from .executor import WorkflowExecutor
        self._executor = WorkflowExecutor(engine)
        
        logger.info("工作流调度器初始化完成")
    
    def start(self):
        """启动调度器"""
        if self._running:
            return
        
        self._running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        logger.info("工作流调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("工作流调度器已停止")
    
    def _scheduler_loop(self):
        """调度循环"""
        while self._running:
            try:
                now = datetime.now()
                
                for task_id, task in self._tasks.items():
                    if not task.get("enabled", True):
                        continue
                    
                    # 检查是否应该执行
                    if self._should_execute(now, task):
                        # 执行工作流
                        self._execute_scheduled_task(task_id, task)
                        
                        # 更新下次执行时间
                        if task["trigger_type"] == TriggerType.CRON:
                            task["last_run"] = now
                            task["next_run"] = self._calculate_next_cron(
                                task["cron_expression"],
                                now
                            )
                        elif task["trigger_type"] == TriggerType.INTERVAL:
                            task["last_run"] = now
                            task["next_run"] = now + timedelta(seconds=task["interval_seconds"])
                
                # 每秒检查一次
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"调度循环出错: {e}")
                time.sleep(5)
    
    def _should_execute(self, now: datetime, task: Dict) -> bool:
        """检查任务是否应该执行"""
        if not task.get("enabled", True):
            return False
        
        next_run = task.get("next_run")
        if not next_run:
            return True
        
        return now >= next_run
    
    def _calculate_next_cron(self, cron_expr: str, base_time: datetime) -> datetime:
        """计算下次Cron执行时间（简化版）"""
        # 简化实现：支持简单的cron格式 "hour:minute"
        # 例如: "14:30" 表示每天14:30执行
        try:
            parts = cron_expr.split(":")
            if len(parts) == 2:
                hour = int(parts[0])
                minute = int(parts[1])
                
                next_run = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # 如果已经过了今天的时间，安排到明天
                if next_run <= base_time:
                    next_run += timedelta(days=1)
                
                return next_run
        except Exception:
            pass
        
        # 默认返回1小时后
        return base_time + timedelta(hours=1)
    
    def _execute_scheduled_task(self, task_id: str, task: Dict):
        """执行调度任务"""
        workflow_id = task["workflow_id"]
        workflow = self.engine.get_workflow(workflow_id)
        
        if not workflow:
            logger.error(f"工作流不存在: {workflow_id}")
            return
        
        # 异步执行
        try:
            # 在线程中执行异步任务
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                self._executor.execute(workflow, task.get("input_data", {}))
            )
            loop.close()
            
            logger.info(f"定时工作流执行成功: {task_id}")
        except Exception as e:
            logger.error(f"定时工作流执行失败: {task_id}, {e}")
    
    # ==================== 调度任务管理 ====================
    
    def add_cron_task(
        self,
        workflow_id: str,
        cron_expression: str,
        input_data: Dict = None,
        name: str = None,
        enabled: bool = True
    ) -> str:
        """
        添加Cron调度任务
        
        Args:
            workflow_id: 工作流ID
            cron_expression: Cron表达式（如 "14:30" 表示每天14:30）
            input_data: 输入数据
            name: 任务名称
            enabled: 是否启用
        
        Returns:
            task_id: 任务ID
        """
        import uuid
        task_id = uuid.uuid4().hex[:12]
        
        task = {
            "id": task_id,
            "name": name or f"Cron Task {task_id}",
            "workflow_id": workflow_id,
            "trigger_type": TriggerType.CRON,
            "cron_expression": cron_expression,
            "next_run": self._calculate_next_cron(cron_expression, datetime.now()),
            "last_run": None,
            "input_data": input_data or {},
            "enabled": enabled
        }
        
        self._tasks[task_id] = task
        logger.info(f"Cron任务已添加: {task_id}, 工作流: {workflow_id}, 表达式: {cron_expression}")
        
        return task_id
    
    def add_interval_task(
        self,
        workflow_id: str,
        interval_seconds: int,
        input_data: Dict = None,
        name: str = None,
        enabled: bool = True
    ) -> str:
        """添加间隔调度任务"""
        import uuid
        task_id = uuid.uuid4().hex[:12]
        
        task = {
            "id": task_id,
            "name": name or f"Interval Task {task_id}",
            "workflow_id": workflow_id,
            "trigger_type": TriggerType.INTERVAL,
            "interval_seconds": interval_seconds,
            "next_run": datetime.now() + timedelta(seconds=interval_seconds),
            "last_run": None,
            "input_data": input_data or {},
            "enabled": enabled
        }
        
        self._tasks[task_id] = task
        logger.info(f"间隔任务已添加: {task_id}, 工作流: {workflow_id}, 间隔: {interval_seconds}s")
        
        return task_id
    
    def add_webhook_task(
        self,
        workflow_id: str,
        webhook_path: str,
        input_mapper: Dict = None,
        name: str = None
    ) -> str:
        """添加Webhook触发任务"""
        import uuid
        task_id = uuid.uuid4().hex[:12]
        
        task = {
            "id": task_id,
            "name": name or f"Webhook Task {task_id}",
            "workflow_id": workflow_id,
            "trigger_type": TriggerType.WEBHOOK,
            "webhook_path": webhook_path,
            "input_mapper": input_mapper or {},
            "enabled": True
        }
        
        self._tasks[task_id] = task
        
        # 注册webhook处理器
        self._webhook_handlers[webhook_path] = self._create_webhook_handler(task_id)
        
        logger.info(f"Webhook任务已添加: {task_id}, 路径: /webhook/{webhook_path}")
        
        return task_id
    
    def _create_webhook_handler(self, task_id: str) -> Callable:
        """创建Webhook处理器"""
        async def handler(data: Dict):
            task = self._tasks[task_id]
            workflow = self.engine.get_workflow(task["workflow_id"])
            
            if not workflow:
                return {"error": "工作流不存在"}
            
            # 映射输入数据
            input_data = {}
            for key, value in task["input_mapper"].items():
                if isinstance(value, str) and value.startswith("$"):
                    # 从webhook数据中提取
                    input_data[key] = data.get(value[1:])
                else:
                    input_data[key] = value
            
            result = await self._executor.execute(workflow, input_data)
            return result
        
        return handler
    
    def trigger_webhook(self, webhook_path: str, data: Dict) -> Dict:
        """触发Webhook"""
        handler = self._webhook_handlers.get(webhook_path)
        
        if not handler:
            return {"error": "Webhook不存在"}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(handler(data))
            return result
        finally:
            loop.close()
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务信息"""
        task = self._tasks.get(task_id)
        if task:
            # 转换为可序列化的格式
            result = task.copy()
            if result.get("next_run"):
                result["next_run"] = result["next_run"].isoformat()
            if result.get("last_run"):
                result["last_run"] = result["last_run"].isoformat()
            return result
        return None
    
    def list_tasks(self) -> List[Dict]:
        """列出所有任务"""
        tasks = []
        for task_id, task in self._tasks.items():
            result = task.copy()
            if result.get("next_run"):
                result["next_run"] = result["next_run"].isoformat()
            if result.get("last_run"):
                result["last_run"] = result["last_run"].isoformat()
            tasks.append(result)
        return tasks
    
    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        if task_id in self._tasks:
            self._tasks[task_id]["enabled"] = True
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        if task_id in self._tasks:
            self._tasks[task_id]["enabled"] = False
            return True
        return False
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            
            # 如果是Webhook任务，移除处理器
            if task["trigger_type"] == TriggerType.WEBHOOK:
                webhook_path = task.get("webhook_path")
                if webhook_path in self._webhook_handlers:
                    del self._webhook_handlers[webhook_path]
            
            del self._tasks[task_id]
            logger.info(f"任务已删除: {task_id}")
            return True
        return False
    
    def run_task_now(self, task_id: str) -> Dict:
        """立即执行任务"""
        task = self._tasks.get(task_id)
        if not task:
            return {"error": "任务不存在"}
        
        self._execute_scheduled_task(task_id, task)
        
        return {"status": "triggered", "task_id": task_id}
    
    def get_stats(self) -> Dict:
        """获取调度器统计"""
        return {
            "total_tasks": len(self._tasks),
            "enabled_tasks": sum(1 for t in self._tasks.values() if t.get("enabled", True)),
            "disabled_tasks": sum(1 for t in self._tasks.values() if not t.get("enabled", True)),
            "running": self._running,
            "tasks_by_type": {
                "cron": sum(1 for t in self._tasks.values() if t["trigger_type"] == TriggerType.CRON),
                "interval": sum(1 for t in self._tasks.values() if t["trigger_type"] == TriggerType.INTERVAL),
                "webhook": sum(1 for t in self._tasks.values() if t["trigger_type"] == TriggerType.WEBHOOK),
            }
        }
