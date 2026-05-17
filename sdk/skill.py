"""
SerpentAI SDK - 技能商店模块
"""

from typing import Optional, Dict, Any, List, TYPE_CHECKING

from .types import SkillInfo
if TYPE_CHECKING:
    from .client import SerpentAI


class SkillManager:
    """技能商店管理器"""
    
    def __init__(self, client: "SerpentAI"):
        self._client = client
    
    def list(
        self,
        category: Optional[str] = None,
        installed: Optional[bool] = None,
    ) -> List[SkillInfo]:
        """
        列出技能
        
        Args:
            category: 按分类过滤
            installed: 只返回已安装/未安装的技能
        """
        params = {}
        if category:
            params["category"] = category
        if installed is not None:
            params["installed"] = str(installed)
        
        result = self._client.get("/api/skills", params=params)
        return [SkillInfo.from_dict(s) for s in result.get("skills", [])]
    
    def get(self, skill_id: str) -> SkillInfo:
        """获取技能信息"""
        result = self._client.get(f"/api/skills/{skill_id}")
        return SkillInfo.from_dict(result)
    
    def install(
        self,
        skill_id: str,
        version: Optional[str] = None,
    ) -> SkillInfo:
        """
        安装技能
        
        Args:
            skill_id: 技能ID
            version: 指定版本（可选）
        
        Returns:
            SkillInfo: 安装的技能信息
        """
        payload = {}
        if version:
            payload["version"] = version
        
        result = self._client.post(f"/api/skills/{skill_id}/install", json=payload)
        return SkillInfo.from_dict(result)
    
    def uninstall(self, skill_id: str) -> bool:
        """卸载技能"""
        result = self._client.delete(f"/api/skills/{skill_id}")
        return result.get("uninstalled", False)
    
    def update(self, skill_id: str) -> SkillInfo:
        """更新技能到最新版本"""
        result = self._client.post(f"/api/skills/{skill_id}/update")
        return SkillInfo.from_dict(result)
    
    def search(
        self,
        query: str,
        category: Optional[str] = None,
        sort_by: str = "relevance",
    ) -> List[SkillInfo]:
        """
        搜索技能
        
        Args:
            query: 搜索关键词
            category: 分类过滤
            sort_by: 排序方式 (relevance/rating/install_count)
        """
        params = {"q": query, "sort_by": sort_by}
        if category:
            params["category"] = category
        
        result = self._client.get("/api/skills/search", params=params)
        return [SkillInfo.from_dict(s) for s in result.get("skills", [])]
    
    def rate(
        self,
        skill_id: str,
        rating: float,
    ) -> bool:
        """
        评价技能
        
        Args:
            skill_id: 技能ID
            rating: 评分 (1-5)
        """
        result = self._client.post(
            f"/api/skills/{skill_id}/rate",
            json={"rating": rating}
        )
        return result.get("rated", False)
    
    def get_marketplace(
        self,
        category: Optional[str] = None,
        sort_by: str = "popular",
    ) -> List[SkillInfo]:
        """
        获取技能市场
        
        Args:
            category: 分类过滤
            sort_by: 排序 (popular/new/rating)
        """
        params = {"sort_by": sort_by}
        if category:
            params["category"] = category
        
        result = self._client.get("/api/skills/marketplace", params=params)
        return [SkillInfo.from_dict(s) for s in result.get("skills", [])]
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """获取技能分类列表"""
        result = self._client.get("/api/skills/categories")
        return result.get("categories", [])
