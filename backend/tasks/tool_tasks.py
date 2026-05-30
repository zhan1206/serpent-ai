"""
Celery tool execution tasks.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="backend.tasks.tool_tasks.execute_tool")
def execute_tool(
    self,
    tool_name: str,
    args: Dict[str, Any],
    sandbox: bool = True,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute a tool in a distributed manner.

    Args:
        tool_name: Name of the tool to execute
        args: Arguments for the tool
        sandbox: Whether to run in sandbox mode
        timeout: Optional timeout in seconds

    Returns:
        Tool execution result
    """
    try:
        from backend.tools.tool_registry import get_tool_registry
        from backend.tools.tool_executor import ToolExecutor

        logger.info(f"Executing tool: {tool_name}")

        executor = ToolExecutor(sandbox_enabled=sandbox)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                executor.execute(
                    tool_name=tool_name,
                    args=args,
                    timeout=timeout
                )
            )
        finally:
            loop.close()

        return {
            "success": True,
            "output": result.get("output", {}),
            "metadata": {
                "tool_name": tool_name,
                "duration_ms": result.get("duration_ms", 0),
                "sandbox": sandbox,
            }
        }

    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "tool_name": tool_name
        }


@shared_task(bind=True, name="backend.tasks.tool_tasks.execute_tool_chain")
def execute_tool_chain(
    self,
    tool_chain: list,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a chain of tools sequentially.

    Args:
        tool_chain: List of (tool_name, args) tuples
        context: Shared context for the chain

    Returns:
        Chain execution results
    """
    try:
        logger.info(f"Executing tool chain with {len(tool_chain)} tools")

        results = []
        current_context = context or {}

        for i, (tool_name, args) in enumerate(tool_chain):
            # Update progress
            self.update_state(
                state="PROGRESS",
                meta={"current": i + 1, "total": len(tool_chain)}
            )

            # Merge context into args
            merged_args = {**args, **current_context}

            result = execute_tool(tool_name=tool_name, args=merged_args)
            results.append(result)

            # Update context with result
            if result["success"]:
                current_context.update(result.get("output", {}))

        return {
            "success": all(r["success"] for r in results),
            "results": results,
            "final_context": current_context
        }

    except Exception as e:
        logger.error(f"Tool chain execution failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@shared_task(name="backend.tasks.tool_tasks.validate_tool")
def validate_tool(tool_name: str) -> Dict[str, Any]:
    """Validate a tool's configuration and availability."""
    try:
        from backend.tools.tool_registry import get_tool_registry

        registry = get_tool_registry()
        tool = registry.get_tool(tool_name)

        if tool is None:
            return {
                "valid": False,
                "error": f"Tool '{tool_name}' not found"
            }

        return {
            "valid": True,
            "tool_name": tool_name,
            "description": getattr(tool, 'description', ''),
            "parameters": getattr(tool, 'parameters', {})
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }
