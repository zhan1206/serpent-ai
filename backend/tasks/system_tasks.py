"""
Celery system tasks for maintenance and monitoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="backend.tasks.system_tasks.health_check")
def health_check() -> Dict[str, Any]:
    """
    Perform system health check.

    Returns:
        Health status dictionary
    """
    try:
        from backend.monitoring.health import HealthChecker

        checker = HealthChecker()
        status = checker.check_all()

        return {
            "healthy": status.get("overall", True),
            "timestamp": datetime.utcnow().isoformat(),
            "components": status.get("components", {})
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(name="backend.tasks.system_tasks.cleanup_expired_sessions")
def cleanup_expired_sessions() -> Dict[str, Any]:
    """
    Clean up expired sessions from the database.

    Returns:
        Cleanup statistics
    """
    try:
        from backend.core.session_store import get_session_store

        logger.info("Running session cleanup")

        session_store = get_session_store()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                session_store.cleanup_expired()
            )
        finally:
            loop.close()

        return {
            "success": True,
            "cleaned_count": result.get("count", 0),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@shared_task(name="backend.tasks.system_tasks.cleanup_old_logs")
def cleanup_old_logs(days_old: int = 7) -> Dict[str, Any]:
    """
    Clean up log files older than specified days.

    Args:
        days_old: Threshold in days

    Returns:
        Cleanup statistics
    """
    try:
        import os
        from backend.core.config import settings

        logger.info(f"Cleaning up logs older than {days_old} days")

        logs_dir = getattr(settings, 'LOGS_DIR', 'logs')
        threshold = datetime.now() - timedelta(days=days_old)
        cleaned_count = 0
        cleaned_size = 0

        if os.path.exists(logs_dir):
            for filename in os.listdir(logs_dir):
                filepath = os.path.join(logs_dir, filename)
                if os.path.isfile(filepath):
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime < threshold:
                        size = os.path.getsize(filepath)
                        os.remove(filepath)
                        cleaned_count += 1
                        cleaned_size += size

        return {
            "success": True,
            "cleaned_files": cleaned_count,
            "cleaned_bytes": cleaned_size,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Log cleanup failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@shared_task(name="backend.tasks.system_tasks.collect_metrics")
def collect_metrics() -> Dict[str, Any]:
    """
    Collect and store system metrics.

    Returns:
        Collected metrics
    """
    try:
        import psutil
        from backend.monitoring.health import HealthChecker

        logger.info("Collecting system metrics")

        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "process_count": len(psutil.pids()),
        }

        # Get application-specific metrics
        checker = HealthChecker()
        app_metrics = checker.get_metrics()
        metrics["application"] = app_metrics

        return {
            "success": True,
            "metrics": metrics
        }

    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@shared_task(name="backend.tasks.system_tasks.optimize_database")
def optimize_database() -> Dict[str, Any]:
    """
    Run database optimization (VACUUM, ANALYZE, etc.).

    Returns:
        Optimization result
    """
    try:
        from backend.core.database import get_database

        logger.info("Running database optimization")

        db = get_database()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(db.optimize())
        finally:
            loop.close()

        return {
            "success": True,
            "optimizations": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@shared_task(name="backend.tasks.system_tasks.sync_cache")
def sync_cache() -> Dict[str, Any]:
    """
    Synchronize cache with database.

    Returns:
        Sync result
    """
    try:
        from backend.core.cache import get_cache_manager

        logger.info("Syncing cache")

        cache = get_cache_manager()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(cache.sync())
        finally:
            loop.close()

        return {
            "success": True,
            "synced_keys": result.get("count", 0),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Cache sync failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
