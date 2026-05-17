"""
SerpentAI 安全模块 - 访问控制 (Layer 4)
基于RBAC的权限管理
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional
import logging

logger = logging.getLogger(__name__)


class Permission(Enum):
    """权限枚举"""
    # 工具权限
    TOOL_READ = "tool:read"
    TOOL_WRITE = "tool:write"
    TOOL_EXECUTE = "tool:execute"
    TOOL_DELETE = "tool:delete"
    
    # 记忆权限
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_DELETE = "memory:delete"
    
    # 智能体权限
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_WRITE = "agent:write"
    AGENT_DELETE = "agent:delete"
    
    # 模型权限
    MODEL_CALL = "model:call"
    MODEL_CONFIG = "model:config"
    
    # 用户权限
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_ADMIN = "user:admin"
    
    # 系统权限
    SYSTEM_CONFIG = "system:config"
    SYSTEM_LOG = "system:log"
    SYSTEM_AUDIT = "system:audit"
    SYSTEM_ALL = "system:all"


class Role(Enum):
    """角色枚举"""
    ADMIN = "admin"           # 管理员 - 所有权限
    OPERATOR = "operator"     # 操作员 - 日常操作
    DEVELOPER = "developer"   # 开发者 - 工具开发和调试
    USER = "user"             # 普通用户 - 基本使用
    GUEST = "guest"           # 访客 - 只读权限
    
    # 子智能体角色
    AGENT = "agent"           # 子智能体 - 工具执行
    PLUGIN = "plugin"         # 插件 - 受限权限


@dataclass
class RolePermissions:
    """角色权限配置"""
    name: str
    permissions: Set[Permission]
    inherits_from: Optional[str] = None
    description: str = ""


class AccessControl:
    """
    访问控制器 - 第四层防御
    基于RBAC（Role-Based Access Control）的权限管理
    """
    
    # 默认角色权限配置
    DEFAULT_ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
        Role.ADMIN.value: {
            # 所有权限
            Permission.SYSTEM_ALL,
            Permission.USER_ADMIN,
        },
        Role.OPERATOR.value: {
            # 操作员：工具执行、记忆读写、智能体操作
            Permission.TOOL_READ,
            Permission.TOOL_EXECUTE,
            Permission.MEMORY_READ,
            Permission.MEMORY_WRITE,
            Permission.AGENT_CREATE,
            Permission.AGENT_READ,
            Permission.AGENT_WRITE,
            Permission.MODEL_CALL,
        },
        Role.DEVELOPER.value: {
            # 开发者：完整的工具管理
            Permission.TOOL_READ,
            Permission.TOOL_WRITE,
            Permission.TOOL_EXECUTE,
            Permission.TOOL_DELETE,
            Permission.MEMORY_READ,
            Permission.MEMORY_WRITE,
            Permission.AGENT_READ,
            Permission.MODEL_CALL,
            Permission.MODEL_CONFIG,
            Permission.SYSTEM_LOG,
        },
        Role.USER.value: {
            # 普通用户：基本使用
            Permission.TOOL_READ,
            Permission.TOOL_EXECUTE,
            Permission.MEMORY_READ,
            Permission.MEMORY_WRITE,
            Permission.AGENT_CREATE,
            Permission.AGENT_READ,
            Permission.MODEL_CALL,
        },
        Role.GUEST.value: {
            # 访客：只读
            Permission.TOOL_READ,
            Permission.AGENT_READ,
        },
        Role.AGENT.value: {
            # 子智能体：受限的工具执行
            Permission.TOOL_READ,
            Permission.TOOL_EXECUTE,
            Permission.MEMORY_READ,
            Permission.MODEL_CALL,
        },
        Role.PLUGIN.value: {
            # 插件：最小权限
            Permission.TOOL_READ,
            Permission.TOOL_EXECUTE,
        },
    }
    
    def __init__(self):
        # 角色 -> 权限映射
        self._role_permissions: Dict[str, Set[Permission]] = {}
        
        # 用户 -> 角色映射
        self._user_roles: Dict[str, Set[str]] = {}
        
        # 用户自定义权限
        self._user_permissions: Dict[str, Set[Permission]] = {}
        
        # 资源权限配置
        self._resource_permissions: Dict[str, Set[Permission]] = {}
        
        # 初始化默认角色
        for role, permissions in self.DEFAULT_ROLE_PERMISSIONS.items():
            self._role_permissions[role] = permissions.copy()
        
        logger.info("访问控制器初始化完成")
    
    def assign_role(self, user_id: str, role: str) -> bool:
        """
        为用户分配角色
        
        Args:
            user_id: 用户ID
            role: 角色名称
        
        Returns:
            bool: 是否成功
        """
        if role not in self._role_permissions:
            logger.warning(f"角色不存在: {role}")
            return False
        
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()
        
        self._user_roles[user_id].add(role)
        
        logger.info(f"用户 {user_id} 被分配角色 {role}")
        return True
    
    def revoke_role(self, user_id: str, role: str) -> bool:
        """撤销用户角色"""
        if user_id in self._user_roles and role in self._user_roles[user_id]:
            self._user_roles[user_id].remove(role)
            logger.info(f"用户 {user_id} 的角色 {role} 已被撤销")
            return True
        return False
    
    def get_user_roles(self, user_id: str) -> Set[str]:
        """获取用户的所有角色"""
        return self._user_roles.get(user_id, set())
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """
        获取用户的所有权限（包含所有角色的权限并集）
        """
        permissions = set()
        
        # 添加角色权限
        roles = self.get_user_roles(user_id)
        for role in roles:
            if role in self._role_permissions:
                permissions.update(self._role_permissions[role])
        
        # 添加自定义权限
        if user_id in self._user_permissions:
            permissions.update(self._user_permissions[user_id])
        
        return permissions
    
    def check_permission(
        self,
        user_id: str,
        operation: str,
        resource: str = None
    ) -> bool:
        """
        检查用户是否有权限执行操作
        
        Args:
            user_id: 用户ID
            operation: 操作类型（如 "tool:execute", "memory:read"）
            resource: 资源路径（可选）
        
        Returns:
            bool: 是否有权限
        """
        # 超级管理员
        if user_id == "admin":
            return True
        
        # 获取用户权限
        permissions = self.get_user_permissions(user_id)
        
        # 检查 SYSTEM_ALL 权限
        if Permission.SYSTEM_ALL in permissions:
            return True
        
        # 解析操作
        try:
            op_permission = Permission(operation)
        except ValueError:
            # 尝试动态创建权限
            op_permission = Permission(operation)
        
        # 检查权限
        has_permission = op_permission in permissions
        
        if not has_permission:
            logger.warning(
                f"权限不足 | 用户: {user_id} | 操作: {operation} | 资源: {resource}"
            )
        
        return has_permission
    
    def check_resource_access(
        self,
        user_id: str,
        resource: str,
        access_type: str = "read"
    ) -> bool:
        """
        检查用户对特定资源的访问权限
        
        Args:
            user_id: 用户ID
            resource: 资源路径
            access_type: 访问类型 (read/write/delete)
        """
        # 超级管理员可以访问所有资源
        if user_id == "admin":
            return True
        
        # 检查资源是否有特殊权限配置
        if resource in self._resource_permissions:
            required_permission = Permission(f"{access_type}:resource")
            permissions = self.get_user_permissions(user_id)
            return required_permission in permissions
        
        # 默认允许读，限制写和删除
        if access_type == "read":
            return self.check_permission(user_id, "memory:read")
        elif access_type == "write":
            return self.check_permission(user_id, "memory:write")
        elif access_type == "delete":
            return self.check_permission(user_id, "memory:delete")
        
        return False
    
    def require_permission(self, user_id: str, permission: str):
        """
        权限检查装饰器
        
        Usage:
            @require_permission("tool:execute")
            def execute_tool(tool_name):
                ...
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                if not self.check_permission(user_id, permission):
                    raise PermissionError(f"权限不足: {permission}")
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    # ==================== 角色管理 ====================
    
    def create_role(self, role_name: str, permissions: Set[Permission], description: str = ""):
        """创建自定义角色"""
        if role_name in self._role_permissions:
            raise ValueError(f"角色已存在: {role_name}")
        
        self._role_permissions[role_name] = permissions
        logger.info(f"自定义角色已创建: {role_name}")
    
    def delete_role(self, role_name: str) -> bool:
        """删除自定义角色（不允许删除内置角色）"""
        if role_name in [r.value for r in Role]:
            logger.warning(f"不能删除内置角色: {role_name}")
            return False
        
        if role_name not in self._role_permissions:
            return False
        
        del self._role_permissions[role_name]
        
        # 撤销所有用户的该角色
        for user_id, roles in self._user_roles.items():
            roles.discard(role_name)
        
        logger.info(f"角色已删除: {role_name}")
        return True
    
    def update_role_permissions(self, role_name: str, permissions: Set[Permission]):
        """更新角色权限"""
        if role_name not in self._role_permissions:
            raise ValueError(f"角色不存在: {role_name}")
        
        self._role_permissions[role_name] = permissions
        logger.info(f"角色权限已更新: {role_name}")
    
    def get_role_permissions(self, role_name: str) -> Set[Permission]:
        """获取角色权限"""
        return self._role_permissions.get(role_name, set())
    
    # ==================== 权限查询 ====================
    
    def list_roles(self) -> List[Dict]:
        """列出所有角色"""
        return [
            {
                "name": name,
                "permissions": [p.value for p in perms],
                "description": ""
            }
            for name, perms in self._role_permissions.items()
        ]
    
    def list_users_with_role(self, role: str) -> List[str]:
        """列出拥有特定角色的所有用户"""
        return [
            user_id for user_id, roles in self._user_roles.items()
            if role in roles
        ]
