"""
SerpentAI SDK - 插件管理模块
"""

from typing import Optional, Dict, Any, List, TYPE_CHECKING

from .types import PluginInfo
if TYPE_CHECKING:
    from .client import SerpentAI


class PluginManager:
    """插件管理器"""
    
    def __init__(self, client: "SerpentAI"):
        self._client = client
    
    def list(
        self,
        category: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> List[PluginInfo]:
        """
        列出插件
        
        Args:
            category: 按分类过滤
            enabled: 只返回启用/禁用的插件
        """
        params = {}
        if category:
            params["category"] = category
        if enabled is not None:
            params["enabled"] = str(enabled)
        
        result = self._client.get("/api/plugins", params=params)
        return [PluginInfo.from_dict(p) for p in result.get("plugins", [])]
    
    def get(self, plugin_id: str) -> PluginInfo:
        """获取插件信息"""
        result = self._client.get(f"/api/plugins/{plugin_id}")
        return PluginInfo.from_dict(result)
    
    def install(
        self,
        source: str,
        name: Optional[str] = None,
    ) -> PluginInfo:
        """
        安装插件
        
        Args:
            source: 插件来源 (URL/GitHub/本地路径)
            name: 插件名称
        
        Returns:
            PluginInfo: 安装的插件信息
        """
        payload = {"source": source}
        if name:
            payload["name"] = name
        
        result = self._client.post("/api/plugins/install", json=payload)
        return PluginInfo.from_dict(result)
    
    def uninstall(self, plugin_id: str) -> bool:
        """卸载插件"""
        result = self._client.delete(f"/api/plugins/{plugin_id}")
        return result.get("uninstalled", False)
    
    def enable(self, plugin_id: str) -> bool:
        """启用插件"""
        result = self._client.post(f"/api/plugins/{plugin_id}/enable")
        return result.get("enabled", False)
    
    def disable(self, plugin_id: str) -> bool:
        """禁用插件"""
        result = self._client.post(f"/api/plugins/{plugin_id}/disable")
        return result.get("disabled", False)
    
    def reload(self, plugin_id: str) -> PluginInfo:
        """热重载插件"""
        result = self._client.post(f"/api/plugins/{plugin_id}/reload")
        return PluginInfo.from_dict(result)
    
    def execute(
        self,
        plugin_id: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        执行插件动作
        
        Args:
            plugin_id: 插件ID
            action: 动作名称
            params: 动作参数
        """
        payload = {"action": action, "params": params or {}}
        result = self._client.post(f"/api/plugins/{plugin_id}/execute", json=payload)
        return result.get("result")
    
    def get_config(self, plugin_id: str) -> Dict[str, Any]:
        """获取插件配置"""
        return self._client.get(f"/api/plugins/{plugin_id}/config")
    
    def update_config(self, plugin_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """更新插件配置"""
        return self._client.put(f"/api/plugins/{plugin_id}/config", json=config)
    
    def search(self, query: str) -> List[PluginInfo]:
        """搜索插件"""
        result = self._client.get("/api/plugins/search", params={"q": query})
        return [PluginInfo.from_dict(p) for p in result.get("plugins", [])]
    
    def get_marketplace(self) -> List[Dict[str, Any]]:
        """获取插件市场列表"""
        result = self._client.get("/api/plugins/marketplace")
        return result.get("plugins", [])
