"""
SerpentAI 多平台账号管理器
管理多个IM平台的账号认证信息，支持加密存储和账号隔离
"""
import logging
import json
import hashlib
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class AccountStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    AUTH_FAILED = "auth_failed"


@dataclass
class Account:
    """平台账号"""
    platform: str                  # 平台名称（wechat, qq, slack等）
    account_id: str                 # 账号唯一标识
    display_name: str = ""          # 显示名称
    status: AccountStatus = AccountStatus.ACTIVE
    is_default: bool = False        # 是否为该平台默认账号
    auth_data: Dict[str, Any] = field(default_factory=dict)  # 加密后的认证数据
    config: Dict[str, Any] = field(default_factory=dict)     # 平台特定配置
    created_at: str = ""
    updated_at: str = ""
    last_used_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


class AccountManager:
    """
    多平台账号管理器

    功能：
    - 账号CRUD（添加/删除/更新/查询）
    - 认证信息AES-256-GCM加密存储
    - 默认账号切换
    - 账号隔离（不同平台消息隔离）
    - OAuth2回调处理框架
    - 基于SQLite持久化
    """

    def __init__(self, db_path: Optional[str] = None, encryption_key: Optional[str] = None):
        """
        初始化账号管理器

        Args:
            db_path: SQLite数据库路径
            encryption_key: 加密密钥（用于加密认证信息）
        """
        self._accounts: Dict[str, Dict[str, Account]] = {}  # platform -> account_id -> Account
        self._default_accounts: Dict[str, str] = {}  # platform -> account_id
        self._db_path = db_path or "data/accounts.db"
        self._encryption_key = encryption_key
        self._encryptor = None
        self._db_initialized = False

        if self._encryption_key:
            self._init_encryptor()

    def _init_encryptor(self):
        """初始化加密器"""
        try:
            from core.encryption import EncryptionManager
            self._encryptor = EncryptionManager()
            self._encryptor.initialize(self._encryption_key)
        except Exception as e:
            logger.warning(f"加密器初始化失败，认证信息将明文存储: {e}")
            self._encryptor = None

    def _encrypt_data(self, data: Dict[str, Any]) -> str:
        """加密认证数据"""
        if not self._encryptor:
            return json.dumps(data)
        try:
            plaintext = json.dumps(data, ensure_ascii=False)
            encrypted = self._encryptor.encrypt(plaintext)
            return encrypted
        except Exception as e:
            logger.warning(f"加密失败: {e}")
            return json.dumps(data)

    def _decrypt_data(self, encrypted: str) -> Dict[str, Any]:
        """解密认证数据"""
        if not self._encryptor:
            try:
                return json.loads(encrypted)
            except (json.JSONDecodeError, TypeError):
                return {}
        try:
            plaintext = self._encryptor.decrypt(encrypted)
            return json.loads(plaintext)
        except Exception:
            try:
                return json.loads(encrypted)
            except (json.JSONDecodeError, TypeError):
                return {}

    def _init_db(self):
        """初始化SQLite数据库"""
        if self._db_initialized:
            return
        try:
            import sqlite3
            import os
            os.makedirs(os.path.dirname(self._db_path) if os.path.dirname(self._db_path) else "data", exist_ok=True)
            conn = sqlite3.connect(self._db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    platform TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    display_name TEXT DEFAULT '',
                    status TEXT DEFAULT 'active',
                    is_default INTEGER DEFAULT 0,
                    auth_data TEXT DEFAULT '{}',
                    config TEXT DEFAULT '{}',
                    created_at TEXT,
                    updated_at TEXT,
                    last_used_at TEXT,
                    PRIMARY KEY (platform, account_id)
                )
            """)
            conn.commit()
            conn.close()
            self._db_initialized = True
            logger.info("账号数据库初始化成功")
        except Exception as e:
            logger.warning(f"账号数据库初始化失败，使用内存存储: {e}")

    def _load_from_db(self):
        """从数据库加载账号"""
        self._init_db()
        if not self._db_initialized:
            return
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM accounts").fetchall()
            conn.close()
            for row in rows:
                account = Account(
                    platform=row["platform"],
                    account_id=row["account_id"],
                    display_name=row["display_name"] or "",
                    status=AccountStatus(row["status"] or "active"),
                    is_default=bool(row["is_default"]),
                    auth_data=self._decrypt_data(row["auth_data"] or "{}"),
                    config=json.loads(row["config"] or "{}"),
                    created_at=row["created_at"] or "",
                    updated_at=row["updated_at"] or "",
                    last_used_at=row["last_used_at"] or "",
                )
                self._accounts.setdefault(account.platform, {})[account.account_id] = account
                if account.is_default:
                    self._default_accounts[account.platform] = account.account_id
        except Exception as e:
            logger.warning(f"从数据库加载账号失败: {e}")

    def _save_account_to_db(self, account: Account):
        """保存账号到数据库"""
        self._init_db()
        if not self._db_initialized:
            return
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.execute("""
                INSERT OR REPLACE INTO accounts
                (platform, account_id, display_name, status, is_default, auth_data, config, created_at, updated_at, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                account.platform, account.account_id, account.display_name,
                account.status.value, int(account.is_default),
                self._encrypt_data(account.auth_data),
                json.dumps(account.config, ensure_ascii=False),
                account.created_at, account.updated_at, account.last_used_at,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"保存账号到数据库失败: {e}")

    def _delete_account_from_db(self, platform: str, account_id: str):
        """从数据库删除账号"""
        self._init_db()
        if not self._db_initialized:
            return
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.execute("DELETE FROM accounts WHERE platform = ? AND account_id = ?",
                         (platform, account_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"从数据库删除账号失败: {e}")

    def add_account(self, platform: str, account_id: str,
                    display_name: str = "", auth_data: Optional[Dict] = None,
                    config: Optional[Dict] = None, set_as_default: bool = False) -> Account:
        """
        添加平台账号

        Args:
            platform: 平台名称
            account_id: 账号唯一标识
            display_name: 显示名称
            auth_data: 认证信息（API Key、Token等）
            config: 平台特定配置
            set_as_default: 是否设为默认账号

        Returns:
            Account: 创建的账号对象
        """
        # 延迟加载
        if not self._accounts and not self._db_initialized:
            self._load_from_db()

        if platform in self._accounts and account_id in self._accounts[platform]:
            raise ValueError(f"账号已存在: {platform}/{account_id}")

        # 如果设为默认，先清除该平台其他默认标记
        if set_as_default and platform in self._accounts:
            for acc in self._accounts[platform].values():
                if acc.is_default:
                    acc.is_default = False

        account = Account(
            platform=platform,
            account_id=account_id,
            display_name=display_name or account_id,
            auth_data=auth_data or {},
            config=config or {},
            is_default=set_as_default or (platform not in self._default_accounts),
        )

        self._accounts.setdefault(platform, {})[account_id] = account
        if account.is_default:
            self._default_accounts[platform] = account_id

        self._save_account_to_db(account)
        logger.info(f"账号已添加: {platform}/{account_id}")
        return account

    def remove_account(self, platform: str, account_id: str) -> bool:
        """
        删除平台账号

        Args:
            platform: 平台名称
            account_id: 账号ID

        Returns:
            bool: 是否成功删除
        """
        if platform not in self._accounts or account_id not in self._accounts[platform]:
            logger.warning(f"账号不存在: {platform}/{account_id}")
            return False

        del self._accounts[platform][account_id]
        self._delete_account_from_db(platform, account_id)

        # 清理默认账号
        if self._default_accounts.get(platform) == account_id:
            del self._default_accounts[platform]
            # 设置新的默认账号
            remaining = self._accounts.get(platform, {})
            if remaining:
                first_key = next(iter(remaining))
                remaining[first_key].is_default = True
                self._default_accounts[platform] = first_key
                self._save_account_to_db(remaining[first_key])

        logger.info(f"账号已删除: {platform}/{account_id}")
        return True

    def get_account(self, platform: str, account_id: str) -> Optional[Account]:
        """获取指定账号"""
        if not self._accounts and not self._db_initialized:
            self._load_from_db()
        return self._accounts.get(platform, {}).get(account_id)

    def get_default_account(self, platform: str) -> Optional[Account]:
        """获取平台默认账号"""
        if not self._accounts and not self._db_initialized:
            self._load_from_db()
        aid = self._default_accounts.get(platform)
        if aid:
            return self._accounts.get(platform, {}).get(aid)
        # 无默认则返回第一个
        platform_accounts = self._accounts.get(platform, {})
        if platform_accounts:
            return next(iter(platform_accounts.values()))
        return None

    def set_default_account(self, platform: str, account_id: str) -> bool:
        """设置平台默认账号"""
        if platform not in self._accounts or account_id not in self._accounts[platform]:
            return False
        # 清除旧默认
        old = self._default_accounts.get(platform)
        if old and old in self._accounts.get(platform, {}):
            self._accounts[platform][old].is_default = False
            self._save_account_to_db(self._accounts[platform][old])
        # 设置新默认
        self._accounts[platform][account_id].is_default = True
        self._default_accounts[platform] = account_id
        self._save_account_to_db(self._accounts[platform][account_id])
        return True

    def list_accounts(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出账号（不包含认证信息）

        Args:
            platform: 平台名称（不指定则列出所有平台）

        Returns:
            账号信息列表
        """
        if not self._accounts and not self._db_initialized:
            self._load_from_db()
        result = []
        platforms = [platform] if platform else list(self._accounts.keys())
        for plat in platforms:
            for acc in self._accounts.get(plat, {}).values():
                result.append({
                    "platform": acc.platform,
                    "account_id": acc.account_id,
                    "display_name": acc.display_name,
                    "status": acc.status.value,
                    "is_default": acc.is_default,
                    "config": acc.config,
                    "created_at": acc.created_at,
                    "last_used_at": acc.last_used_at,
                })
        return result

    def update_auth_data(self, platform: str, account_id: str, auth_data: Dict[str, Any]) -> bool:
        """更新账号认证信息"""
        account = self.get_account(platform, account_id)
        if not account:
            return False
        account.auth_data = auth_data
        account.updated_at = datetime.now().isoformat()
        self._save_account_to_db(account)
        return True

    def update_config(self, platform: str, account_id: str, config: Dict[str, Any]) -> bool:
        """更新账号配置"""
        account = self.get_account(platform, account_id)
        if not account:
            return False
        account.config = {**account.config, **config}
        account.updated_at = datetime.now().isoformat()
        self._save_account_to_db(account)
        return True

    def update_status(self, platform: str, account_id: str, status: AccountStatus) -> bool:
        """更新账号状态"""
        account = self.get_account(platform, account_id)
        if not account:
            return False
        account.status = status
        account.updated_at = datetime.now().isoformat()
        self._save_account_to_db(account)
        return True

    def touch_account(self, platform: str, account_id: str):
        """记录账号最后使用时间"""
        account = self.get_account(platform, account_id)
        if account:
            account.last_used_at = datetime.now().isoformat()
            self._save_account_to_db(account)

    def get_auth_data(self, platform: str, account_id: str) -> Dict[str, Any]:
        """获取账号认证信息（解密后）"""
        account = self.get_account(platform, account_id)
        if not account:
            return {}
        return account.auth_data

    def list_platforms(self) -> List[str]:
        """列出所有已注册平台"""
        if not self._accounts and not self._db_initialized:
            self._load_from_db()
        return list(self._accounts.keys())

    def handle_oauth_callback(self, platform: str, code: str, state: Optional[str] = None) -> Optional[Dict]:
        """
        OAuth2回调处理框架

        Args:
            platform: 平台名称
            code: 授权码
            state: 状态参数

        Returns:
            OAuth结果（包含access_token等）
        """
        logger.info(f"OAuth回调: platform={platform}, state={state}")
        # 框架实现 - 各平台需要具体实现token交换
        # 返回占位结果，各网关适配器可覆盖此逻辑
        return {"platform": platform, "code": code, "status": "callback_received"}
