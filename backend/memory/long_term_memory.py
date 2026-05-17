"""
SerpentAI 记忆系统 - 长期记忆
使用Neo4j知识图谱存储重要信息，响应时间 <500ms
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import threading
import hashlib

from core.config import settings
from core.database import get_neo4j_driver, init_neo4j_constraints

logger = logging.getLogger(__name__)

class LongTermMemory:
    """
    长期记忆管理器
    使用Neo4j知识图谱存储和检索记忆
    """
    
    NODE_LABEL = "Memory"
    RELATIONSHIP_TYPE = "RELATED_TO"
    
    def __init__(self):
        """初始化长期记忆"""
        self.driver = None
        self._lock = threading.Lock()
        
        # 延迟初始化（首次使用时再连接Neo4j）
        logger.info("长期记忆初始化（延迟加载）")
    
    def _ensure_connected(self):
        """确保Neo4j连接已建立（延迟初始化）"""
        if self.driver is not None:
            return
        
        with self._lock:
            if self.driver is not None:
                return
            
            try:
                self.driver = get_neo4j_driver()
                
                if self.driver is None:
                    logger.warning("Neo4j不可用，长期记忆功能受限")
                    return
                
                # 初始化约束
                init_neo4j_constraints()
                
                logger.info("Neo4j连接已建立")
                
            except Exception as e:
                logger.error(f"Neo4j连接失败: {e}")
                raise
    
    def _is_available(self) -> bool:
        """检查Neo4j是否可用"""
        self._ensure_connected()
        return self.driver is not None

    def _generate_memory_id(self, session_id: str, content: str) -> str:
        """
        生成唯一的记忆ID
        
        Args:
            session_id: 会话ID
            content: 记忆内容
            
        Returns:
            str: 唯一ID
        """
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:16]
        return f"mem_{session_id}_{content_hash}"
    
    def add_memory(
        self,
        session_id: str,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        添加记忆到知识图谱
        
        Args:
            session_id: 会话ID
            content: 记忆内容
            memory_type: 记忆类型（fact/event/task/preference）
            importance: 重要性评分（0-1）
            metadata: 额外元数据
            
        Returns:
            Optional[str]: 记忆ID，如果失败则返回None
        """
        if not self._is_available():
            return None
        
        with self._lock:
            try:
                memory_id = self._generate_memory_id(session_id, content)
                timestamp = datetime.now().isoformat()
                
                # 使用Cypher查询创建记忆节点
                query = """
                CREATE (m:Memory {
                    id: $id,
                    session_id: $session_id,
                    content: $content,
                    memory_type: $memory_type,
                    importance: $importance,
                    timestamp: $timestamp,
                    metadata: $metadata
                })
                RETURN m
                """
                
                with self.driver.session() as session:
                    result = session.run(
                        query,
                        id=memory_id,
                        session_id=session_id,
                        content=content,
                        memory_type=memory_type,
                        importance=importance,
                        timestamp=timestamp,
                        metadata=metadata or {}
                    )
                    
                    if result.single():
                        logger.debug(f"长期记忆添加成功 | id: {memory_id}")
                        return memory_id
                    else:
                        logger.warning(f"长期记忆添加失败（无返回） | id: {memory_id}")
                        return None
                        
            except Exception as e:
                logger.error(f"添加长期记忆失败: {e}")
                return None
    
    def search_memories(
        self,
        query: str,
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索记忆（基于关键词匹配和图遍历）
        
        Args:
            query: 搜索查询
            session_id: 会话ID（可选，用于限定搜索范围）
            memory_type: 记忆类型（可选）
            limit: 返回结果数量
            
        Returns:
            List[Dict]: 记忆列表
        """
        if not self._is_available(): return []
        
        with self._lock:
            try:
                # 构建Cypher查询
                where_clauses = []
                params = {"query": query.lower(), "limit": limit}
                
                if session_id:
                    where_clauses.append("m.session_id = $session_id")
                    params["session_id"] = session_id
                
                if memory_type:
                    where_clauses.append("m.memory_type = $memory_type")
                    params["memory_type"] = memory_type
                
                # 关键词匹配（简单版本，可升级为向量检索）
                where_clauses.append("toLower(m.content) CONTAINS $query")
                
                where_str = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
                
                cypher_query = f"""
                MATCH (m:Memory)
                {where_str}
                RETURN m
                ORDER BY m.importance DESC, m.timestamp DESC
                LIMIT $limit
                """
                
                memories = []
                with self.driver.session() as session:
                    results = session.run(cypher_query, **params)
                    
                    for record in results:
                        node = record["m"]
                        memories.append({
                            "id": node["id"],
                            "content": node["content"],
                            "memory_type": node["memory_type"],
                            "importance": node["importance"],
                            "timestamp": node["timestamp"],
                            "metadata": node.get("metadata", {}),
                            "score": node["importance"]  # 使用重要性作为相关性评分
                        })
                
                logger.debug(f"长期记忆搜索完成 | query: {query[:50]}... | 结果数: {len(memories)}")
                return memories
                
            except Exception as e:
                logger.error(f"搜索长期记忆失败: {e}")
                return []
    
    def get_memories_by_session(
        self,
        session_id: str,
        memory_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取指定会话的所有记忆
        
        Args:
            session_id: 会话ID
            memory_type: 记忆类型（可选）
            limit: 返回数量限制
            
        Returns:
            List[Dict]: 记忆列表
        """
        if not self._is_available(): return []
        
        with self._lock:
            try:
                where_clauses = ["m.session_id = $session_id"]
                params = {"session_id": session_id, "limit": limit}
                
                if memory_type:
                    where_clauses.append("m.memory_type = $memory_type")
                    params["memory_type"] = memory_type
                
                where_str = "WHERE " + " AND ".join(where_clauses)
                
                cypher_query = f"""
                MATCH (m:Memory)
                {where_str}
                RETURN m
                ORDER BY m.timestamp DESC
                LIMIT $limit
                """
                
                memories = []
                with self.driver.session() as session:
                    results = session.run(cypher_query, **params)
                    
                    for record in results:
                        node = record["m"]
                        memories.append({
                            "id": node["id"],
                            "content": node["content"],
                            "memory_type": node["memory_type"],
                            "importance": node["importance"],
                            "timestamp": node["timestamp"],
                            "metadata": node.get("metadata", {})
                        })
                
                return memories
                
            except Exception as e:
                logger.error(f"获取会话长期记忆失败: {e}")
                return []
    
    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新记忆
        
        Args:
            memory_id: 记忆ID
            content: 新内容（可选）
            importance: 新重要性评分（可选）
            metadata: 新元数据（可选，合并更新）
            
        Returns:
            bool: 更新是否成功
        """
        if not self._is_available(): return []
        
        with self._lock:
            try:
                # 构建更新查询
                set_clauses = ["m.updated_at = $updated_at"]
                params = {
                    "memory_id": memory_id,
                    "updated_at": datetime.now().isoformat()
                }
                
                if content is not None:
                    set_clauses.append("m.content = $content")
                    params["content"] = content
                
                if importance is not None:
                    set_clauses.append("m.importance = $importance")
                    params["importance"] = importance
                
                if metadata is not None:
                    # 合并元数据（简化处理，直接替换）
                    set_clauses.append("m.metadata = $metadata")
                    params["metadata"] = metadata
                
                set_str = "SET " + ", ".join(set_clauses)
                
                cypher_query = f"""
                MATCH (m:Memory {{id: $memory_id}})
                {set_str}
                RETURN m
                """
                
                with self.driver.session() as session:
                    result = session.run(cypher_query, **params)
                    
                    if result.single():
                        logger.debug(f"长期记忆更新成功 | id: {memory_id}")
                        return True
                    else:
                        logger.warning(f"长期记忆更新失败（未找到） | id: {memory_id}")
                        return False
                        
            except Exception as e:
                logger.error(f"更新长期记忆失败: {e}")
                return False
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        删除记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            bool: 删除是否成功
        """
        if not self._is_available(): return []
        
        with self._lock:
            try:
                cypher_query = """
                MATCH (m:Memory {id: $memory_id})
                DETACH DELETE m
                RETURN count(m) AS deleted_count
                """
                
                with self.driver.session() as session:
                    result = session.run(cypher_query, memory_id=memory_id)
                    record = result.single()
                    
                    if record and record["deleted_count"] > 0:
                        logger.debug(f"长期记忆删除成功 | id: {memory_id}")
                        return True
                    else:
                        logger.warning(f"长期记忆删除失败（未找到） | id: {memory_id}")
                        return False
                        
            except Exception as e:
                logger.error(f"删除长期记忆失败: {e}")
                return False
    
    def clear_session(self, session_id: str) -> int:
        """
        清空指定会话的所有长期记忆
        
        Args:
            session_id: 会话ID
            
        Returns:
            int: 删除的记忆数量
        """
        if not self._is_available(): return []
        
        with self._lock:
            try:
                cypher_query = """
                MATCH (m:Memory {session_id: $session_id})
                DETACH DELETE m
                RETURN count(m) AS deleted_count
                """
                
                with self.driver.session() as session:
                    result = session.run(cypher_query, session_id=session_id)
                    record = result.single()
                    deleted_count = record["deleted_count"] if record else 0
                    
                    logger.info(f"长期记忆已清空 | session: {session_id} | 删除: {deleted_count}")
                    return deleted_count
                    
            except Exception as e:
                logger.error(f"清空会话长期记忆失败: {e}")
                return 0
    
    def clear_all(self) -> int:
        """
        清空所有长期记忆
        
        Returns:
            int: 删除的记忆总数
        """
        if not self._is_available(): return []
        
        with self._lock:
            try:
                cypher_query = """
                MATCH (m:Memory)
                DETACH DELETE m
                RETURN count(m) AS deleted_count
                """
                
                with self.driver.session() as session:
                    result = session.run(cypher_query)
                    record = result.single()
                    deleted_count = record["deleted_count"] if record else 0
                    
                    logger.info(f"所有长期记忆已清空 | 删除: {deleted_count}")
                    return deleted_count
                    
            except Exception as e:
                logger.error(f"清空所有长期记忆失败: {e}")
                return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        if not self._is_available(): return dict(type="long_term", available=False)
        
        try:
            with self.driver.session() as session:
                # 统计总记忆数
                result = session.run("MATCH (m:Memory) RETURN count(m) AS total")
                total = result.single()["total"]
                
                # 统计按类型的记忆数
                result = session.run("""
                    MATCH (m:Memory)
                    RETURN m.memory_type AS type, count(m) AS count
                """)
                type_counts = {record["type"]: record["count"] for record in result}
                
                return {
                    "type": "long_term",
                    "total_memories": total,
                    "by_type": type_counts,
                    "backend": "neo4j"
                }
                
        except Exception as e:
            logger.error(f"获取长期记忆统计失败: {e}")
            return {"type": "long_term", "error": str(e)}

# 全局长期记忆实例（单例模式）
_long_term_memory_instance: Optional[LongTermMemory] = None
_long_term_memory_lock = threading.Lock()

def get_long_term_memory() -> LongTermMemory:
    """
    获取长期记忆单例
    
    Returns:
        LongTermMemory: 长期记忆实例
    """
    global _long_term_memory_instance
    
    if _long_term_memory_instance is None:
        with _long_term_memory_lock:
            if _long_term_memory_instance is None:
                _long_term_memory_instance = LongTermMemory()
    
    return _long_term_memory_instance

def reset_long_term_memory():
    """重置长期记忆单例（用于测试）"""
    global _long_term_memory_instance
    _long_term_memory_instance = None
