"""
SerpentAI Monitoring Module

Provides observability features:
- Prometheus metrics exposure (/metrics endpoint)
- Structured JSON logging (for ELK/Loki collection)
- Enhanced health check (/health endpoint with detailed status)
- Performance tracing (request latency, Token usage, cost statistics)
"""

from .metrics import get_metrics, init_metrics, metrics_middleware
from .logging import setup_structured_logging, get_structured_logger
from .health import enhanced_health_check
from .tracing import TracingMiddleware, TraceCollector

__all__ = [
    "get_metrics",
    "init_metrics",
    "metrics_middleware",
    "setup_structured_logging",
    "get_structured_logger",
    "enhanced_health_check",
    "TracingMiddleware",
    "TraceCollector",
]
