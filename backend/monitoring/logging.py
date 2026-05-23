"""
Structured Logging Module for SerpentAI

Provides JSON-formatted logs for ELK/Loki collection.
Supports:
- JSON formatting with timestamps
- Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Contextual information (request_id, session_id, etc.)
- Request tracing (correlation IDs)
"""

import json
import logging
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


# ==================== JSON Formatter ====================

class JSONFormatter(logging.Formatter):
    """
    Custom logging formatter that outputs JSON.
    
    Format:
        {
            "timestamp": "2024-01-01T12:00:00.000Z",
            "level": "INFO",
            "logger": "serpent.module",
            "message": "Log message",
            "context": {  # optional
                "request_id": "abc123",
                "session_id": "user123",
                "duration_ms": 150
            }
        }
    """
    
    def __init__(self, include_context: bool = True):
        """
        Initialize JSON formatter.
        
        Args:
            include_context: Whether to include extra context fields
        """
        super().__init__()
        self.include_context = include_context
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            str: JSON-formatted log string
        """
        # Base log structure
        log_obj = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add context if available
        if self.include_context:
            context = {}
            
            # Standard fields
            if hasattr(record, "request_id"):
                context["request_id"] = record.request_id
            if hasattr(record, "session_id"):
                context["session_id"] = record.session_id
            if hasattr(record, "user_id"):
                context["user_id"] = record.user_id
            if hasattr(record, "duration_ms"):
                context["duration_ms"] = record.duration_ms
            if hasattr(record, "token_count"):
                context["token_count"] = record.token_count
            if hasattr(record, "cost"):
                context["cost"] = record.cost
            
            # Add any extra fields from record
            for key, value in record.__dict__.items():
                if key.startswith("_") or key in [
                    "name", "msg", "args", "levelname", "levelno",
                    "pathname", "filename", "module", "exc_info",
                    "exc_text", "stack_info", "lineno", "funcName",
                    "created", "msecs", "relativeCreated", "thread",
                    "threadName", "processName", "process", "message",
                    "request_id", "session_id", "user_id", "duration_ms",
                    "token_count", "cost"
                ]:
                    continue
                context[key] = value
            
            if context:
                log_obj["context"] = context
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj, ensure_ascii=False)


# ==================== Contextual Logger ====================

class ContextualLogger:
    """
    Logger wrapper that adds context to all log messages.
    
    Usage:
        logger = get_structured_logger(__name__)
        logger.set_context(request_id="abc123", session_id="user123")
        logger.info("Request processed")
        # Output includes context fields
    """
    
    def __init__(self, name: str, level: Optional[str] = None):
        """
        Initialize contextual logger.
        
        Args:
            name: Logger name (usually __name__)
            level: Log level override (default: from settings)
        """
        self._logger = logging.getLogger(name)
        self._context: Dict[str, Any] = {}
        
        if level:
            self._logger.setLevel(getattr(logging, level.upper()))
    
    def set_context(self, **kwargs):
        """
        Set context fields for all subsequent log messages.
        
        Args:
            **kwargs: Context key-value pairs
        """
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear all context fields."""
        self._context.clear()
    
    def _log(self, level: int, msg: str, *args, **kwargs):
        """
        Internal log method that adds context.
        
        Args:
            level: Log level
            msg: Log message
            *args: Positional arguments for message formatting
            **kwargs: Additional context fields (override existing)
        """
        # Merge instance context with call-specific context
        context = {**self._context, **kwargs}
        
        # Create log record with context
        if context:
            # Add context to extra
            extra = {"context": context}
            self._logger.log(level, msg, *args, extra=extra)
        else:
            self._logger.log(level, msg, *args)
    
    def debug(self, msg: str, *args, **kwargs):
        """Log debug message with context."""
        self._log(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """Log info message with context."""
        self._log(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """Log warning message with context."""
        self._log(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """Log error message with context."""
        self._log(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """Log critical message with context."""
        self._log(logging.CRITICAL, msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        """
        Log exception with traceback.
        
        Args:
            msg: Log message
            *args: Positional arguments
            **kwargs: Context fields
        """
        context = {**self._context, **kwargs}
        extra = {"context": context} if context else {}
        self._logger.exception(msg, *args, extra=extra)


# ==================== Setup Functions ====================

def setup_structured_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = True,
    include_context: bool = True
):
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path (if None, logs to stdout)
        json_format: Whether to use JSON formatting (default: True)
        include_context: Whether to include context in JSON (default: True)
    """
    # Remove existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set log level
    log_level_obj = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level_obj)
    
    # Create handler
    if log_file:
        # File handler
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file, encoding="utf-8")
    else:
        # Stdout handler
        handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter
    if json_format:
        handler.setFormatter(JSONFormatter(include_context=include_context))
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
    
    # Add handler to root logger
    root_logger.addHandler(handler)
    
    # Set third-party loggers to WARNING
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Structured logging initialized (level={log_level}, json={json_format})")


def get_structured_logger(name: str, level: Optional[str] = None) -> ContextualLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        level: Optional log level override
    
    Returns:
        ContextualLogger: Logger with context support
    """
    return ContextualLogger(name, level)


# ==================== Request Context Middleware ====================

def add_request_context(request_id: str, **kwargs):
    """
    Add request context for the current request.
    
    This function can be used in FastAPI middleware to add
    request-specific context to all log messages.
    
    Args:
        request_id: Unique request identifier
        **kwargs: Additional context (session_id, user_id, etc.)
    """
    # Store in thread-local or contextvars for async support
    import threading
    thread_local = threading.local()
    thread_local.request_context = {
        "request_id": request_id,
        **kwargs
    }


def get_request_context() -> Dict[str, Any]:
    """
    Get current request context.
    
    Returns:
        dict: Request context dictionary
    """
    import threading
    thread_local = threading.local()
    return getattr(thread_local, "request_context", {})


# ==================== Log Event Functions ====================

def log_request(
    logger: ContextualLogger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **kwargs
):
    """
    Log HTTP request with structured data.
    
    Args:
        logger: Structured logger instance
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        **kwargs: Additional fields
    """
    logger.info(
        f"{method} {path} {status_code}",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs
    )


def log_token_usage(
    logger: ContextualLogger,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost: float,
    **kwargs
):
    """
    Log token usage with structured data.
    
    Args:
        logger: Structured logger instance
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost: Cost in USD
        **kwargs: Additional fields
    """
    logger.info(
        f"Token usage: {input_tokens}+{output_tokens} tokens, cost=${cost:.6f}",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost=cost,
        **kwargs
    )


def log_tool_execution(
    logger: ContextualLogger,
    tool_name: str,
    status: str,
    duration_ms: float,
    cached: bool = False,
    **kwargs
):
    """
    Log tool execution with structured data.
    
    Args:
        logger: Structured logger instance
        tool_name: Tool name
        status: Execution status ('success' or 'failure')
        duration_ms: Execution duration in milliseconds
        cached: Whether result was from cache
        **kwargs: Additional fields
    """
    logger.info(
        f"Tool {tool_name}: {status} ({duration_ms:.1f}ms, cached={cached})",
        tool_name=tool_name,
        status=status,
        duration_ms=duration_ms,
        cached=cached,
        **kwargs
    )


def log_memory_operation(
    logger: ContextualLogger,
    operation: str,
    session_id: str,
    layer: str,
    count: int = 0,
    **kwargs
):
    """
    Log memory system operation with structured data.
    
    Args:
        logger: Structured logger instance
        operation: Operation type ('add', 'recall', 'clear')
        session_id: Session identifier
        layer: Memory layer ('instant', 'short_term', 'long_term', 'archive')
        count: Number of affected items
        **kwargs: Additional fields
    """
    logger.info(
        f"Memory {operation}: session={session_id}, layer={layer}, count={count}",
        operation=operation,
        session_id=session_id,
        layer=layer,
        count=count,
        **kwargs
    )


# ==================== Example Usage ====================

if __name__ == "__main__":
    # Example: Setup structured logging
    setup_structured_logging(log_level="DEBUG", json_format=True)
    
    # Get logger
    logger = get_structured_logger(__name__)
    
    # Set global context
    logger.set_context(service="serpent-api", version="0.1.0")
    
    # Log messages
    logger.info("Application started")
    
    # Log with additional context
    logger.info(
        "Request received",
        request_id="abc123",
        method="POST",
        path="/api/chat"
    )
    
    # Log token usage
    log_token_usage(
        logger,
        model="gpt-4o",
        input_tokens=100,
        output_tokens=50,
        cost=0.0015,
        session_id="user123"
    )
    
    # Log tool execution
    log_tool_execution(
        logger,
        tool_name="fs_read",
        status="success",
        duration_ms=15.5,
        cached=False
    )
    
    # Log memory operation
    log_memory_operation(
        logger,
        operation="add",
        session_id="user123",
        layer="instant",
        count=1
    )
    
    logger.error("An error occurred", error="Something went wrong")
