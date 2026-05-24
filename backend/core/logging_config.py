"""
SerpentAI 日志配置模块
支持结构化日志、自动轮转、分级过滤
"""
import logging
import sys
from pathlib import Path
from loguru import logger
from typing import Any, Dict
import json
from datetime import datetime

from backend.core.config import settings

class InterceptHandler(logging.Handler):
    """
    拦截标准logging日志，转发到loguru
    用于捕获第三方库的日志
    """
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

def format_log(record: Dict[str, Any]) -> str:
    """
    自定义日志格式（无彩色，兼容所有终端）
    """
    level_name = record["level"].name
    
    log_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        + f"{level_name: <8}"
        + " | {name}:{function}:{line} | {message}\n"
    )
    
    # 如果有异常信息，附加到日志
    if record.get("exception"):
        log_format += "{exception}\n"
    
    return log_format

def serialize_log(record: Dict[str, Any]) -> str:
    """
    序列化日志为JSON格式（用于文件存储）
    符合ELK Stack等日志收集系统的要求
    """
    log_entry = {
        "timestamp": datetime.fromtimestamp(record["time"].timestamp()).isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": record["message"],
        "process": record["process"].name,
        "thread": record["thread"].name,
    }
    
    # 添加额外字段
    if record.get("extra"):
        log_entry["extra"] = record["extra"]
    
    # 添加异常信息
    if record.get("exception"):
        log_entry["exception"] = record["exception"]
    
    return json.dumps(log_entry, ensure_ascii=False) + "\n"

def setup_logging() -> None:
    """
    配置loguru日志系统
    同时支持控制台输出和文件轮转
    """
    # 移除默认处理器
    logger.remove()
    
    # 确保日志目录存在
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 控制台输出（彩色、结构化）
    logger.add(
        sys.stdout,
        format=format_log,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # 主日志文件（轮转）
    log_file = settings.LOGS_DIR / "serpent_ai.log"
    logger.add(
        str(log_file),
        format=format_log,
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,  # 100 MB轮转
        retention=settings.LOG_RETENTION,  # 30天保留
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True
    )
    
    # 错误日志单独存储
    error_log_file = settings.LOGS_DIR / "error.log"
    logger.add(
        str(error_log_file),
        format=format_log,
        level="ERROR",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
        filter=lambda record: record["level"].name == "ERROR",
        encoding="utf-8"
    )
    
    # 拦截标准logging日志
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # 捕获第三方库日志
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", 
                        "fastapi", "sqlalchemy", "redis", "celery"]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False
    
    logger.info("日志系统初始化完成")
    logger.info(f"日志级别: {settings.LOG_LEVEL}")
    logger.info(f"日志目录: {settings.LOGS_DIR}")

def get_logger(name: str) -> logger:
    """获取指定名称的logger"""
    return logger.bind(name=name)

# ==================== 性能监控装饰器 ====================

def log_execution_time(func):
    """
    记录函数执行时间的装饰器
    用于性能分析和瓶颈定位
    """
    from functools import wraps
    import time
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000  # 毫秒
            logger.debug(f"{func.__name__} 执行时间: {execution_time:.2f}ms")
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"{func.__name__} 执行失败 (耗时 {execution_time:.2f}ms): {e}")
            raise
    
    return wrapper

def log_token_usage(model: str, input_tokens: int, output_tokens: int):
    """
    记录Token使用情况的辅助函数
    用于Token优化分析
    """
    total_tokens = input_tokens + output_tokens
    cost = estimate_token_cost(model, input_tokens, output_tokens)
    
    logger.info(
        f"Token使用 - 模型: {model}, "
        f"输入: {input_tokens}, 输出: {output_tokens}, "
        f"总计: {total_tokens}, 估算成本: ${cost:.4f}"
    )

def estimate_token_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    估算Token成本（美元）
    价格基于2024年5月的市场价
    """
    # 价格表（每1K tokens）
    pricing = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    }
    
    if model not in pricing:
        return 0.0
    
    input_cost = (input_tokens / 1000) * pricing[model]["input"]
    output_cost = (output_tokens / 1000) * pricing[model]["output"]
    
    return input_cost + output_cost
