"""
SerpentAI 安全模块 - 认证管理 (Layer 3)
JWT Token认证、会话管理
"""

import secrets
import hashlib
import time
import base64
import hmac
import struct
import pyotp
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import logging

from core.encryption import encrypt_data, decrypt_data, hash_password, verify_password

logger = logging.getLogger(__name__)


@dataclass
class Token:
    """访问令牌"""
    token: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    scopes: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        return not self.is_expired


@dataclass
class Session:
    """用户会话"""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        # 会话30分钟无活动则过期
        return datetime.now() > self.last_activity + timedelta(minutes=30)


@dataclass
class MFAConfig:
    """MFA配置"""
    enabled: bool = False
    totp_secret: Optional[str] = None
    backup_codes: List[str] = field(default_factory=list)
    verified: bool = False

@dataclass
class APIKey:
    """API密钥"""
    key_id: str
    key_hash: str  # SHA-256哈希，不存储明文
    user_id: str
    name: str
    scopes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class AuthManager:
    """
    认证管理器 - 第三层防御
    功能：
    1. 用户注册和登录
    2. Token生成和验证
    3. 会话管理
    4. 密码重置
    5. MFA多因素认证
    6. API Key认证
    """
    
    def __init__(self):
        # 内存存储（生产环境应使用数据库）
        self._users: Dict[str, dict] = {}  # user_id -> user_data
        self._tokens: Dict[str, Token] = {}  # token -> Token
        self._sessions: Dict[str, Session] = {}  # session_id -> Session
        self._login_attempts: Dict[str, dict] = {}  # user_id -> {attempts, locked_until}
        self._mfa_configs: Dict[str, MFAConfig] = {}  # user_id -> MFAConfig
        self._api_keys: Dict[str, APIKey] = {}  # key_id -> APIKey
        self._pending_mfa: Dict[str, dict] = {}  # token -> {user_id, created_at}
        
        # 配置
        self.token_expiry_hours = 24
        self.max_login_attempts = 5
        self.lockout_duration_minutes = 15
        
        logger.info("认证管理器初始化完成")
    
    # ==================== 用户管理 ====================
    
    def register_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> tuple[bool, str]:
        """
        注册新用户
        
        Returns:
            (success, message)
        """
        # 检查用户名是否已存在
        for user in self._users.values():
            if user.get("username") == username:
                return False, "用户名已存在"
            if email and user.get("email") == email:
                return False, "邮箱已被注册"
        
        # 生成用户ID
        user_id = secrets.token_urlsafe(16)
        
        # 密码哈希
        password_hash = hash_password(password)
        
        # 创建用户
        self._users[user_id] = {
            "user_id": user_id,
            "username": username,
            "password_hash": password_hash,
            "email": email,
            "created_at": datetime.now().isoformat(),
            "is_active": True,
            "is_verified": False,
            "metadata": metadata or {}
        }
        
        logger.info(f"用户注册成功: {username} ({user_id})")
        
        return True, user_id
    
    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> tuple[bool, str, Optional[Token]]:
        """
        用户登录认证
        
        Returns:
            (success, message, token)
        """
        # 查找用户
        user = None
        user_id = None
        for uid, u in self._users.items():
            if u.get("username") == username:
                user = u
                user_id = uid
                break
        
        if not user:
            return False, "用户名或密码错误", None
        
        # 检查账户是否被锁定
        if user_id in self._login_attempts:
            attempts = self._login_attempts[user_id]
            if attempts["locked_until"] and datetime.now() < attempts["locked_until"]:
                remaining = (attempts["locked_until"] - datetime.now()).seconds // 60
                return False, f"账户已被锁定，请在 {remaining} 分钟后重试", None
        
        # 验证密码
        if not verify_password(password, user["password_hash"]):
            # 记录失败尝试
            self._record_failed_attempt(user_id)
            return False, "用户名或密码错误", None
        
        # 登录成功，清除失败记录
        if user_id in self._login_attempts:
            del self._login_attempts[user_id]
        
        # 生成Token
        token = self._generate_token(user_id)
        
        # 创建会话
        session = self._create_session(user_id, ip_address)
        
        logger.info(f"用户登录成功: {username}")
        
        return True, "登录成功", token
    
    def _record_failed_attempt(self, user_id: str):
        """记录失败的登录尝试"""
        if user_id not in self._login_attempts:
            self._login_attempts[user_id] = {
                "attempts": 0,
                "locked_until": None
            }
        
        self._login_attempts[user_id]["attempts"] += 1
        
        if self._login_attempts[user_id]["attempts"] >= self.max_login_attempts:
            self._login_attempts[user_id]["locked_until"] = datetime.now() + timedelta(
                minutes=self.lockout_duration_minutes
            )
            logger.warning(f"用户 {user_id} 因多次登录失败被锁定")
    
    def logout(self, token: str) -> bool:
        """用户登出"""
        if token in self._tokens:
            user_id = self._tokens[token].user_id
            
            # 清除Token
            del self._tokens[token]
            
            # 清除会话
            sessions_to_remove = [
                sid for sid, s in self._sessions.items()
                if s.user_id == user_id
            ]
            for sid in sessions_to_remove:
                del self._sessions[sid]
            
            logger.info(f"用户登出: {user_id}")
            return True
        
        return False
    
    def is_authenticated(self, user_id: str) -> bool:
        """检查用户是否已认证（当前会话有效）"""
        for session in self._sessions.values():
            if session.user_id == user_id and not session.is_expired:
                return True
        return False
    
    # ==================== Token管理 ====================
    
    def _generate_token(self, user_id: str, scopes: List[str] = None) -> Token:
        """生成访问令牌"""
        token_str = secrets.token_urlsafe(32)
        
        token = Token(
            token=token_str,
            user_id=user_id,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=self.token_expiry_hours),
            scopes=scopes or ["read", "write"]
        )
        
        self._tokens[token_str] = token
        return token
    
    def verify_token(self, token_str: str) -> tuple[bool, Optional[str], Optional[Token]]:
        """
        验证Token
        
        Returns:
            (is_valid, user_id, token)
        """
        token = self._tokens.get(token_str)
        
        if not token:
            return False, None, None
        
        if token.is_expired:
            # 删除过期Token
            del self._tokens[token_str]
            return False, None, None
        
        return True, token.user_id, token
    
    def refresh_token(self, token_str: str) -> tuple[bool, Optional[Token]]:
        """
        刷新Token
        
        Returns:
            (success, new_token)
        """
        is_valid, user_id, old_token = self.verify_token(token_str)
        
        if not is_valid:
            return False, None
        
        # 删除旧Token
        del self._tokens[token_str]
        
        # 生成新Token
        new_token = self._generate_token(user_id, old_token.scopes)
        
        logger.info(f"Token刷新成功: {user_id}")
        
        return True, new_token
    
    def revoke_token(self, token_str: str) -> bool:
        """撤销Token"""
        if token_str in self._tokens:
            del self._tokens[token_str]
            logger.info(f"Token已撤销")
            return True
        return False
    
    # ==================== 会话管理 ====================
    
    def _create_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Session:
        """创建新会话"""
        session_id = secrets.token_urlsafe(32)
        
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self._sessions[session_id] = session
        return session
    
    def update_session_activity(self, session_id: str) -> bool:
        """更新会话活跃时间"""
        if session_id in self._sessions:
            self._sessions[session_id].last_activity = datetime.now()
            return True
        return False
    
    def get_user_sessions(self, user_id: str) -> List[Session]:
        """获取用户的所有会话"""
        return [
            s for s in self._sessions.values()
            if s.user_id == user_id
        ]
    
    def terminate_session(self, session_id: str) -> bool:
        """终止会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def terminate_all_sessions(self, user_id: str) -> int:
        """终止用户所有会话"""
        sessions_to_remove = [
            sid for sid, s in self._sessions.items()
            if s.user_id == user_id
        ]
        
        for sid in sessions_to_remove:
            del self._sessions[sid]
        
        logger.info(f"终止用户 {user_id} 的 {len(sessions_to_remove)} 个会话")
        
        return len(sessions_to_remove)
    
    # ==================== 用户查询 ====================
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        return self._users.get(user_id)
    
    def list_users(self, limit: int = 100) -> List[Dict]:
        """列出用户（不包含密码）"""
        users = []
        for user in list(self._users.values())[:limit]:
            user_copy = user.copy()
            user_copy.pop("password_hash", None)
            users.append(user_copy)
        return users
    
    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        if user_id in self._users:
            # 终止所有会话
            self.terminate_all_sessions(user_id)
            
            # 撤销所有Token
            tokens_to_remove = [
                t for t, token in self._tokens.items()
                if token.user_id == user_id
            ]
            for t in tokens_to_remove:
                del self._tokens[t]
            
            # 删除用户
            del self._users[user_id]
            
            logger.info(f"用户已删除: {user_id}")
            return True
        
        return False
    
    def update_user(self, user_id: str, updates: Dict) -> bool:
        """更新用户信息"""
        if user_id in self._users:
            # 不允许更新密码和user_id
            updates.pop("password_hash", None)
            updates.pop("user_id", None)
            
            self._users[user_id].update(updates)
            logger.info(f"用户已更新: {user_id}")
            return True
        
        return False

    # ==================== MFA 多因素认证 ====================

    def setup_mfa(self, user_id: str) -> Tuple[str, str]:
        """
        为用户设置MFA（TOTP）
        
        Returns:
            (totp_secret, provisioning_uri)
        """
        if user_id not in self._users:
            raise ValueError("用户不存在")
        
        totp_secret = pyotp.random_base32()
        username = self._users[user_id]["username"]
        totp = pyotp.TOTP(totp_secret)
        provisioning_uri = totp.provisioning_uri(name=username, issuer_name="SerpentAI")
        
        # 生成备用恢复码
        backup_codes = [secrets.token_urlsafe(8) for _ in range(10)]
        
        self._mfa_configs[user_id] = MFAConfig(
            enabled=False,  # 需要验证后启用
            totp_secret=totp_secret,
            backup_codes=backup_codes,
            verified=False
        )
        
        logger.info(f"MFA设置已初始化: {user_id}")
        return totp_secret, provisioning_uri

    def verify_mfa_setup(self, user_id: str, code: str) -> Tuple[bool, str]:
        """
        验证MFA设置（用户输入TOTP码确认设置）
        
        Returns:
            (success, message)
        """
        if user_id not in self._mfa_configs:
            return False, "MFA未初始化"
        
        config = self._mfa_configs[user_id]
        if self._verify_totp_code(config.totp_secret, code):
            config.enabled = True
            config.verified = True
            logger.info(f"MFA验证成功并已启用: {user_id}")
            return True, "MFA已启用"
        
        return False, "验证码无效"

    def verify_mfa(self, user_id: str, code: str) -> Tuple[bool, str]:
        """
        验证MFA代码（登录时使用）
        
        Returns:
            (success, message)
        """
        if user_id not in self._mfa_configs:
            return False, "MFA未设置"
        
        config = self._mfa_configs[user_id]
        
        if not config.enabled:
            return False, "MFA未启用"
        
        # 检查TOTP
        if self._verify_totp_code(config.totp_secret, code):
            return True, "MFA验证通过"
        
        # 检查备用码
        if code in config.backup_codes:
            config.backup_codes.remove(code)  # 备用码一次性使用
            logger.info(f"使用备用码验证MFA成功: {user_id}")
            return True, "备用码验证通过（已消耗）"
        
        return False, "MFA验证码无效"

    def disable_mfa(self, user_id: str, password: str) -> Tuple[bool, str]:
        """禁用MFA（需验证密码）"""
        if user_id not in self._users:
            return False, "用户不存在"
        
        if not verify_password(password, self._users[user_id]["password_hash"]):
            return False, "密码验证失败"
        
        if user_id in self._mfa_configs:
            del self._mfa_configs[user_id]
            logger.info(f"MFA已禁用: {user_id}")
            return True, "MFA已禁用"
        
        return True, "MFA未设置"

    def _verify_totp_code(self, secret: str, code: str) -> bool:
        """验证TOTP代码"""
        totp = pyotp.TOTP(secret)
        # 允许前后各1个时间窗口（共3个窗口，30秒窗口期）
        return totp.verify(code, valid_window=1)

    def get_mfa_status(self, user_id: str) -> Optional[Dict]:
        """获取用户MFA状态"""
        if user_id not in self._mfa_configs:
            return {"enabled": False, "configured": False}
        
        config = self._mfa_configs[user_id]
        return {
            "enabled": config.enabled,
            "configured": True,
            "verified": config.verified,
            "backup_codes_remaining": len(config.backup_codes)
        }

    # ==================== MFA 感知的登录流程 ====================

    def authenticate_with_mfa(
        self,
        username: str,
        password: str,
        mfa_code: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Token]]:
        """
        支持MFA的登录认证
        
        如果用户启用了MFA且未提供mfa_code，返回待验证状态。
        """
        success, message, token = self.authenticate(username, password, ip_address)
        
        if not success:
            return False, message, None
        
        # 查找user_id
        user_id = None
        for uid, u in self._users.items():
            if u.get("username") == username:
                user_id = uid
                break
        
        # 检查是否需要MFA
        if user_id in self._mfa_configs and self._mfa_configs[user_id].enabled:
            if mfa_code is None:
                # 暂停token，等待MFA验证
                pending_token = token.token
                self._pending_mfa[pending_token] = {
                    "user_id": user_id,
                    "created_at": datetime.now(),
                    "token": token
                }
                return False, "MFA_REQUIRED", None
            
            mfa_ok, mfa_msg = self.verify_mfa(user_id, mfa_code)
            if not mfa_ok:
                return False, mfa_msg, None
        
        return True, "登录成功", token

    # ==================== API Key 管理 ====================

    def create_api_key(
        self,
        user_id: str,
        name: str,
        scopes: Optional[List[str]] = None,
        expires_days: Optional[int] = None
    ) -> Tuple[str, str]:
        """
        创建API Key
        
        Returns:
            (key_id, plaintext_key)  # 明文key仅返回一次
        """
        if user_id not in self._users:
            raise ValueError("用户不存在")
        
        key_id = f"sk-{secrets.token_urlsafe(24)}"
        plaintext_key = f"sk-live-{secrets.token_urlsafe(48)}"
        
        # 仅存储哈希
        key_hash = hashlib.sha256(plaintext_key.encode()).hexdigest()
        
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            scopes=scopes or ["read"],
            created_at=datetime.now(),
            expires_at=expires_at
        )
        
        self._api_keys[key_id] = api_key
        
        logger.info(f"API Key已创建: {key_id} ({name})")
        return key_id, plaintext_key

    def verify_api_key(self, plaintext_key: str) -> Tuple[bool, Optional[str], Optional[APIKey]]:
        """
        验证API Key
        
        Returns:
            (is_valid, user_id, api_key)
        """
        key_hash = hashlib.sha256(plaintext_key.encode()).hexdigest()
        
        for api_key in self._api_keys.values():
            if api_key.key_hash == key_hash:
                if not api_key.is_active:
                    return False, None, None
                if api_key.is_expired:
                    return False, None, None
                
                api_key.last_used = datetime.now()
                return True, api_key.user_id, api_key
        
        return False, None, None

    def revoke_api_key(self, key_id: str) -> bool:
        """撤销API Key"""
        if key_id in self._api_keys:
            self._api_keys[key_id].is_active = False
            logger.info(f"API Key已撤销: {key_id}")
            return True
        return False

    def list_api_keys(self, user_id: str) -> List[Dict]:
        """列出用户的API Key（不包含明文密钥）"""
        result = []
        for api_key in self._api_keys.values():
            if api_key.user_id == user_id:
                result.append({
                    "key_id": api_key.key_id,
                    "name": api_key.name,
                    "scopes": api_key.scopes,
                    "created_at": api_key.created_at.isoformat(),
                    "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
                    "last_used": api_key.last_used.isoformat() if api_key.last_used else None,
                    "is_active": api_key.is_active,
                    "is_expired": api_key.is_expired
                })
        return result

    # ==================== 密码管理 ====================

    def change_password(self, user_id: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """修改密码"""
        if user_id not in self._users:
            return False, "用户不存在"
        
        if not verify_password(old_password, self._users[user_id]["password_hash"]):
            return False, "原密码错误"
        
        password_hash = hash_password(new_password)
        self._users[user_id]["password_hash"] = password_hash
        
        # 密码变更后终止所有会话
        self.terminate_all_sessions(user_id)
        
        logger.info(f"密码已修改: {user_id}")
        return True, "密码修改成功"

    def reset_password(self, user_id: str, new_password: str) -> Tuple[bool, str]:
        """管理员重置密码"""
        if user_id not in self._users:
            return False, "用户不存在"
        
        password_hash = hash_password(new_password)
        self._users[user_id]["password_hash"] = password_hash
        self.terminate_all_sessions(user_id)
        
        logger.info(f"密码已重置: {user_id}")
        return True, "密码已重置"
