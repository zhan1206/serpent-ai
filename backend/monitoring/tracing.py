"""
Performance Tracing Module for SerpentAI

Provides request tracing and performance metrics:
- Request latency tracking
- Token usage tracking
- Cost statistics
- Distributed tracing support (OpenTelemetry compatible)

Usage:
    from monitoring.tracing import TracingMiddleware, TraceCollector
    
    # Add middleware to FastAPI app
    app.add_middleware(TracingMiddleware)
    
    # Get trace collector for custom tracing
    collector = TraceCollector()
    collector.trace_function(my_func)
"""

from typing import Dict, Any, Optional, Callable, List
from functools import wraps
import time
import logging
from datetime import datetime
from contextlib import contextmanager

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("prometheus_client not installed. Install with: pip install prometheus-client")


logger = logging.getLogger(__name__)

# ==================== Trace Data Structures ====================

class Trace:
    """
    Single trace record.
    
    Attributes:
        trace_id: Unique trace identifier
        span_id: Span identifier (for distributed tracing)
        parent_span_id: Parent span (for nested spans)
        operation: Operation name (e.g., 'api_chat', 'tool_execute')
        start_time: Operation start time
        end_time: Operation end time
        duration_ms: Duration in milliseconds
        status: 'success' or 'failure'
        metadata: Additional key-value pairs
        error: Error message (if failed)
    """
    
    def __init__(
        self,
        trace_id: str,
        operation: str,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ):
        """
        Initialize trace.
        
        Args:
            trace_id: Unique trace ID
            operation: Operation name
            span_id: Span ID (auto-generated if None)
            parent_span_id: Parent span ID (for nested operations)
        """
        self.trace_id = trace_id
        self.operation = operation
        self.span_id = span_id or self._generate_span_id()
        self.parent_span_id = parent_span_id
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration_ms: Optional[float] = None
        self.status: str = "unknown"
        self.metadata: Dict[str, Any] = {}
        self.error: Optional[str] = None
    
    def _generate_span_id(self) -> str:
        """Generate unique span ID."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def start(self):
        """Mark trace start."""
        self.start_time = time.time()
    
    def stop(self, status: str = "success", error: Optional[str] = None):
        """
        Mark trace end.
        
        Args:
            status: 'success' or 'failure'
            error: Error message (if failed)
        """
        self.end_time = time.time()
        if self.start_time:
            self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error = error
    
    def add_metadata(self, key: str, value: Any):
        """
        Add metadata to trace.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            dict: Trace as dictionary
        """
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation": self.operation,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_ms": round(self.duration_ms, 2) if self.duration_ms else None,
            "status": self.status,
            "metadata": self.metadata,
            "error": self.error,
        }
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"Trace(trace_id={self.trace_id}, operation={self.operation}, "
            f"duration_ms={self.duration_ms:.2f}, status={self.status})"
        )


# ==================== Trace Collector ====================

class TraceCollector:
    """
    Collects and stores traces.
    
    Usage:
        collector = TraceCollector(max_traces=1000)
        
        # Manual tracing
        trace = collector.start_trace("api_chat")
        # ... do work ...
        collector.stop_trace(trace, status="success")
        
        # Decorator tracing
        @collector.trace_function
        def my_function():
            pass
    """
    
    def __init__(self, max_traces: int = 1000, enable_prometheus: bool = True):
        """
        Initialize trace collector.
        
        Args:
            max_traces: Maximum number of traces to keep in memory
            enable_prometheus: Whether to report metrics to Prometheus
        """
        self.max_traces = max_traces
        self.enable_prometheus = enable_prometheus and PROMETHEUS_AVAILABLE
        self.traces: List[Trace] = []
        
        # Prometheus metrics (if available)
        if self.enable_prometheus:
            self._init_prometheus_metrics()
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics."""
        self.prom_latency = Histogram(
            "serpent_tracing_duration_seconds",
            "Trace duration in seconds",
            ["operation"],
            buckets=[0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )
        
        self.prom_operations_total = Counter(
            "serpent_tracing_operations_total",
            "Total traced operations",
            ["operation", "status"]
        )
        
        self.prom_operations_in_progress = Gauge(
            "serpent_tracing_operations_in_progress",
            "Operations currently in progress",
            ["operation"]
        )
    
    def start_trace(
        self,
        operation: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ) -> Trace:
        """
        Start a new trace.
        
        Args:
            operation: Operation name
            trace_id: Trace ID (auto-generated if None)
            parent_span_id: Parent span ID (for nested operations)
            
        Returns:
            Trace: Started trace object
        """
        import uuid
        
        if not trace_id:
            trace_id = str(uuid.uuid4())
        
        trace = Trace(
            trace_id=trace_id,
            operation=operation,
            parent_span_id=parent_span_id,
        )
        trace.start()
        
        # Track in-progress operations
        if self.enable_prometheus:
            self.prom_operations_in_progress.labels(operation=operation).inc()
        
        logger.debug(f"Started trace: {trace}")
        
        return trace
    
    def stop_trace(
        self,
        trace: Trace,
        status: str = "success",
        error: Optional[str] = None,
    ):
        """
        Stop a trace.
        
        Args:
            trace: Trace to stop
            status: 'success' or 'failure'
            error: Error message (if failed)
        """
        trace.stop(status=status, error=error)
        
        # Add to traces list
        self.traces.append(trace)
        
        # Trim if exceeds max_traces
        if len(self.traces) > self.max_traces:
            self.traces = self.traces[-self.max_traces:]
        
        # Report to Prometheus
        if self.enable_prometheus:
            self.prom_latency.labels(operation=trace.operation).observe(trace.duration_ms / 1000)
            self.prom_operations_total.labels(operation=trace.operation, status=status).inc()
            self.prom_operations_in_progress.labels(operation=trace.operation).dec()
        
        logger.debug(f"Stopped trace: {trace}")
    
    def get_traces(
        self,
        operation: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Trace]:
        """
        Get traces, optionally filtered.
        
        Args:
            operation: Filter by operation name
            status: Filter by status
            limit: Maximum number of traces to return
            
        Returns:
            list: Filtered traces
        """
        filtered = self.traces
        
        if operation:
            filtered = [t for t in filtered if t.operation == operation]
        
        if status:
            filtered = [t for t in filtered if t.status == status]
        
        # Return most recent first
        return list(reversed(filtered[-limit:]))
    
    def get_statistics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get trace statistics.
        
        Args:
            operation: Filter by operation name (None = all operations)
            
        Returns:
            dict: Statistics (count, avg_duration_ms, p50, p95, p99, etc.)
        """
        traces = self.get_traces(operation=operation, limit=10000)
        
        if not traces:
            return {
                "count": 0,
                "avg_duration_ms": 0,
                "min_duration_ms": 0,
                "max_duration_ms": 0,
                "p50_duration_ms": 0,
                "p95_duration_ms": 0,
                "p99_duration_ms": 0,
            }
        
        durations = sorted([t.duration_ms for t in traces if t.duration_ms is not None])
        
        count = len(durations)
        avg = sum(durations) / count
        min_dur = min(durations)
        max_dur = max(durations)
        
        # Percentiles
        p50 = durations[int(count * 0.5)]
        p95 = durations[int(count * 0.95)]
        p99 = durations[int(count * 0.99)]
        
        success_count = sum(1 for t in traces if t.status == "success")
        
        return {
            "count": count,
            "success_count": success_count,
            "failure_count": count - success_count,
            "success_rate": success_count / count if count > 0 else 0,
            "avg_duration_ms": round(avg, 2),
            "min_duration_ms": round(min_dur, 2),
            "max_duration_ms": round(max_dur, 2),
            "p50_duration_ms": round(p50, 2),
            "p95_duration_ms": round(p95, 2),
            "p99_duration_ms": round(p99, 2),
        }
    
    def clear(self):
        """Clear all traces."""
        self.traces.clear()
        logger.info("Cleared all traces")
    
    def trace_function(self, func: Callable) -> Callable:
        """
        Decorator to trace function execution.
        
        Usage:
            @collector.trace_function
            def my_function():
                pass
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            trace = self.start_trace(operation=func.__name__)
            
            try:
                result = func(*args, **kwargs)
                self.stop_trace(trace, status="success")
                return result
            except Exception as e:
                self.stop_trace(trace, status="failure", error=str(e))
                raise
        
        return wrapper


# ==================== Token Usage Tracker ====================

class TokenUsageTracker:
    """
    Track Token usage and cost statistics.
    
    Tracks:
    - Total input/output tokens per model
    - Total cost per model
    - Cost per session
    - Token usage over time
    """
    
    def __init__(self):
        """Initialize token usage tracker."""
        self.session_tokens: Dict[str, Dict[str, int]] = {}  # session_id -> {input, output}
        self.session_costs: Dict[str, float] = {}  # session_id -> total_cost
        self.model_tokens: Dict[str, Dict[str, int]] = {}  # model -> {input, output}
        self.model_costs: Dict[str, float] = {}  # model -> total_cost
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_cost: float = 0.0
    
    def track_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        session_id: Optional[str] = None,
    ):
        """
        Track token usage and cost.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost: Cost in USD
            session_id: Session ID (optional)
        """
        # Update totals
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        
        # Update model stats
        if model not in self.model_tokens:
            self.model_tokens[model] = {"input": 0, "output": 0}
        if model not in self.model_costs:
            self.model_costs[model] = 0.0
        
        self.model_tokens[model]["input"] += input_tokens
        self.model_tokens[model]["output"] += output_tokens
        self.model_costs[model] += cost
        
        # Update session stats
        if session_id:
            if session_id not in self.session_tokens:
                self.session_tokens[session_id] = {"input": 0, "output": 0}
            if session_id not in self.session_costs:
                self.session_costs[session_id] = 0.0
            
            self.session_tokens[session_id]["input"] += input_tokens
            self.session_tokens[session_id]["output"] += output_tokens
            self.session_costs[session_id] += cost
        
        logger.debug(
            f"Tracked token usage: model={model}, "
            f"input={input_tokens}, output={output_tokens}, cost=${cost:.6f}"
        )
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get token usage statistics for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            dict: Session statistics
        """
        tokens = self.session_tokens.get(session_id, {"input": 0, "output": 0})
        cost = self.session_costs.get(session_id, 0.0)
        
        return {
            "session_id": session_id,
            "input_tokens": tokens["input"],
            "output_tokens": tokens["output"],
            "total_tokens": tokens["input"] + tokens["output"],
            "total_cost": round(cost, 6),
        }
    
    def get_model_stats(self, model: str) -> Dict[str, Any]:
        """
        Get token usage statistics for a model.
        
        Args:
            model: Model name
            
        Returns:
            dict: Model statistics
        """
        tokens = self.model_tokens.get(model, {"input": 0, "output": 0})
        cost = self.model_costs.get(model, 0.0)
        
        return {
            "model": model,
            "input_tokens": tokens["input"],
            "output_tokens": tokens["output"],
            "total_tokens": tokens["input"] + tokens["output"],
            "total_cost": round(cost, 6),
        }
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """
        Get overall token usage statistics.
        
        Returns:
            dict: Overall statistics
        """
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost": round(self.total_cost, 6),
            "session_count": len(self.session_tokens),
            "model_count": len(self.model_tokens),
            "sessions": {
                session_id: self.get_session_stats(session_id)
                for session_id in self.session_tokens
            },
            "models": {
                model: self.get_model_stats(model)
                for model in self.model_tokens
            },
        }
    
    def reset(self):
        """Reset all statistics."""
        self.session_tokens.clear()
        self.session_costs.clear()
        self.model_tokens.clear()
        self.model_costs.clear()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        logger.info("Reset all token usage statistics")


# ==================== FastAPI Middleware ====================

class TracingMiddleware:
    """
    FastAPI middleware for automatic request tracing.
    
    Usage:
        app.add_middleware(TracingMiddleware, collector=collector)
    """
    
    def __init__(self, app, collector: Optional[TraceCollector] = None):
        """
        Initialize tracing middleware.
        
        Args:
            app: FastAPI application
            collector: TraceCollector instance (creates new if None)
        """
        self.app = app
        self.collector = collector or TraceCollector()
    
    async def __call__(self, request, call_next):
        """
        Process request with tracing.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        # Start trace
        operation = f"{request.method} {request.url.path}"
        trace = self.collector.start_trace(operation=operation)
        
        # Add metadata
        trace.add_metadata("method", request.method)
        trace.add_metadata("path", str(request.url.path))
        trace.add_metadata("client_ip", request.client.host if request.client else None)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Stop trace (success)
            trace.add_metadata("status_code", response.status_code)
            self.collector.stop_trace(trace, status="success")
            
            return response
        
        except Exception as e:
            # Stop trace (failure)
            trace.add_metadata("status_code", 500)
            self.collector.stop_trace(trace, status="failure", error=str(e))
            raise


