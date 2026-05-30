"""
Celery tasks package for SerpentAI.
"""

from backend.tasks.agent_tasks import (
    execute_agent,
    execute_reasoning,
    batch_process,
    health_check_agent,
)

from backend.tasks.tool_tasks import (
    execute_tool,
    execute_tool_chain,
    validate_tool,
)

from backend.tasks.memory_tasks import (
    store_memory,
    search_memories,
    consolidate_memories,
    archive_old_memories,
)

from backend.tasks.system_tasks import (
    health_check,
    cleanup_expired_sessions,
    cleanup_old_logs,
    collect_metrics,
    optimize_database,
    sync_cache,
)

__all__ = [
    # Agent tasks
    "execute_agent",
    "execute_reasoning",
    "batch_process",
    "health_check_agent",
    # Tool tasks
    "execute_tool",
    "execute_tool_chain",
    "validate_tool",
    # Memory tasks
    "store_memory",
    "search_memories",
    "consolidate_memories",
    "archive_old_memories",
    # System tasks
    "health_check",
    "cleanup_expired_sessions",
    "cleanup_old_logs",
    "collect_metrics",
    "optimize_database",
    "sync_cache",
]
