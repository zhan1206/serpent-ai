"""
Celery agent tasks for distributed execution.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="backend.tasks.agent_tasks.execute_agent")
def execute_agent(
    self,
    agent_id: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute an agent task in a distributed manner.

    Args:
        agent_id: ID of the agent to execute
        message: Input message for the agent
        context: Optional context dictionary
        model: Optional model override
        max_tokens: Optional max tokens limit

    Returns:
        Dict containing response and metadata
    """
    try:
        # Import here to avoid circular imports
        from backend.agent.agent import Agent
        from backend.models.model_registry import get_model_registry

        logger.info(f"Executing agent task: {agent_id}")

        # Create agent instance
        agent = Agent(agent_id=agent_id)

        # Get model if specified
        if model:
            registry = get_model_registry()
            model_adapter = registry.get_model(model)
            if model_adapter:
                agent.set_model(model_adapter)

        # Run agent execution
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                agent.execute(
                    message=message,
                    context=context or {},
                    max_tokens=max_tokens
                )
            )
        finally:
            loop.close()

        return {
            "success": True,
            "response": result.get("response", ""),
            "metadata": {
                "agent_id": agent_id,
                "model": model,
                "tokens_used": result.get("tokens_used", 0),
                "duration_ms": result.get("duration_ms", 0),
            }
        }

    except Exception as e:
        logger.error(f"Agent task failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "agent_id": agent_id
        }


@shared_task(bind=True, name="backend.tasks.agent_tasks.execute_reasoning")
def execute_reasoning(
    self,
    query: str,
    reasoning_type: str = "chain_of_thought",
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a reasoning task.

    Args:
        query: Query to reason about
        reasoning_type: Type of reasoning to apply
        context: Optional context

    Returns:
        Reasoning result
    """
    try:
        from backend.agent.reasoning_engine import ReasoningEngine

        logger.info(f"Executing reasoning task: {reasoning_type}")

        engine = ReasoningEngine()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.reason(
                    query=query,
                    reasoning_type=reasoning_type,
                    context=context or {}
                )
            )
        finally:
            loop.close()

        return {
            "success": True,
            "reasoning": result.get("reasoning", ""),
            "conclusion": result.get("conclusion", ""),
            "confidence": result.get("confidence", 0.0),
        }

    except Exception as e:
        logger.error(f"Reasoning task failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@shared_task(bind=True, name="backend.tasks.agent_tasks.batch_process")
def batch_process(
    self,
    agent_id: str,
    messages: list,
    parallel: bool = True,
) -> Dict[str, Any]:
    """
    Process multiple messages in batch.

    Args:
        agent_id: Agent ID
        messages: List of messages to process
        parallel: Whether to process in parallel

    Returns:
        Batch processing results
    """
    try:
        logger.info(f"Batch processing {len(messages)} messages for agent {agent_id}")

        results = []
        for i, message in enumerate(messages):
            # Update progress
            self.update_state(
                state="PROGRESS",
                meta={"current": i + 1, "total": len(messages)}
            )

            result = execute_agent(
                agent_id=agent_id,
                message=message
            )
            results.append(result)

        return {
            "success": True,
            "total": len(messages),
            "results": results
        }

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@shared_task(name="backend.tasks.agent_tasks.health_check_agent")
def health_check_agent(agent_id: str) -> Dict[str, Any]:
    """Check health of an agent."""
    try:
        from backend.agent.agent import Agent
        agent = Agent(agent_id=agent_id)
        return {
            "healthy": True,
            "agent_id": agent_id,
            "status": agent.status if hasattr(agent, 'status') else "ready"
        }
    except Exception as e:
        return {
            "healthy": False,
            "agent_id": agent_id,
            "error": str(e)
        }
