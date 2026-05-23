# -*- coding: utf-8 -*-
"""
会话存储模块 - 基于SQLite的会话和消息持久化
"""

import time
import uuid
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """会话数据类"""
    id: str = ""
    title: str = "新对话"
    created_at: float = 0.0
    updated_at: float = 0.0
    message_count: int = 0
    model: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = f"session_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": int(self.created_at),
            "updated_at": int(self.updated_at),
            "message_count": self.message_count,
            "model": self.model,
            "metadata": self.metadata,
        }


@dataclass
class ChatMessage:
    """聊天消息数据类"""
    id: str = ""
    session_id: str = ""
    role: str = "user"
    content: str = ""
    model: str = ""
    tokens: int = 0
    latency_ms: int = 0
    created_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = f"msg_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "model": self.model,
            "tokens": self.tokens,
            "latency_ms": self.latency_ms,
            "created_at": int(self.created_at),
            "metadata": self.metadata,
        }


class SessionStore:
    """
    会话存储 - 使用SQLite进行持久化
    
    提供会话和消息的CRUD操作，支持按时间/ID查询
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._messages: Dict[str, List[ChatMessage]] = {}
        self._db_available = False
        self._init_sqlite_tables()

    def _init_sqlite_tables(self):
        """初始化SQLite表（如果数据库可用）"""
        try:
            from core.database import engine
            with engine.connect() as conn:
                from sqlalchemy import text as sa_text
                conn.execute(sa_text("""
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL DEFAULT '新对话',
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        message_count INTEGER NOT NULL DEFAULT 0,
                        model TEXT NOT NULL DEFAULT '',
                        metadata TEXT DEFAULT '{}'
                    )
                """))
                conn.execute(sa_text("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        model TEXT NOT NULL DEFAULT '',
                        tokens INTEGER NOT NULL DEFAULT 0,
                        latency_ms INTEGER NOT NULL DEFAULT 0,
                        created_at REAL NOT NULL,
                        metadata TEXT DEFAULT '{}',
                        FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                    )
                """))
                conn.execute(sa_text("""
                    CREATE INDEX IF NOT EXISTS idx_messages_session 
                    ON chat_messages(session_id, created_at)
                """))
                conn.commit()
            self._db_available = True
            self._load_from_db()
            logger.info("会话存储: SQLite持久化已启用")
        except Exception as e:
            logger.warning(f"会话存储: SQLite不可用，使用内存存储: {e}")
            self._db_available = False

    def _load_from_db(self):
        """从数据库加载已有会话"""
        try:
            from core.database import engine
            from sqlalchemy import text as sa_text
            import json
            with engine.connect() as conn:
                rows = conn.execute(sa_text(
                    "SELECT id, title, created_at, updated_at, message_count, model, metadata FROM chat_sessions ORDER BY updated_at DESC"
                )).fetchall()
                for row in rows:
                    session = Session(
                        id=row[0], title=row[1], created_at=row[2],
                        updated_at=row[3], message_count=row[4],
                        model=row[5], metadata=json.loads(row[6] or '{}')
                    )
                    self._sessions[session.id] = session

                msg_rows = conn.execute(sa_text(
                    "SELECT id, session_id, role, content, model, tokens, latency_ms, created_at, metadata FROM chat_messages ORDER BY created_at ASC"
                )).fetchall()
                for row in msg_rows:
                    msg = ChatMessage(
                        id=row[0], session_id=row[1], role=row[2],
                        content=row[3], model=row[4], tokens=row[5],
                        latency_ms=row[6], created_at=row[7],
                        metadata=json.loads(row[8] or '{}')
                    )
                    self._messages.setdefault(msg.session_id, []).append(msg)
            logger.info(f"会话存储: 从数据库加载 {len(self._sessions)} 个会话")
        except Exception as e:
            logger.warning(f"会话存储: 加载数据库数据失败: {e}")

    def _save_session_to_db(self, session: Session):
        """保存会话到数据库"""
        if not self._db_available:
            return
        try:
            import json
            from core.database import engine
            from sqlalchemy import text as sa_text
            with engine.connect() as conn:
                conn.execute(sa_text("""
                    INSERT OR REPLACE INTO chat_sessions 
                    (id, title, created_at, updated_at, message_count, model, metadata)
                    VALUES (:id, :title, :created_at, :updated_at, :message_count, :model, :metadata)
                """), {
                    "id": session.id, "title": session.title,
                    "created_at": session.created_at, "updated_at": session.updated_at,
                    "message_count": session.message_count, "model": session.model,
                    "metadata": json.dumps(session.metadata, ensure_ascii=False)
                })
                conn.commit()
        except Exception as e:
            logger.error(f"保存会话到数据库失败: {e}")

    def _save_message_to_db(self, msg: ChatMessage):
        """保存消息到数据库"""
        if not self._db_available:
            return
        try:
            import json
            from core.database import engine
            from sqlalchemy import text as sa_text
            with engine.connect() as conn:
                conn.execute(sa_text("""
                    INSERT OR REPLACE INTO chat_messages 
                    (id, session_id, role, content, model, tokens, latency_ms, created_at, metadata)
                    VALUES (:id, :session_id, :role, :content, :model, :tokens, :latency_ms, :created_at, :metadata)
                """), {
                    "id": msg.id, "session_id": msg.session_id,
                    "role": msg.role, "content": msg.content,
                    "model": msg.model, "tokens": msg.tokens,
                    "latency_ms": msg.latency_ms, "created_at": msg.created_at,
                    "metadata": json.dumps(msg.metadata, ensure_ascii=False)
                })
                conn.commit()
        except Exception as e:
            logger.error(f"保存消息到数据库失败: {e}")

    def _delete_session_from_db(self, session_id: str):
        """从数据库删除会话及其消息"""
        if not self._db_available:
            return
        try:
            from core.database import engine
            from sqlalchemy import text as sa_text
            with engine.connect() as conn:
                conn.execute(sa_text("DELETE FROM chat_messages WHERE session_id = :sid"), {"sid": session_id})
                conn.execute(sa_text("DELETE FROM chat_sessions WHERE id = :sid"), {"sid": session_id})
                conn.commit()
        except Exception as e:
            logger.error(f"从数据库删除会话失败: {e}")

    # ==================== 公开API ====================

    def create_session(self, title: Optional[str] = None) -> Session:
        """创建新会话"""
        session = Session(title=title or "新对话")
        self._sessions[session.id] = session
        self._messages[session.id] = []
        self._save_session_to_db(session)
        logger.info(f"创建会话: {session.id}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self._sessions.get(session_id)

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Session]:
        """列出会话（按更新时间倒序）"""
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True
        )
        return sessions[offset:offset + limit]

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._messages.pop(session_id, None)
            self._delete_session_from_db(session_id)
            logger.info(f"删除会话: {session_id}")
            return True
        return False

    def add_message(self, session_id: str, role: str, content: str,
                    model: str = "", tokens: int = 0, latency_ms: int = 0,
                    metadata: Optional[Dict] = None) -> Optional[ChatMessage]:
        """向会话添加消息"""
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"会话不存在: {session_id}")
            return None

        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            model=model,
            tokens=tokens,
            latency_ms=latency_ms,
            metadata=metadata or {}
        )
        self._messages.setdefault(session_id, []).append(msg)
        
        # 更新会话元数据
        session.message_count = len(self._messages[session_id])
        session.updated_at = time.time()
        if model:
            session.model = model
        
        self._save_message_to_db(msg)
        self._save_session_to_db(session)
        return msg

    def get_messages(self, session_id: str, limit: int = 100,
                     offset: int = 0) -> List[ChatMessage]:
        """获取会话消息"""
        msgs = self._messages.get(session_id, [])
        return msgs[offset:offset + limit]

    def get_message_history(self, session_id: str,
                            max_messages: int = 50) -> List[Dict[str, str]]:
        """获取消息历史（简化格式，用于模型调用）"""
        msgs = self._messages.get(session_id, [])
        recent = msgs[-max_messages:] if len(msgs) > max_messages else msgs
        return [{"role": m.role, "content": m.content} for m in recent]

    def update_session_title(self, session_id: str, title: str) -> bool:
        """更新会话标题"""
        session = self._sessions.get(session_id)
        if session:
            session.title = title
            session.updated_at = time.time()
            self._save_session_to_db(session)
            return True
        return False


# ==================== 全局单例 ====================
_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """获取全局会话存储实例"""
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
