"""
SerpentAI Security Module - 多层安全防御系统
实现完整的安全架构，保护智能体免受各种威胁
"""

from .input_guard import InputGuard, ValidationResult
from .auth import AuthManager, Session, Token
from .access_control import AccessControl, Permission, Role
from .audit_logger import AuditLogger, AuditEvent, AuditLevel
from .rate_limiter import RateLimiter, RateLimitResult

__all__ = [
    # 输入安全
    "InputGuard",
    "ValidationResult",
    
    # 认证授权
    "AuthManager",
    "Session",
    "Token",
    
    # 访问控制
    "AccessControl",
    "Permission",
    "Role",
    
    # 审计日志
    "AuditLogger",
    "AuditEvent",
    "AuditLevel",
    
    # 速率限制
    "RateLimiter",
    "RateLimitResult",
]

# 全局实例
_auth_manager = None
_access_control = None
_audit_logger = None
_rate_limiter = None


def get_auth_manager() -> AuthManager:
    """获取认证管理器单例"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def get_access_control() -> AccessControl:
    """获取访问控制器单例"""
    global _access_control
    if _access_control is None:
        _access_control = AccessControl()
    return _access_control


def get_audit_logger() -> AuditLogger:
    """获取审计日志器单例"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def get_rate_limiter() -> RateLimiter:
    """获取速率限制器单例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def get_input_guard() -> InputGuard:
    """获取输入守卫单例"""
    return InputGuard()


def security_check(
    operation: str,
    user_id: str = None,
    resource: str = None,
    input_data: dict = None,
    session_id: str = None
) -> tuple[bool, str]:
    """
    完整安全检查流程
    
    5层防御：
    1. 输入验证 (InputGuard)
    2. 速率限制 (RateLimiter)
    3. 认证 (AuthManager)
    4. 授权 (AccessControl)
    5. 审计 (AuditLogger)
    
    Args:
        operation: 操作类型
        user_id: 用户ID
        resource: 资源路径
        input_data: 输入数据
        session_id: 会话ID
    
    Returns:
        (allowed, reason): 是否允许，失败原因
    """
    audit = get_audit_logger()
    
    # Layer 1: 输入验证
    if input_data:
        guard = get_input_guard()
        validation = guard.validate_all(input_data)
        if not validation.is_valid:
            audit.log(
                event_type="SECURITY_BLOCK",
                user_id=user_id,
                details={"operation": operation, "reason": "input_validation_failed", "errors": validation.errors},
                level=AuditLevel.WARN
            )
            return False, f"输入验证失败: {validation.errors}"
    
    # Layer 2: 速率限制
    limiter = get_rate_limiter()
    if user_id:
        rate_result = limiter.check(user_id, operation)
        if not rate_result.allowed:
            audit.log(
                event_type="RATE_LIMITED",
                user_id=user_id,
                details={"operation": operation, "reason": "rate_limit_exceeded"},
                level=AuditLevel.WARN
            )
            return False, f"速率限制: {rate_result.retry_after}s 后重试"
    
    # Layer 3: 认证检查
    if user_id:
        auth = get_auth_manager()
        if not auth.is_authenticated(user_id):
            audit.log(
                event_type="AUTH_FAILURE",
                user_id=user_id,
                details={"operation": operation, "reason": "not_authenticated"},
                level=AuditLevel.WARN
            )
            return False, "未认证"
    
    # Layer 4: 授权检查
    if user_id and resource:
        ac = get_access_control()
        if not ac.check_permission(user_id, operation, resource):
            audit.log(
                event_type="ACCESS_DENIED",
                user_id=user_id,
                details={"operation": operation, "resource": resource, "reason": "permission_denied"},
                level=AuditLevel.WARN
            )
            return False, "权限不足"
    
    # Layer 5: 审计日志（记录成功操作）
    audit.log(
        event_type="OPERATION_SUCCESS",
        user_id=user_id,
        details={"operation": operation, "resource": resource, "session_id": session_id},
        level=AuditLevel.INFO
    )
    
    return True, "OK"
