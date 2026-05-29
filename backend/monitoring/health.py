"""
Enhanced Health Check Module for SerpentAI

Provides detailed health status for all system components.
Used by:
- /health endpoint (detailed status)
- Load balancers (active health check)
- Monitoring systems (alerting)

Health status levels:
- healthy: All components operational
- degraded: Some components impaired but service functional
- unhealthy: Critical components failed, service impaired
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import time
import logging

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


# ==================== Health Check Classes ====================

class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth:
    """
    Health information for a single component.
    
    Attributes:
        name: Component name
        status: 'healthy', 'degraded', or 'unhealthy'
        details: Additional information (response time, error messages, etc.)
        last_check: Timestamp of last health check
        response_time_ms: Response time in milliseconds
    """
    
    def __init__(
        self,
        name: str,
        status: str = HealthStatus.HEALTHY,
        details: Optional[Dict[str, Any]] = None,
        response_time_ms: Optional[float] = None
    ):
        """
        Initialize component health.
        
        Args:
            name: Component name
            status: Health status
            details: Additional details dictionary
            response_time_ms: Response time in milliseconds
        """
        self.name = name
        self.status = status
        self.details = details or {}
        self.last_check = datetime.now(timezone.utc)
        self.response_time_ms = response_time_ms
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON response.
        
        Returns:
            dict: Health information as dictionary
        """
        return {
            "status": self.status,
            "details": self.details,
            "last_check": self.last_check.isoformat(),
            "response_time_ms": self.response_time_ms,
        }
    
    def is_healthy(self) -> bool:
        """Check if component is healthy."""
        return self.status == HealthStatus.HEALTHY
    
    def is_degraded(self) -> bool:
        """Check if component is degraded."""
        return self.status == HealthStatus.DEGRADED