# ==================== Global Instances ====================

# Global trace collector
_global_collector: Optional[TraceCollector] = None

# Global token usage tracker
_global_tracker: Optional[TokenUsageTracker] = None


def get_trace_collector() -> TraceCollector:
    """
    Get global trace collector instance.
    
    Returns:
        TraceCollector: Global instance
    """
    global _global_collector
    
    if _global_collector is None:
        _global_collector = TraceCollector()
    
    return _global_collector


def get_token_tracker() -> TokenUsageTracker:
    """
    Get global token usage tracker instance.
    
    Returns:
        TokenUsageTracker: Global instance
    """
    global _global_tracker
    
    if _global_tracker is None:
        _global_tracker = TokenUsageTracker()
    
    return _global_tracker


# ==================== Utility Functions ====================

@contextmanager
def trace_block(
    operation: str,
    collector: Optional[TraceCollector] = None,
    **metadata
):
    """
    Context manager for tracing a code block.
    
    Usage:
        with trace_block("my_operation", key1="value1") as trace:
            # ... do work ...
            trace.add_metadata("result", "success")
    
    Args:
        operation: Operation name
        collector: TraceCollector (uses global if None)
        **metadata: Initial metadata
    """
    coll = collector or get_trace_collector()
    
    trace = coll.start_trace(operation=operation)
    
    for key, value in metadata.items():
        trace.add_metadata(key, value)
    
    try:
        yield trace
        coll.stop_trace(trace, status="success")
    except Exception as e:
        coll.stop_trace(trace, status="failure", error=str(e))
        raise


# ==================== Example Usage ====================

if __name__ == "__main__":
    # Example: Using TraceCollector
    collector = TraceCollector()
    
    # Trace a function
    @collector.trace_function
    def process_data():
        time.sleep(0.1)
        return "done"
    
    result = process_data()
    print(f"Result: {result}")
    
    # Get statistics
    stats = collector.get_statistics()
    print(f"Statistics: {stats}")
    
    # Example: Using TokenUsageTracker
    tracker = TokenUsageTracker()
    
    tracker.track_usage(
        model="gpt-4o",
        input_tokens=100,
        output_tokens=50,
        cost=0.0015,
        session_id="user123"
    )
    
    overall = tracker.get_overall_stats()
    print(f"Overall stats: {overall}")
