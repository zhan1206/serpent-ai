"""
SerpentAI Celery Configuration

Distributed task queue for scalable agent operations.
"""

from celery import Celery
from backend.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Celery app instance
celery_app = Celery(
    "serpent_ai",
    broker=settings.CELERY_BROKER_URL if hasattr(settings, 'CELERY_BROKER_URL') else "redis://localhost:6379/0",
    backend=settings.CELERY_RESULT_BACKEND if hasattr(settings, 'CELERY_RESULT_BACKEND') else "redis://localhost:6379/0",
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,

    # Result backend
    result_expires=3600,  # 1 hour

    # Task routing
    task_routes={
        "backend.tasks.agent_tasks.*": {"queue": "agent"},
        "backend.tasks.tool_tasks.*": {"queue": "tools"},
        "backend.tasks.memory_tasks.*": {"queue": "memory"},
    },

    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-expired-sessions": {
            "task": "backend.tasks.system_tasks.cleanup_expired_sessions",
            "schedule": 3600.0,  # Every hour
        },
        "health-check": {
            "task": "backend.tasks.system_tasks.health_check",
            "schedule": 60.0,  # Every minute
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks([
    "backend.tasks.agent_tasks",
    "backend.tasks.tool_tasks",
    "backend.tasks.memory_tasks",
    "backend.tasks.system_tasks",
])


def get_celery_app() -> Celery:
    """Get the Celery application instance."""
    return celery_app


def is_celery_available() -> bool:
    """Check if Celery is properly configured and available."""
    try:
        from celery import Celery
        import redis
        return True
    except ImportError:
        return False


class CeleryTaskManager:
    """
    Manager for Celery task operations.

    Provides a high-level interface for submitting and managing
    distributed tasks.
    """

    def __init__(self, app: Celery = None):
        self.app = app or celery_app

    def submit_task(
        self,
        task_name: str,
        args: tuple = None,
        kwargs: dict = None,
        queue: str = None,
        priority: int = None,
        countdown: float = None,
        eta=None,
    ):
        """
        Submit a task for execution.

        Args:
            task_name: Name of the task to execute
            args: Positional arguments for the task
            kwargs: Keyword arguments for the task
            queue: Specific queue to use
            priority: Task priority (0-9, higher is more important)
            countdown: Seconds to wait before executing
            eta: Specific time to execute

        Returns:
            AsyncResult: Task result object
        """
        options = {}
        if queue:
            options["queue"] = queue
        if priority is not None:
            options["priority"] = priority
        if countdown is not None:
            options["countdown"] = countdown
        if eta is not None:
            options["eta"] = eta

        return self.app.send_task(
            task_name,
            args=args or (),
            kwargs=kwargs or {},
            **options
        )

    def get_task_result(self, task_id: str):
        """Get the result of a task by ID."""
        return self.app.AsyncResult(task_id)

    def revoke_task(self, task_id: str, terminate: bool = False):
        """Revoke a pending or running task."""
        self.app.control.revoke(task_id, terminate=terminate)

    def get_active_tasks(self):
        """Get list of currently active tasks."""
        inspect = self.app.control.inspect()
        return inspect.active()

    def get_scheduled_tasks(self):
        """Get list of scheduled tasks."""
        inspect = self.app.control.inspect()
        return inspect.scheduled()

    def get_worker_stats(self):
        """Get statistics from all workers."""
        inspect = self.app.control.inspect()
        return inspect.stats()


# Task decorators for convenience
def agent_task(func):
    """Decorator for agent-related tasks."""
    return celery_app.task(bind=True, name=f"backend.tasks.agent_tasks.{func.__name__}")(func)


def tool_task(func):
    """Decorator for tool execution tasks."""
    return celery_app.task(bind=True, name=f"backend.tasks.tool_tasks.{func.__name__}")(func)


def memory_task(func):
    """Decorator for memory-related tasks."""
    return celery_app.task(bind=True, name=f"backend.tasks.memory_tasks.{func.__name__}")(func)


def system_task(func):
    """Decorator for system tasks."""
    return celery_app.task(bind=True, name=f"backend.tasks.system_tasks.{func.__name__}")(func)