class SystemHealth:
    """
    Overall system health aggregator.
    
    Collects health status from all components and
    provides overall system health assessment.
    """
    
    def __init__(self, app_name: str = "SerpentAI", app_version: str = "0.1.0-alpha"):
        """
        Initialize system health.
        
        Args:
            app_name: Application name
            app_version: Application version
        """
        self.app_name = app_name
        self.app_version = app_version
        self.components: Dict[str, ComponentHealth] = {}
        self.start_time = datetime.now(timezone.utc)
    
    def add_component(self, name: str, health: ComponentHealth):
        """
        Add component health status.
        
        Args:
            name: Component name
            health: ComponentHealth instance
        """
        self.components[name] = health
    
    def get_component(self, name: str) -> Optional[ComponentHealth]:
        """
        Get health status for a component.
        
        Args:
            name: Component name
            
        Returns:
            ComponentHealth or None if not found
        """
        return self.components.get(name)
    
    def get_overall_status(self) -> str:
        """
        Calculate overall system health status.
        
        Rules:
        - If any component is 'unhealthy', system is 'unhealthy'
        - If any component is 'degraded' (and none are 'unhealthy'), system is 'degraded'
        - Otherwise, system is 'healthy'
        
        Returns:
            str: Overall health status
        """
        has_degraded = False
        
        for component in self.components.values():
            if component.status == HealthStatus.UNHEALTHY:
                return HealthStatus.UNHEALTHY
            elif component.status == HealthStatus.DEGRADED:
                has_degraded = True
        
        if has_degraded:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def get_uptime_seconds(self) -> float:
        """
        Get system uptime in seconds.
        
        Returns:
            float: Uptime in seconds
        """
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON response.
        
        Returns:
            dict: Complete health status as dictionary
        """
        overall_status = self.get_overall_status()
        
        return {
            "status": overall_status,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": self.get_uptime_seconds(),
            "components": {
                name: component.to_dict()
                for name, component in self.components.items()
            },
            "summary": {
                "total_components": len(self.components),
                "healthy": sum(1 for c in self.components.values() if c.is_healthy()),
                "degraded": sum(1 for c in self.components.values() if c.is_degraded()),
                "unhealthy": sum(1 for c in self.components.values() if not c.is_healthy() and not c.is_degraded()),
            }
        }


# ==================== Health Check Functions ====================

def check_sqlite_health(database_url: str) -> ComponentHealth:
    """
    Check SQLite database health.
    
    Args:
        database_url: SQLite database URL
        
    Returns:
        ComponentHealth: Database health status
    """
    import sqlite3
    
    component = ComponentHealth("sqlite")
    start_time = time.time()
    
    try:
        # Extract path from URL
        db_path = database_url.replace("sqlite:///", "").replace("sqlite+aiosqlite:///", "")
        
        # Try to connect and execute a simple query
        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        
        response_time = (time.time() - start_time) * 1000
        component.status = HealthStatus.HEALTHY
        component.response_time_ms = response_time
        component.details = {
            "path": db_path,
            "connected": True,
        }
        
        logger.debug(f"SQLite health check passed ({response_time:.1f}ms)")
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        component.status = HealthStatus.UNHEALTHY
        component.response_time_ms = response_time
        component.details = {
            "error": str(e),
            "connected": False,
        }
        
        logger.error(f"SQLite health check failed: {e}")
    
    return component


def check_neo4j_health(uri: str, user: str, password: str, database: str = "neo4j") -> ComponentHealth:
    """
    Check Neo4j database health.
    
    Args:
        uri: Neo4j connection URI
        user: Username
        password: Password
        database: Database name
        
    Returns:
        ComponentHealth: Neo4j health status
    """
    component = ComponentHealth("neo4j")
    
    if not NEO4J_AVAILABLE:
        component.status = HealthStatus.DEGRADED
        component.details = {
            "error": "neo4j driver not installed",
            "connected": False,
        }
        logger.warning("Neo4j driver not installed, skipping health check")
        return component
    
    start_time = time.time()
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        
        # Run a simple query
        with driver.session(database=database) as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            assert record["test"] == 1
        
        driver.close()
        
        response_time = (time.time() - start_time) * 1000
        component.status = HealthStatus.HEALTHY
        component.response_time_ms = response_time
        component.details = {
            "uri": uri,
            "database": database,
            "connected": True,
        }
        
        logger.debug(f"Neo4j health check passed ({response_time:.1f}ms)")
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        component.status = HealthStatus.DEGRADED  # Degraded, not unhealthy
        component.response_time_ms = response_time
        component.details = {
            "error": str(e),
            "connected": False,
        }
        
        logger.warning(f"Neo4j health check failed (degraded): {e}")
    
    return component


def check_redis_health(host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None) -> ComponentHealth:
    """
    Check Redis health.
    
    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Redis password
        
    Returns:
        ComponentHealth: Redis health status
    """
    component = ComponentHealth("redis")
    
    if not REDIS_AVAILABLE:
        component.status = HealthStatus.DEGRADED
        component.details = {
            "error": "redis package not installed",
            "connected": False,
        }
        logger.warning("Redis package not installed, skipping health check")
        return component
    
    start_time = time.time()
    
    try:
        r = redis.Redis(host=host, port=port, db=db, password=password, socket_timeout=5)
        r.ping()
        
        # Get Redis info
        info = r.info()
        
        response_time = (time.time() - start_time) * 1000
        component.status = HealthStatus.HEALTHY
        component.response_time_ms = response_time
        component.details = {
            "host": host,
            "port": port,
            "db": db,
            "connected": True,
            "version": info.get("redis_version"),
            "used_memory": info.get("used_memory_human"),
            "clients": info.get("connected_clients"),
        }
        
        logger.debug(f"Redis health check passed ({response_time:.1f}ms)")
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        component.status = HealthStatus.DEGRADED  # Degraded
        component.response_time_ms = response_time
        component.details = {
            "error": str(e),
            "connected": False,
        }
        
        logger.warning(f"Redis health check failed (degraded): {e}")
    
    return component


def check_memory_health() -> ComponentHealth:
    """
    Check memory system health.
    
    Returns:
        ComponentHealth: Memory system health status
    """
    component = ComponentHealth("memory")
    start_time = time.time()
    
    try:
        from backend.memory import get_memory_manager
        
        memory_mgr = get_memory_manager()
        stats = memory_mgr.get_stats()
        
        response_time = (time.time() - start_time) * 1000
        component.status = HealthStatus.HEALTHY
        component.response_time_ms = response_time
        component.details = {
            "stats": stats,
            "operational": True,
        }
        
        logger.debug(f"Memory health check passed ({response_time:.1f}ms)")
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        component.status = HealthStatus.DEGRADED
        component.response_time_ms = response_time
        component.details = {
            "error": str(e),
            "operational": False,
        }
        
        logger.warning(f"Memory health check failed (degraded): {e}")
    
    return component


def check_disk_space(path: str = ".", threshold_percent: float = 90.0) -> ComponentHealth:
    """
    Check disk space.
    
    Args:
        path: Path to check
        threshold_percent: Alert threshold percentage
        
    Returns:
        ComponentHealth: Disk space health status
    """
    component = ComponentHealth("disk")
    
    try:
        import shutil
        
        total, used, free = shutil.disk_usage(path)
        used_percent = (used / total) * 100
        
        component.details = {
            "path": path,
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "used_percent": round(used_percent, 2),
        }
        
        if used_percent >= threshold_percent:
            component.status = HealthStatus.DEGRADED
            component.details["warning"] = f"Disk usage above {threshold_percent}%"
        else:
            component.status = HealthStatus.HEALTHY
        
        logger.debug(f"Disk space check: {used_percent:.1f}% used")
        
    except Exception as e:
        component.status = HealthStatus.DEGRADED
        component.details = {
            "error": str(e),
        }
        
        logger.warning(f"Disk space check failed: {e}")
    
    return component


# ==================== Enhanced Health Check Endpoint Handler ====================

def enhanced_health_check(
    settings,
    include_details: bool = True
) -> Dict[str, Any]:
    """
    Perform comprehensive health check.
    
    Args:
        settings: Application settings object
        include_details: Whether to include detailed component info
        
    Returns:
        dict: Complete health status dictionary
    """
    system_health = SystemHealth(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION
    )
    
    # Check SQLite
    sqlite_health = check_sqlite_health(settings.SQLITE_URL)
    system_health.add_component("sqlite", sqlite_health)
    
    # Check Neo4j
    neo4j_health = check_neo4j_health(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )
    system_health.add_component("neo4j", neo4j_health)
    
    # Check Redis (optional)
    if hasattr(settings, 'REDIS_HOST'):
        redis_health = check_redis_health(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD
        )
        system_health.add_component("redis", redis_health)
    
    # Check Memory system
    memory_health = check_memory_health()
    system_health.add_component("memory", memory_health)
    
    # Check Disk space
    disk_health = check_disk_space()
    system_health.add_component("disk", disk_health)
    
    # Get overall status
    result = system_health.to_dict()
    
    # Add additional metadata
    result["environment"] = settings.ENVIRONMENT
    result["debug"] = settings.DEBUG
    
    logger.info(f"Health check: {result['status']} (components: {result['summary']['healthy']}/{result['summary']['total_components']} healthy)")
    
    return result


# ==================== FastAPI Endpoint Integration ====================

def create_health_endpoint(app, settings):
    """
    Create /health endpoint with enhanced health check.
    
    Usage:
        from monitoring.health import create_health_endpoint
        create_health_endpoint(app, settings)
    """
    @app.get(
        "/health",
        tags=["System"],
        summary="Enhanced health check",
        description="""
        Comprehensive health check for all system components.
        
        Returns detailed status of:
        - SQLite database
        - Neo4j database
        - Redis (if configured)
        - Memory system
        - Disk space
        
        Status levels:
        - 'healthy': All components operational
        - 'degraded': Some components impaired but service functional
        - 'unhealthy': Critical components failed
        
        Returns:
            dict: Complete health status with component details
        
        Example Response:
            {
                "status": "healthy",
                "app_name": "SerpentAI",
                "app_version": "0.1.0-alpha",
                "uptime_seconds": 3600.5,
                "components": {
                    "sqlite": {"status": "healthy", ...},
                    "neo4j": {"status": "healthy", ...},
                    ...
                },
                "summary": {
                    "total_components": 5,
                    "healthy": 5,
                    "degraded": 0,
                    "unhealthy": 0
                }
            }
        """
    )
    async def health_endpoint():
        return enhanced_health_check(settings)
    
    logger.info("Enhanced /health endpoint created")
