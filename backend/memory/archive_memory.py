"""
SerpentAI 记忆系统 - 归档记忆
存储压缩的对话摘要，响应时间 <5秒
使用SQLite存储，轻量且快速
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import threading
import sqlite3
import json
import hashlib

from core.config import settings
from core.database import get_db

logger = logging.getLogger(__name__)

class ArchiveMemory:
    """
    归档记忆管理器
    存储压缩的对话摘要，使用SQLite存储
    """
    
    TABLE_NAME = "archive_memories"
    DAYS_TO_KEEP = 365  # 保留1年
    
    def __init__(self):
        """初始化归档记忆"""
        self._lock = threading.Lock()
        self._init_table()
        
        logger.info(f"归档记忆初始化完成 | 保留天数: {self.DAYS_TO_KEEP}")
    
    def _init_table(self):
        """初始化数据库表"""
        try:
            from core.database import engine, Base
            Base.metadata.create_all(bind=engine)
            logger.info("归档记忆表初始化完成")
        except Exception as e:
            logger.error(f"归档记忆表初始化失败: {e}")
    
    def _get_connection(self):
        """获取SQLite连接（直接使用SQLite以实现归档记忆）"""
        db_path = settings.SQLITE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_table(self, conn):
        """确保归档表存在（直接使用SQL）"""
        conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            summary TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            message_count INTEGER DEFAULT 0,
            metadata TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        
        # 创建索引
        conn.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_session_id 
        ON {self.TABLE_NAME}(session_id)
        """)
        
        conn.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_created_at 
        ON {self.TABLE_NAME}(created_at)
        """)
        
        conn.commit()
    
    def _generate_archive_id(self, session_id: str, start_date: str, end_date: str) -> str:
        """
        生成唯一的归档ID
        
        Args:
            session_id: 会话ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            str: 唯一ID
        """
        content = f"{session_id}_{start_date}_{end_date}"
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:16]
        return f"arc_{content_hash}"
    
    def add_summary(
        self,
        session_id: str,
        summary: str,
        start_date: str,
        end_date: str,
        message_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        添加归档摘要
        
        Args:
            session_id: 会话ID
            summary: 压缩摘要
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            message_count: 消息数量
            metadata: 额外元数据
            
        Returns:
            Optional[str]: 归档ID，如果失败则返回None
        """
        with self._lock:
            try:
                conn = self._get_connection()
                self._ensure_table(conn)
                
                archive_id = self._generate_archive_id(session_id, start_date, end_date)
                timestamp = datetime.now().isoformat()
                
                conn.execute(f"""
                INSERT OR REPLACE INTO {self.TABLE_NAME}
                (id, session_id, summary, start_date, end_date, message_count, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    archive_id,
                    session_id,
                    summary,
                    start_date,
                    end_date,
                    message_count,
                    json.dumps(metadata or {}),
                    timestamp,
                    timestamp
                ))
                
                conn.commit()
                conn.close()
                
                logger.debug(f"归档记忆添加成功 | id: {archive_id}")
                return archive_id
                
            except Exception as e:
                logger.error(f"添加归档记忆失败: {e}")
                return None
    
    def search_summaries(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索归档摘要（关键词匹配）
        
        Args:
            query: 搜索查询
            session_id: 会话ID（可选）
            limit: 返回结果数量
            
        Returns:
            List[Dict]: 归档摘要列表
        """
        with self._lock:
            try:
                conn = self._get_connection()
                self._ensure_table(conn)
                
                # 构建查询
                where_clauses = ["summary LIKE ?"]
                params = [f"%{query}%"]
                
                if session_id:
                    where_clauses.append("session_id = ?")
                    params.append(session_id)
                
                where_str = "WHERE " + " AND ".join(where_clauses)
                
                sql = f"""
                SELECT * FROM {self.TABLE_NAME}
                {where_str}
                ORDER BY created_at DESC
                LIMIT ?
                """
                params.append(limit)
                
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                
                summaries = []
                for row in rows:
                    summaries.append({
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "summary": row["summary"],
                        "start_date": row["start_date"],
                        "end_date": row["end_date"],
                        "message_count": row["message_count"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "created_at": row["created_at"],
                        "score": 0.2  # 归档记忆的相似度较低
                    })
                
                conn.close()
                
                logger.debug(f"归档记忆搜索完成 | query: {query[:50]}... | 结果数: {len(summaries)}")
                return summaries
                
            except Exception as e:
                logger.error(f"搜索归档记忆失败: {e}")
                return []
    
    def get_summaries_by_session(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取指定会话的所有归档摘要
        
        Args:
            session_id: 会话ID
            limit: 返回数量限制
            
        Returns:
            List[Dict]: 归档摘要列表
        """
        with self._lock:
            try:
                conn = self._get_connection()
                self._ensure_table(conn)
                
                cursor = conn.execute(f"""
                SELECT * FROM {self.TABLE_NAME}
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """, (session_id, limit))
                
                rows = cursor.fetchall()
                
                summaries = []
                for row in rows:
                    summaries.append({
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "summary": row["summary"],
                        "start_date": row["start_date"],
                        "end_date": row["end_date"],
                        "message_count": row["message_count"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "created_at": row["created_at"],
                    })
                
                conn.close()
                
                return summaries
                
            except Exception as e:
                logger.error(f"获取会话归档记忆失败: {e}")
                return []
    
    def distill_from_short_term(self, session_id: str, days: int = 7) -> Optional[str]:
        """
        从短期记忆蒸馏归档摘要
        
        Args:
            session_id: 会话ID
            days: 蒸馏多少天的数据
            
        Returns:
            Optional[str]: 归档ID，如果失败则返回None
        """
        try:
            from .short_term_memory import get_short_term_memory
            
            short_term = get_short_term_memory()
            messages = short_term.get_messages_by_session(session_id, limit=1000)
            
            if not messages or len(messages) < 10:
                logger.info(f"消息数量不足，跳过蒸馏 | session: {session_id}")
                return None
            
            # 生成时间范围
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # 生成摘要（简单拼接，可升级为LLM生成）
            summary_parts = []
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:100]  # 只取前100字符
                summary_parts.append(f"{role}: {content}")
            
            summary = "\n".join(summary_parts)
            
            # 添加到归档
            archive_id = self.add_summary(
                session_id=session_id,
                summary=summary,
                start_date=start_date,
                end_date=end_date,
                message_count=len(messages),
                metadata={"source": "short_term_distillation"}
            )
            
            if archive_id:
                logger.info(f"蒸馏完成 | session: {session_id} | 消息数: {len(messages)}")
            
            return archive_id
            
        except Exception as e:
            logger.error(f"从短期记忆蒸馏失败: {e}")
            return None
    
    def clear_session(self, session_id: str) -> int:
        """
        清空指定会话的归档记忆
        
        Args:
            session_id: 会话ID
            
        Returns:
            int: 删除的归档数量
        """
        with self._lock:
            try:
                conn = self._get_connection()
                self._ensure_table(conn)
                
                cursor = conn.execute(f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE session_id = ?
                """, (session_id,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()
                
                logger.info(f"归档记忆已清空 | session: {session_id} | 删除: {deleted_count}")
                return deleted_count
                
            except Exception as e:
                logger.error(f"清空会话归档记忆失败: {e}")
                return 0
    
    def clear_old_archives(self) -> int:
        """
        清理超过保留期限的归档
        
        Returns:
            int: 删除的归档数量
        """
        with self._lock:
            try:
                cutoff_date = (datetime.now() - timedelta(days=self.DAYS_TO_KEEP)).strftime("%Y-%m-%d")
                
                conn = self._get_connection()
                self._ensure_table(conn)
                
                cursor = conn.execute(f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE end_date < ?
                """, (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()
                
                if deleted_count > 0:
                    logger.info(f"清理过期归档记忆 | 删除: {deleted_count}")
                
                return deleted_count
                
            except Exception as e:
                logger.error(f"清理过期归档记忆失败: {e}")
                return 0
    
    def clear_all(self) -> int:
        """
        清空所有归档记忆
        
        Returns:
            int: 删除的归档数量
        """
        with self._lock:
            try:
                conn = self._get_connection()
                self._ensure_table(conn)
                
                cursor = conn.execute(f"DELETE FROM {self.TABLE_NAME}")
                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()
                
                logger.info(f"所有归档记忆已清空 | 删除: {deleted_count}")
                return deleted_count
                
            except Exception as e:
                logger.error(f"清空所有归档记忆失败: {e}")
                return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            conn = self._get_connection()
            self._ensure_table(conn)
            
            # 统计总数
            cursor = conn.execute(f"SELECT COUNT(*) as total FROM {self.TABLE_NAME}")
            total = cursor.fetchone()["total"]
            
            # 统计按会话
            cursor = conn.execute(f"""
            SELECT session_id, COUNT(*) as count 
            FROM {self.TABLE_NAME}
            GROUP BY session_id
            """)
            by_session = {row["session_id"]: row["count"] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                "type": "archive",
                "total_archives": total,
                "by_session": by_session,
                "days_to_keep": self.DAYS_TO_KEEP,
                "backend": "sqlite"
            }
            
        except Exception as e:
            logger.error(f"获取归档记忆统计失败: {e}")
            return {"type": "archive", "error": str(e)}

# 全局归档记忆实例（单例模式）
_archive_memory_instance: Optional[ArchiveMemory] = None
_archive_memory_lock = threading.Lock()

def get_archive_memory() -> ArchiveMemory:
    """
    获取归档记忆单例
    
    Returns:
        ArchiveMemory: 归档记忆实例
    """
    global _archive_memory_instance
    
    if _archive_memory_instance is None:
        with _archive_memory_lock:
            if _archive_memory_instance is None:
                _archive_memory_instance = ArchiveMemory()
    
    return _archive_memory_instance

def reset_archive_memory():
    """重置归档记忆单例（用于测试）"""
    global _archive_memory_instance
    _archive_memory_instance = None
