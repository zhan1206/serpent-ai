"""
Prometheus Metrics Module for SerpentAI

Exposes metrics at /metrics endpoint for monitoring.
Supports:
- HTTP request metrics (latency, count, status)
- Token usage metrics
- Cost tracking metrics
- Tool execution metrics
- Memory system metrics
"""

from typing import Callable, Dict, Any
from functools import wraps
import time
import logging

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Info,
        generate_latest, CONTENT_TYPE_LATEST,
        REGISTRY
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("prometheus_client not installed. Install with: pip install prometheus-client")


logger = logging.getLogger(__name__)

# ==================== Metric Definitions ====================

if PROMETHEUS_AVAILABLE:
    # HTTP Request Metrics
    http_requests_total = Counter(
        "serpent_http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status_code"]
    )
    
    http_request_duration_seconds = Histogram(
        "serpent_http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
    )
    
    http_requests_in_progress = Gauge(
        "serpent_http_requests_in_progress",
        "HTTP requests currently in progress",
        ["method", "endpoint"]
    )
    
    # Token Usage Metrics
    token_usage_total = Counter(
        "serpent_token_usage_total",
        "Total token usage",
        ["model", "type"]  # type: input/output/total
    )
    
    # Cost Tracking Metrics
    cost_total = Counter(
        "serpent_cost_total",
        "Total cost in USD",
        ["model"]
    )
    
    cost_current = Gauge(
        "serpent_cost_current",
        "Current session cost in USD",
        ["session_id"]
    )
    
    # Tool Execution Metrics
    tool_executions_total = Counter(
        "serpent_tool_executions_total",
        "Total tool executions",
        ["tool_name", "status"]  # status: success/failure
    )
    
    tool_execution_duration_seconds = Histogram(
        "serpent_tool_execution_duration_seconds",
        "Tool execution duration in seconds",
        ["tool_name"],
        buckets=[0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    )
    
    tool_cache_hits_total = Counter(
        "serpent_tool_cache_hits_total",
        "Total tool cache hits",
        ["tool_name"]
    )
    
    tool_cache_misses_total = Counter(
        "serpent_tool_cache_misses_total",
        "Total tool cache misses",
        ["tool_name"]
    )
    
    # Memory System Metrics
    memory_messages_total = Gauge(
        "serpent_memory_messages_total",
        "Total messages in memory system",
        ["session_id", "layer"]  # layer: instant/short_term/long_term/archive
    )
    
    memory_operations_total = Counter(
        "serpent_memory_operations_total",
        "Total memory operations",
        ["operation", "layer"]  # operation: add/recall/clear
    )
    
    # AI Model Metrics
    ai_requests_total = Counter(
        "serpent_ai_requests_total",
        "Total AI model requests",
        ["model", "status"]  # status: success/failure
    )
    
    ai_request_duration_seconds = Histogram(
        "serpent_ai_request_duration_seconds",
        "AI model request duration in seconds",
        ["model"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
    )
    
    # Agent Metrics
    agent_sessions_total = Counter(
        "serpent_agent_sessions_total",
        "Total agent sessions",
        ["agent_name"]
    )
    
    agent_sessions_active = Gauge(
        "serpent_agent_sessions_active",
        "Currently active agent sessions",
        ["agent_name"]
    )
    
    # Task Scheduler Metrics
    tasks_total = Counter(
        "serpent_tasks_total",
        "Total tasks",
        ["status"]  # status: pending/running/completed/failed/cancelled
    )
    
    tasks_in_progress = Gauge(
        "serpent_tasks_in_progress",
        "Tasks currently in progress",
    )
    
    # Application Info
    app_info = Info(
        "serpent_app",
        "Application information"
    )


# ==================== Metrics Functions ====================

def init_metrics(app_name: str = "SerpentAI", app_version: str = "0.1.0-alpha"):
    """
    Initialize metrics with application info.
    
    Args:
        app_name: Application name
        app_version: Application version
    """
    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus not available. Metrics disabled.")
        return
    
    app_info.info({
        "name": app_name,
        "version": app_version,
        "python_version": "3.12",
    })
    
    logger.info("Prometheus metrics initialized")


def get_metrics() -> bytes:
    """
    Get current metrics in Prometheus format.
    
    Returns:
        bytes: Prometheus formatted metrics
    """
    if not PROMETHEUS_AVAILABLE:
        return b"# Prometheus client not installed\n"
    
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """
    Get content type for metrics endpoint.
    
    Returns:
        str: Content type string
    """
    if not PROMETHEUS_AVAILABLE:
        return "text/plain"
    
    return CONTENT_TYPE_LATEST


# ==================== Metrics Decorators ====================

def track_token_usage(model: str, input_tokens: int, output_tokens: int, cost: float):
    """
    Track token usage and cost.
    
    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost: Cost in USD
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    token_usage_total.labels(model=model, type="input").inc(input_tokens)
    token_usage_total.labels(model=model, type="output").inc(output_tokens)
    token_usage_total.labels(model=model, type="total").inc(input_tokens + output_tokens)
    
    if cost > 0:
        cost_total.labels(model=model).inc(cost)
    
    logger.debug(f"Tracked token usage: model={model}, input={input_tokens}, output={output_tokens}, cost={cost}")


def track_tool_execution(tool_name: str, status: str, duration: float, cached: bool = False):
    """
    Track tool execution metrics.
    
    Args:
        tool_name: Tool name
        status: 'success' or 'failure'
        duration: Execution duration in seconds
        cached: Whether result was from cache
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    tool_executions_total.labels(tool_name=tool_name, status=status).inc()
    tool_execution_duration_seconds.labels(tool_name=tool_name).observe(duration)
    
    if cached:
        tool_cache_hits_total.labels(tool_name=tool_name).inc()
    else:
        tool_cache_misses_total.labels(tool_name=tool_name).inc()
    
    logger.debug(f"Tracked tool execution: tool={tool_name}, status={status}, duration={duration:.3f}s, cached={cached}")


def track_memory_operation(operation: str, layer: str, session_id: str = "unknown"):
    """
    Track memory system operations.
    
    Args:
        operation: 'add', 'recall', or 'clear'
        layer: 'instant', 'short_term', 'long_term', or 'archive'
        session_id: Session identifier
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    memory_operations_total.labels(operation=operation, layer=layer).inc()
    
    logger.debug(f"Tracked memory operation: operation={operation}, layer={layer}, session={session_id}")


def update_memory_count(session_id: str, layer: str, count: int):
    """
    Update memory message count gauge.
    
    Args:
        session_id: Session identifier
        layer: Memory layer
        count: Number of messages
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    memory_messages_total.labels(session_id=session_id, layer=layer).set(count)


def track_ai_request(model: str, status: str, duration: float):
    """
    Track AI model request.
    
    Args:
        model: Model name
        status: 'success' or 'failure'
        duration: Request duration in seconds
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    ai_requests_total.labels(model=model, status=status).inc()
    ai_request_duration_seconds.labels(model=model).observe(duration)
    
    logger.debug(f"Tracked AI request: model={model}, status={status}, duration={duration:.3f}s")


def track_agent_session(agent_name: str, active: bool):
    """
    Track agent session.
    
    Args:
        agent_name: Agent name
        active: True if session started, False if ended
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    if active:
        agent_sessions_total.labels(agent_name=agent_name).inc()
    
    # Note: For proper active session tracking, you'd need to increment/decrement
    # This is a simplified version
    logger.debug(f"Tracked agent session: agent={agent_name}, active={active}")


def update_task_count(status: str, increment: int = 1):
    """
    Update task count.
    
    Args:
        status: Task status
        increment: Amount to increment (use -1 to decrement)
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    tasks_total.labels(status=status).inc(increment)
    
    # Update in-progress gauge
    if status == "running":
        tasks_in_progress.inc(increment)
    
    logger.debug(f"Updated task count: status={status}, increment={increment}")


# ==================== FastAPI Middleware ====================

def metrics_middleware(app):
    """
    FastAPI middleware for automatic HTTP metrics collection.
    
    Usage:
        app.middleware('http')(metrics_middleware)
    """
    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus not available. Metrics middleware disabled.")
        return lambda request, call_next: call_next(request)
    
    @wraps(app)
    async def middleware(request, call_next):
        """Collect HTTP metrics for each request."""
        method = request.method
        path = request.url.path
        
        # Skip metrics endpoint to avoid recursion
        if path == "/metrics":
            return await call_next(request)
        
        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=path).inc()
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            
            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=path,
                status_code=str(status_code)
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=path
            ).observe(duration)
            
            http_requests_in_progress.labels(
                method=method,
                endpoint=path
            ).dec()
        
        return response
    
    return middleware


# ==================== Metrics Endpoint Handler ====================

async def metrics_endpoint():
    """
    FastAPI endpoint handler for /metrics.
    
    Usage:
        @app.get("/metrics")
        async def metrics():
            return await metrics_endpoint()
    """
    from fastapi.responses import Response
    
    content = get_metrics()
    content_type = get_metrics_content_type()
    
    return Response(
        content=content,
        media_type=content_type
    )
