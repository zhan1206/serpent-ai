"""
SerpentAI 统一收件箱
跨通道统一消息聚合和管理
"""

import asyncio
import json
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """消息优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageStatus(Enum):
    """消息状态"""
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class Message:
    """统一消息格式"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    
    # 内容
    title: str = ""
    content: str = ""
    content_type: str = "text"  # text, html, markdown
    
    # 来源
    source_channel: str = ""  # discord, telegram, email, webhook, etc.
    source_id: str = ""  # 原始消息ID
    author_id: str = ""
    author_name: str = ""
    
    # 元数据
    priority: str = "normal"
    status: str = "unread"
    is_starred: bool = False
    is_archived: bool = False
    
    # 时间
    received_at: datetime = field(default_factory=datetime.now)
    read_at: Optional[datetime] = None
    
    # 附加数据
    metadata: Dict = field(default_factory=dict)
    attachments: List[Dict] = field(default_factory=list)
    
    # 会话
    thread_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "content_type": self.content_type,
            "source_channel": self.source_channel,
            "source_id": self.source_id,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "priority": self.priority,
            "status": self.status,
            "is_starred": self.is_starred,
            "is_archived": self.is_archived,
            "received_at": self.received_at.isoformat(),
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "metadata": self.metadata,
            "attachments": self.attachments,
            "thread_id": self.thread_id,
            "parent_message_id": self.parent_message_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        return cls(
            id=data.get("id", uuid.uuid4().hex[:12]),
            title=data.get("title", ""),
            content=data.get("content", ""),
            content_type=data.get("content_type", "text"),
            source_channel=data.get("source_channel", ""),
            source_id=data.get("source_id", ""),
            author_id=data.get("author_id", ""),
            author_name=data.get("author_name", ""),
            priority=data.get("priority", "normal"),
            status=data.get("status", "unread"),
            is_starred=data.get("is_starred", False),
            is_archived=data.get("is_archived", False),
            received_at=datetime.fromisoformat(data["received_at"]) if data.get("received_at") else datetime.now(),
            read_at=datetime.fromisoformat(data["read_at"]) if data.get("read_at") else None,
            metadata=data.get("metadata", {}),
            attachments=data.get("attachments", []),
            thread_id=data.get("thread_id"),
            parent_message_id=data.get("parent_message_id"),
        )


