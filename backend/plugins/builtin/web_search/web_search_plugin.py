# -*- coding: utf-8 -*-
"""
网页搜索插件 - 通过 DuckDuckGo 进行网页搜索
无需API密钥，开箱即用
"""

import json
import logging
import urllib.parse
import urllib.request
import re
from typing import Dict, List, Any, Optional

from backend.plugins.plugin_base import ToolPlugin
from backend.plugins.plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)

UA = "SerpentAI/1.0 (Plugin; WebSearch; +https://github.com/zhan1206/serpent-ai)"


def _duckduckgo_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """通过 DuckDuckGo Instant Answer API + Lite 搜索"""
    results = []
    params = urllib.parse.urlencode({"q": query})
    
    # 尝试 DuckDuckGo Instant Answer API（无需解析HTML）
    try:
        api_url = f"https://api.duckduckgo.com/?{params}&format=json&no_html=1"
        req = urllib.request.Request(api_url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", query),
                "url": data.get("AbstractURL", ""),
                "snippet": data["AbstractText"],
            })
        
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:100],
                    "url": topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", ""),
                })
    except Exception as e:
        logger.error(f"DuckDuckGo API 搜索失败: {e}")
    
    # 回退：尝试 Lite 版本
    if not results:
        try:
            url = f"https://lite.duckduckgo.com/lite/?{params}"
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            
            # 简单提取链接和文本
            a_pattern = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', re.DOTALL)
            for href, title in a_pattern.findall(html)[:max_results]:
                title = title.strip()
                actual_url = href
                if "uddg=" in href:
                    m = re.search(r"uddg=([^&]+)", href)
                    if m:
                        actual_url = urllib.parse.unquote(m.group(1))
                if title and actual_url and actual_url.startswith("http"):
                    results.append({
                        "title": title,
                        "url": actual_url,
                        "snippet": "",
                    })
        except Exception as e:
            logger.error(f"DuckDuckGo Lite 搜索失败: {e}")
    
    return results[:max_results]


class WebSearchPlugin(ToolPlugin):
    """网页搜索插件"""
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "web_search",
                "description": "搜索互联网获取最新信息。使用 DuckDuckGo 搜索引擎，无需API密钥。返回搜索结果的标题、链接和摘要。",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "最大结果数量（默认5）",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                },
                "handler": self._handle_search,
                "category": "search"
            },
        ]
    
    def _handle_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments["query"]
        max_results = arguments.get("max_results", 5)
        
        from backend.plugins.plugin_security import Permission
        if not self.context or not self.context.sandbox.check_permission(self.name, Permission.NETWORK):
            return {"error": "插件没有网络访问权限"}
        
        results = _duckduckgo_search(query, max_results)
        
        return {
            "query": query,
            "results": results,
            "count": len(results),
        }


def create_plugin(manifest: PluginManifest) -> WebSearchPlugin:
    return WebSearchPlugin(manifest)
