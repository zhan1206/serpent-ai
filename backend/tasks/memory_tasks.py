"""
Celery memory operations tasks.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="backend.tasks.memory_tasks.store_memory")
def store_memory(
    self,
    agent_id: str,
    key: str,
    value: Any,
    memory_type: str = "long_term",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Store a memory entry.

    Args:
        agent_id: Agent ID
        key: Memory key
        value: Memory value
        memory_type: Type of memory (short_term, long_term, archive)
        metadata: Optional metadata

    Returns:
        Storage result
    """
    try:
        from backend.memory.knowledge_graph import KnowledgeGraph

        logger.info(f"Storing memory: {key} for agent {agent_id}")

        kg = KnowledgeGraph()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                kg.add_memory(
                    agent_id=agent_id,
                    key=key,
                    value=value,
                    memory_type=memory_type,
                    metadata=metadata or {}
                )
            )
        finally:
            loop.close()

        return {
            "success": True,
            "memory_id": result.get("id"),
            "key": key
        }

    except Exception as e:
        logger.error(f"Memory storage failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@shared_task(bind=True, name="backend.tasks.memory_tasks.search_memories")
def search_memories(
    self,
    agent_id: str,
    query: str,
    limit: int = 10,
    memory_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search memories by query.

    Args:
        agent_id: Agent ID
        query: Search query
        limit: Maximum results
        memory_type: Optional memory type filter

    Returns:
        Search results
    """
    try:
        from backend.memory.knowledge_graph import KnowledgeGraph

        logger.info(f"Searching memories for agent {agent_id}")

        kg = KnowledgeGraph()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(
                kg.search(
                    agent_id=agent_id,
                    query=query,
                    limit=limit,
                    memory_type=memory_type
                )
            )
        finally:
            loop.close()

        return {
            "success": True,
            "results": results,
            "total": len(results)
        }

    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@shared_task(name="backend.tasks.memory_tasks.consolidate_memories")
def consolidate_memories(agent_id: str) -> Dict[str, Any]:
    """
    Consolidate short-term memories into long-term memory.

    Args:
        agent_id: Agent ID

    Returns:
        Consolidation result
    """
    try:
        from backend.memory.knowledge_graph import KnowledgeGraph

        logger.info(f"Consolidating memories for agent {agent_id}")

        kg = KnowledgeGraph()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                kg.consolidate(agent_id=agent_id)
            )
        finally:
            loop.close()

        return {
            "success": True,
            "consolidated_count": result.get("count", 0),
            "agent_id": agent_id
        }

    except Exception as e:
        logger.error(f"Memory consolidation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@shared_task(name="backend.tasks.memory_tasks.archive_old_memories")
def archive_old_memories(
    agent_id: str,
    days_old: int = 30,
) -> Dict[str, Any]:
    """
    Archive memories older than specified days.

    Args:
        agent_id: Agent ID
        days_old: Threshold in days

    Returns:
        Archive result
    """
    try:
        from backend.memory.knowledge_graph import KnowledgeGraph
        from datetime import datetime, timedelta

        logger.info(f"Archiving memories older than {days_old} days")

        kg = KnowledgeGraph()
        threshold = datetime.now() - timedelta(days=days_old)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                kg.archive_before(agent_id=agent_id, threshold=threshold)
            )
        finally:
            loop.close()

        return {
            "success": True,
            "archived_count": result.get("count", 0),
            "agent_id": agent_id
        }

    except Exception as e:
        logger.error(f"Memory archival failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
