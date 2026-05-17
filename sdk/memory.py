"""
SerpentAI SDK - 记忆管理模块
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING

from .types import MemoryStats
if TYPE_CHECKING:
    from .client import SerpentAI


class MemoryManager:
    """记忆系统管理器"""
    
    def __init__(self, client: "SerpentAI"):
        self._client = client
    
    def add(
        self,
        content: str,
        session_id: str,
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        添加内容到记忆
        
        Args:
            content: 内容
            session_id: 会话ID
            role: 角色 (user/assistant/system/tool)
            metadata: 元数据
        """
        payload = {"content": content, "role": role}
        if metadata:
            payload["metadata"] = metadata
        
        result = self._client.post(f"/api/memory/add?session_id={session_id}", json=payload)
        return result.get("status") == "success"
    
    def recall(
        self,
        query: str,
        session_id: str,
        limit: int = 10,
        layers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        召回记忆
        
        Args:
            query: 查询文本
            session_id: 会话ID
            limit: 返回数量
            layers: 记忆层 (instant/short_term/long_term/archive)
        
        Returns:
            List[Dict]: 记忆列表
        """
        if layers is None:
            layers = ["instant", "short_term", "long_term"]
        
        payload = {
            "query": query,
            "limit": limit,
            "include_instant": "instant" in layers,
            "include_short_term": "short_term" in layers,
            "include_long_term": "long_term" in layers,
            "include_archive": "archive" in layers,
        }
        
        result = self._client.post(f"/api/memory/recall?session_id={session_id}", json=payload)
        return result.get("results", [])
    
    def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        layers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索记忆（跨会话）
        
        Args:
            query: 搜索关键词
            session_id: 限制到特定会话
            layers: 搜索的记忆层
        """
        payload = {"query": query}
        
        if session_id:
            payload["session_id"] = session_id
        
        if layers:
            payload["layers"] = layers
        
        result = self._client.post("/api/memory/search", json=payload)
        return result.get("results", [])
    
    def archive(
        self,
        memory_id: str,
        summary: Optional[str] = None,
    ) -> bool:
        """
        归档记忆（移动到归档层）
        
        Args:
            memory_id: 记忆ID
            summary: 归档摘要
        """
        payload = {}
        if summary:
            payload["summary"] = summary
        
        result = self._client.post(f"/api/memory/{memory_id}/archive", json=payload)
        return result.get("archived", False)
    
    def restore(
        self,
        memory_id: str,
        target_layer: str = "long_term",
    ) -> bool:
        """
        恢复归档的记忆
        
        Args:
            memory_id: 记忆ID
            target_layer: 目标层
        """
        payload = {"target_layer": target_layer}
        result = self._client.post(f"/api/memory/{memory_id}/restore", json=payload)
        return result.get("restored", False)
    
    def get_stats(self) -> MemoryStats:
        """获取记忆统计"""
        result = self._client.get("/api/memory/stats")
        return MemoryStats.from_dict(result)
    
    def clear(
        self,
        session_id: Optional[str] = None,
        layer: Optional[str] = None,
    ) -> bool:
        """
        清空记忆
        
        Args:
            session_id: 会话ID（不提供则清空所有）
            layer: 只清空特定层
        """
        params = {}
        if layer:
            params["layer"] = layer
        
        if session_id:
            result = self._client.delete(f"/api/memory/clear?session_id={session_id}", params=params)
        else:
            result = self._client.delete("/api/memory/clear", params=params)
        
        return result.get("status") == "success"
    
    def export(
        self,
        session_id: str,
        format: str = "json",
        layers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        导出记忆
        
        Args:
            session_id: 会话ID
            format: 导出格式 (json/csv/markdown)
            layers: 导出的层
        """
        params = {"format": format}
        if layers:
            params["layers"] = ",".join(layers)
        
        result = self._client.get(f"/api/memory/export/{session_id}", params=params)
        return result
    
    def import_memory(
        self,
        session_id: str,
        data: Dict[str, Any],
        layer: str = "long_term",
    ) -> int:
        """
        导入记忆
        
        Args:
            session_id: 会话ID
            data: 记忆数据
            layer: 导入到哪一层
        
        Returns:
            导入的记忆数量
        """
        payload = {"data": data, "layer": layer}
        result = self._client.post(f"/api/memory/import/{session_id}", json=payload)
        return result.get("imported", 0)
