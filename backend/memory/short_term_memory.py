"""
SerpentAI 记忆系统 - 短期记忆
存储最近7天对话，使用向量数据库进行语义检索，响应时间 <100ms
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import threading
import hashlib
import json

from models.base_model import Message
from core.config import settings
from core.database import get_chroma_client, init_chroma

logger = logging.getLogger(__name__)

class ShortTermMemory:
    """
    短期记忆管理器
    使用ChromaDB存储消息的向量表示，支持语义检索
    只保留最近7天的消息
    """
    
    COLLECTION_NAME = "short_term_memory"
    DAYS_TO_KEEP = 7  # 保留最近7天
    
    def __init__(self):
        """初始化短期记忆"""
        self.collection = None
        self._lock = threading.Lock()
        self._embedding_model = None
        
        # 延迟初始化（首次使用时再连接ChromaDB）
        logger.info(f"短期记忆初始化（延迟加载）| 保留天数: {self.DAYS_TO_KEEP}")
    
    def _ensure_collection(self):
        """确保ChromaDB集合存在（延迟初始化）"""
        if self.collection is not None:
            return
        
        with self._lock:
            if self.collection is not None:
                return
            
            try:
                # 初始化ChromaDB
                chroma_client = get_chroma_client()
                
                # 获取或创建集合
                try:
                    self.collection = chroma_client.get_collection(
                        name=self.COLLECTION_NAME
                    )
                    logger.info(f"已连接现有ChromaDB集合: {self.COLLECTION_NAME}")
                except:
                    self.collection = chroma_client.create_collection(
                        name=self.COLLECTION_NAME,
                        metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
                    )
                    logger.info(f"已创建ChromaDB集合: {self.COLLECTION_NAME}")
                
            except Exception as e:
                logger.error(f"ChromaDB初始化失败: {e}")
                raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        获取文本的向量表示
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 向量表示
        """
        try:
            from sentence_transformers import SentenceTransformer
            
            if self._embedding_model is None:
                # 延迟加载模型（首次使用时加载）
                self._embedding_model = SentenceTransformer(
                    'paraphrase-MiniLM-L6-v2'  # 轻量级模型，384维
                )
                logger.info("句子向量模型加载完成")
            
            # 生成向量
            embedding = self._embedding_model.encode(text)
            return embedding.tolist()
            
        except ImportError:
            logger.warning("sentence-transformers未安装，使用简单哈希向量（不精确）")
            # 降级方案：使用文本哈希生成伪向量（仅用于测试）
            return self._get_fallback_embedding(text)
    
    def _get_fallback_embedding(self, text: str) -> List[float]:
        """
        降级方案：使用文本哈希生成伪向量（仅用于测试）
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 伪向量（384维）
        """
        # 使用SHA-256哈希生成确定性伪向量
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        
        # 将哈希转换为384维向量
        vector = []
        for i in range(384):
            # 取哈希的不同部分转换为浮点数
            start_idx = (i * 2) % len(hash_hex)
            hex_part = hash_hex[start_idx:start_idx + 2]
            value = int(hex_part, 16) / 255.0  # 归一化到[0, 1]
            vector.append(value)
        
        return vector
    
    def _generate_doc_id(self, session_id: str, timestamp: str, content: str) -> str:
        """
        生成唯一的文档ID
        
        Args:
            session_id: 会话ID
            timestamp: 时间戳
            content: 消息内容（用于去重）
            
        Returns:
            str: 唯一ID
        """
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
        return f"{session_id}_{timestamp}_{content_hash}"
    
    def add_message(self, session_id: str, message: Message) -> None:
        """
        添加消息到短期记忆
        
        Args:
            session_id: 会话ID
            message: 消息对象
        """
        self._ensure_collection()
        
        with self._lock:
            try:
                # 生成ID和向量
                timestamp = datetime.now().isoformat()
                doc_id = self._generate_doc_id(session_id, timestamp, message.content)
                embedding = self._get_embedding(message.content)
                
                # 准备元数据
                metadata = {
                    "session_id": session_id,
                    "role": message.role,
                    "content": message.content[:500],  # 只存前500字符（ChromaDB限制）
                    "timestamp": timestamp,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                }
                
                if message.name:
                    metadata["name"] = message.name
                
                # 添加到ChromaDB
                self.collection.add(
                    embeddings=[embedding],
                    documents=[message.content],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
                
                logger.debug(f"短期记忆添加消息 | session: {session_id} | role: {message.role}")
                
                # 清理过期消息（异步，不阻塞主流程）
                self._cleanup_old_messages()
                
            except Exception as e:
                logger.error(f"添加消息到短期记忆失败: {e}")
                raise
    
    def _cleanup_old_messages(self) -> None:
        """
        清理超过7天的消息（异步执行）
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=self.DAYS_TO_KEEP)).strftime("%Y-%m-%d")
            
            # 查询需要删除的消息
            results = self.collection.get(
                where={"date": {"$lt": cutoff_date}}
            )
            
            if results and results['ids']:
                # 删除过期消息
                self.collection.delete(ids=results['ids'])
                logger.info(f"清理过期短期记忆 | 删除数量: {len(results['ids'])}")
                
        except Exception as e:
            logger.error(f"清理过期消息失败: {e}")
    
    def search_messages(
        self, 
        query: str, 
        session_id: Optional[str] = None,
        limit: int = 5,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        搜索相似消息（语义检索）
        
        Args:
            query: 搜索查询
            session_id: 会话ID（可选，用于限定搜索范围）
            limit: 返回结果数量
            min_similarity: 最小相似度阈值
            
        Returns:
            List[Dict]: 相似消息列表
        """
        self._ensure_collection()
        
        with self._lock:
            try:
                # 生成查询向量
                query_embedding = self._get_embedding(query)
                
                # 构建查询条件
                where_clause = {}
                if session_id:
                    where_clause["session_id"] = session_id
                
                # 执行向量检索
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    where=where_clause if where_clause else None
                )
                
                # 解析结果
                messages = []
                if results and results['ids']:
                    for i, doc_id in enumerate(results['ids'][0]):
                        metadata = results['metadatas'][0][i]
                        distance = results['distances'][0][i]
                        
                        # 转换距离为相似度（ChromaDB使用余弦距离）
                        similarity = 1 - distance
                        
                        if similarity >= min_similarity:
                            messages.append({
                                "id": doc_id,
                                "content": metadata.get("content", ""),
                                "role": metadata.get("role"),
                                "timestamp": metadata.get("timestamp"),
                                "similarity": similarity,
                            })
                
                logger.debug(f"语义检索完成 | query: {query[:50]}... | 结果数: {len(messages)}")
                return messages
                
            except Exception as e:
                logger.error(f"语义检索失败: {e}")
                return []
    
    def get_messages_by_session(
        self, 
        session_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取指定会话的消息（按时间排序）
        
        Args:
            session_id: 会话ID
            limit: 返回消息数量
            
        Returns:
            List[Dict]: 消息列表
        """
        self._ensure_collection()
        
        with self._lock:
            try:
                # 查询指定会话的所有消息
                results = self.collection.get(
                    where={"session_id": session_id},
                    limit=limit
                )
                
                # 解析结果并排序
                messages = []
                if results and results['ids']:
                    for i, doc_id in enumerate(results['ids']):
                        metadata = results['metadatas'][i]
                        messages.append({
                            "id": doc_id,
                            "content": metadata.get("content", ""),
                            "role": metadata.get("role"),
                            "timestamp": metadata.get("timestamp"),
                        })
                
                # 按时间戳排序
                messages.sort(key=lambda x: x['timestamp'])
                
                return messages[-limit:]  # 返回最近的N条
                
            except Exception as e:
                logger.error(f"获取会话消息失败: {e}")
                return []
    
    def clear_session(self, session_id: str) -> None:
        """
        清空指定会话的短期记忆
        
        Args:
            session_id: 会话ID
        """
        self._ensure_collection()
        
        with self._lock:
            try:
                results = self.collection.get(
                    where={"session_id": session_id}
                )
                
                if results and results['ids']:
                    self.collection.delete(ids=results['ids'])
                    logger.info(f"短期记忆已清空 | session: {session_id}")
                    
            except Exception as e:
                logger.error(f"清空会话短期记忆失败: {e}")
    
    def clear_all(self) -> None:
        """清空所有短期记忆"""
        self._ensure_collection()
        
        with self._lock:
            try:
                # 删除整个集合
                chroma_client = get_chroma_client()
                chroma_client.delete_collection(self.COLLECTION_NAME)
                
                # 重新创建空集合
                self.collection = chroma_client.create_collection(
                    name=self.COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"}
                )
                
                logger.info("短期记忆已全部清空并重新初始化")
                
            except Exception as e:
                logger.error(f"清空短期记忆失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        self._ensure_collection()
        
        try:
            count = self.collection.count()
            
            return {
                "type": "short_term",
                "total_messages": count,
                "days_to_keep": self.DAYS_TO_KEEP,
                "embedding_model": "paraphrase-MiniLM-L6-v2" if self._embedding_model else "not_loaded",
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"type": "short_term", "error": str(e)}

# 全局短期记忆实例（单例模式）
_short_term_memory_instance: Optional[ShortTermMemory] = None
_short_term_memory_lock = threading.Lock()

def get_short_term_memory() -> ShortTermMemory:
    """
    获取短期记忆单例
    
    Returns:
        ShortTermMemory: 短期记忆实例
    """
    global _short_term_memory_instance
    
    if _short_term_memory_instance is None:
        with _short_term_memory_lock:
            if _short_term_memory_instance is None:
                _short_term_memory_instance = ShortTermMemory()
    
    return _short_term_memory_instance

def reset_short_term_memory():
    """重置短期记忆单例（用于测试）"""
    global _short_term_memory_instance
    _short_term_memory_instance = None