class UnifiedInbox:
    """
    统一收件箱
    功能：
    1. 消息聚合：从所有已注册网关收集消息
    2. 消息去重
    3. 消息排序（按时间/priority）
    4. 消息搜索/过滤（按来源/时间/关键词）
    5. 消息标记（已读/星标/归档）
    6. SQLite持久化
    """
    
    def __init__(self, db_path: str = None):
        """
        初始化统一收件箱
        
        Args:
            db_path: 数据库文件路径（可选，默认 ~/serpentai/data/inbox.db）
        """
        if db_path is None:
            # 默认路径
            base_dir = Path.home() / ".qclaw" / "workspace" / "serpent-ai" / "data"
            base_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(base_dir / "inbox.db")
        
        self.db_path = db_path
        self._lock = threading.Lock()
        
        # 初始化数据库
        self._init_database()
        
        # 注册的消息源
        self._handlers: Dict[str, callable] = {}
        
        logger.info(f"统一收件箱初始化完成: {db_path}")
    
    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                content_type TEXT DEFAULT 'text',
                source_channel TEXT,
                source_id TEXT,
                author_id TEXT,
                author_name TEXT,
                priority TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'unread',
                is_starred INTEGER DEFAULT 0,
                is_archived INTEGER DEFAULT 0,
                received_at TEXT,
                read_at TEXT,
                thread_id TEXT,
                parent_message_id TEXT,
                UNIQUE(source_channel, source_id)
            )
        """)
        
        # 创建消息元数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT,
                key TEXT,
                value TEXT,
                FOREIGN KEY (message_id) REFERENCES messages(id)
            )
        """)
        
        # 创建附件表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT,
                file_name TEXT,
                file_type TEXT,
                file_url TEXT,
                file_size INTEGER,
                FOREIGN KEY (message_id) REFERENCES messages(id)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_received 
            ON messages(received_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_source 
            ON messages(source_channel, source_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_status 
            ON messages(status)
        """)
        
        conn.commit()
        conn.close()
    
    # ==================== 消息接收 ====================
    
    def register_source(self, channel: str, handler: callable):
        """
        注册消息源处理器
        
        Args:
            channel: 渠道名称
            handler: 回调函数，接收原始消息，返回统一Message格式
        """
        self._handlers[channel] = handler
        logger.info(f"已注册消息源: {channel}")
    
    def receive_message(
        self,
        channel: str,
        source_id: str,
        title: str = "",
        content: str = "",
        content_type: str = "text",
        author_id: str = "",
        author_name: str = "",
        priority: str = "normal",
        metadata: Dict = None,
        attachments: List[Dict] = None,
        thread_id: str = None,
        parent_message_id: str = None
    ) -> Message:
        """
        接收消息
        
        Args:
            channel: 消息来源渠道
            source_id: 原始消息ID
            其他参数见 Message 定义
        
        Returns:
            创建的 Message 对象
        """
        # 检查是否重复
        if self._is_duplicate(channel, source_id):
            logger.debug(f"消息已存在，跳过: {channel}/{source_id}")
            return None
        
        # 创建消息对象
        message = Message(
            title=title,
            content=content,
            content_type=content_type,
            source_channel=channel,
            source_id=source_id,
            author_id=author_id,
            author_name=author_name,
            priority=priority,
            metadata=metadata or {},
            attachments=attachments or [],
            thread_id=thread_id,
            parent_message_id=parent_message_id
        )
        
        # 保存到数据库
        self._save_message(message)
        
        logger.info(f"收到消息: {message.id} from {channel}")
        return message
    
    def _is_duplicate(self, channel: str, source_id: str) -> bool:
        """检查是否重复消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT 1 FROM messages WHERE source_channel = ? AND source_id = ?",
            (channel, source_id)
        )
        
        result = cursor.fetchone() is not None
        conn.close()
        
        return result
    
    def _save_message(self, message: Message):
        """保存消息到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO messages (
                id, title, content, content_type, source_channel, source_id,
                author_id, author_name, priority, status, is_starred, is_archived,
                received_at, read_at, thread_id, parent_message_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.id,
                message.title,
                message.content,
                message.content_type,
                message.source_channel,
                message.source_id,
                message.author_id,
                message.author_name,
                message.priority,
                message.status,
                1 if message.is_starred else 0,
                1 if message.is_archived else 0,
                message.received_at.isoformat(),
                message.read_at.isoformat() if message.read_at else None,
                message.thread_id,
                message.parent_message_id,
            )
        )
        
        # 保存元数据
        for key, value in message.metadata.items():
            if isinstance(value, str):
                cursor.execute(
                    "INSERT INTO message_metadata (message_id, key, value) VALUES (?, ?, ?)",
                    (message.id, key, value)
                )
        
        # 保存附件
        for att in message.attachments:
            cursor.execute(
                """
                INSERT INTO attachments 
                (message_id, file_name, file_type, file_url, file_size) 
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    att.get("file_name"),
                    att.get("file_type"),
                    att.get("file_url"),
                    att.get("file_size", 0),
                )
            )
        
        conn.commit()
        conn.close()
    
    # ==================== 消息查询 ====================
    
    def get_message(self, message_id: str) -> Optional[Message]:
        """获取单个消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM messages WHERE id = ?",
            (message_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_message(row)
        return None
    
    def list_messages(
        self,
        channels: List[str] = None,
        status: str = None,
        is_starred: bool = None,
        is_archived: bool = None,
        priority: str = None,
        keyword: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "received_at",
        order_desc: bool = True
    ) -> List[Message]:
        """
        列出消息
        
        Args:
            channels: 渠道过滤
            status: 状态过滤
            is_starred: 星标过滤
            is_archived: 归档过滤
            priority: 优先级过滤
            keyword: 关键词搜索（搜索标题和内容）
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            offset: 偏移量
            order_by: 排序字段
            order_desc: 是否倒序
        
        Returns:
            Message 列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建查询
        conditions = []
        params = []
        
        if channels:
            placeholders = ",".join(["?"] * len(channels))
            conditions.append(f"source_channel IN ({placeholders})")
            params.extend(channels)
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        if is_starred is not None:
            conditions.append(f"is_starred = {1 if is_starred else 0}")
        
        if is_archived is not None:
            conditions.append(f"is_archived = {1 if is_archived else 0}")
        
        if priority:
            conditions.append("priority = ?")
            params.append(priority)
        
        if keyword:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        if start_time:
            conditions.append("received_at >= ?")
            params.append(start_time.isoformat())
        
        if end_time:
            conditions.append("received_at <= ?")
            params.append(end_time.isoformat())
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # 排序
        order = "DESC" if order_desc else "ASC"
        if order_by not in ["received_at", "priority", "status"]:
            order_by = "received_at"
        
        query = f"""
            SELECT * FROM messages 
            {where_clause}
            ORDER BY {order_by} {order}
            LIMIT ? OFFSET ?
        """
        
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_message(row) for row in rows]
    
    def _row_to_message(self, row: tuple) -> Message:
        """将数据库行转换为 Message 对象"""
        return Message(
            id=row[0],
            title=row[1],
            content=row[2],
            content_type=row[3],
            source_channel=row[4],
            source_id=row[5],
            author_id=row[6],
            author_name=row[7],
            priority=row[8],
            status=row[9],
            is_starred=bool(row[10]),
            is_archived=bool(row[11]),
            received_at=datetime.fromisoformat(row[12]) if row[12] else datetime.now(),
            read_at=datetime.fromisoformat(row[13]) if row[13] else None,
            thread_id=row[14],
            parent_message_id=row[15],
        )
    
    # ==================== 消息操作 ====================
    
    def mark_as_read(self, message_id: str) -> bool:
        """标记为已读"""
        return self._update_message(
            message_id,
            status="read",
            read_at=datetime.now().isoformat()
        )
    
    def mark_as_unread(self, message_id: str) -> bool:
        """标记为未读"""
        return self._update_message(
            message_id,
            status="unread",
            read_at=None
        )
    
    def toggle_star(self, message_id: str) -> bool:
        """切换星标状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT is_starred FROM messages WHERE id = ?",
            (message_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        
        new_star = 0 if row[0] else 1
        
        cursor.execute(
            "UPDATE messages SET is_starred = ? WHERE id = ?",
            (new_star, message_id)
        )
        
        conn.commit()
        conn.close()
        
        return True
    
    def archive_message(self, message_id: str) -> bool:
        """归档消息"""
        return self._update_message(
            message_id,
            is_archived=1,
            status="archived"
        )
    
    def unarchive_message(self, message_id: str) -> bool:
        """取消归档"""
        return self._update_message(
            message_id,
            is_archived=0,
            status="unread"
        )
    
    def delete_message(self, message_id: str) -> bool:
        """删除消息"""
        return self._update_message(
            message_id,
            status="deleted"
        )
    
    def _update_message(
        self,
        message_id: str,
        **kwargs
    ) -> bool:
        """更新消息字段"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建更新语句
        sets = []
        params = []
        
        for key, value in kwargs.items():
            if key == "status":
                sets.append("status = ?")
                params.append(value)
            elif key == "read_at":
                sets.append("read_at = ?")
                params.append(value)
            elif key == "is_archived":
                sets.append("is_archived = ?")
                params.append(value)
            elif key == "is_starred":
                sets.append("is_starred = ?")
                params.append(int(value) if isinstance(value, int) else (1 if value else 0))
        
        if not sets:
            conn.close()
            return False
        
        query = f"UPDATE messages SET {', '.join(sets)} WHERE id = ?"
        params.append(message_id)
        
        cursor.execute(query, params)
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0
    
    # ==================== 统计和聚合 ====================
    
    def get_unread_count(self, channels: List[str] = None) -> int:
        """获取未读消息数量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if channels:
            placeholders = ",".join(["?"] * len(channels))
            cursor.execute(
                f"SELECT COUNT(*) FROM messages WHERE status = 'unread' AND source_channel IN ({placeholders})",
                channels
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM messages WHERE status = 'unread'"
            )
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总数
        cursor.execute("SELECT COUNT(*) FROM messages")
        total = cursor.fetchone()[0]
        
        # 未读
        cursor.execute("SELECT COUNT(*) FROM messages WHERE status = 'unread'")
        unread = cursor.fetchone()[0]
        
        # 星标
        cursor.execute("SELECT COUNT(*) FROM messages WHERE is_starred = 1")
        starred = cursor.fetchone()[0]
        
        # 按渠道统计
        cursor.execute("""
            SELECT source_channel, COUNT(*) 
            FROM messages 
            GROUP BY source_channel
        """)
        by_channel = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 按优先级统计
        cursor.execute("""
            SELECT priority, COUNT(*) 
            FROM messages 
            GROUP BY priority
        """)
        by_priority = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "total": total,
            "unread": unread,
            "starred": starred,
            "by_channel": by_channel,
            "by_priority": by_priority
        }
    
    # ==================== 清理 ====================
    
    def purge_old_messages(self, days: int = 30) -> int:
        """清理旧消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute(
            "DELETE FROM messages WHERE received_at < ? AND is_starred = 0 AND status = 'archived'",
            (cutoff,)
        )
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"已清理 {affected} 条旧消息")
        return affected
    
    def close(self):
        """关闭数据库连接"""
        logger.info("统一收件箱已关闭")