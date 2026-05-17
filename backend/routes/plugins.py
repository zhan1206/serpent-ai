# -*- coding: utf-8 -*-
"""
插件与技能 API 路由
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from backend.plugins.plugin_manager import get_plugin_manager
from backend.plugins.plugin_registry import get_plugin_registry
from backend.skills.skill_store import get_skill_store
from backend.skills.skill_installer import SkillInstaller

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["plugins-skills"])

class PluginLoadRequest(BaseModel):
    name: str
    config: dict = {}

class PluginUnloadRequest(BaseModel):
    name: str

class SkillInstallRequest(BaseModel):
    url: str = ""
    data: dict = None

@router.get("/plugins")
async def list_plugins(state: Optional[str] = None, plugin_type: Optional[str] = None):
    try:
        registry = get_plugin_registry()
        plugins = registry.list_plugins(state=state, plugin_type=plugin_type)
        return {"plugins": plugins, "stats": registry.get_plugin_count(), "total": len(plugins)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/plugins/load")
async def load_plugin(request: PluginLoadRequest):
    try:
        manager = get_plugin_manager()
        plugin = manager.load_plugin(request.name, request.config)
        return {"status": "success", "plugin": plugin.get_info()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/plugins/unload")
async def unload_plugin(request: PluginUnloadRequest):
    try:
        manager = get_plugin_manager()
        if not manager.unload_plugin(request.name):
            raise HTTPException(status_code=404, detail=f"插件 {request.name} 未找到")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/plugins/reload")
async def reload_plugin(request: PluginLoadRequest):
    try:
        manager = get_plugin_manager()
        plugin = manager.reload_plugin(request.name)
        return {"status": "success", "plugin": plugin.get_info()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plugins/{name}")
async def get_plugin(name: str):
    try:
        registry = get_plugin_registry()
        plugin = registry.get_plugin(name)
        if not plugin:
            raise HTTPException(status_code=404, detail=f"插件 {name} 不存在")
        instance = registry.get_instance(name)
        info = plugin.copy()
        if instance:
            info["instance_info"] = instance.get_info()
        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plugins/search")
async def search_plugins(query: str = Query(...)):
    try:
        registry = get_plugin_registry()
        results = registry.search(query)
        return {"query": query, "results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/skills")
async def list_skills(category: Optional[str] = None, enabled_only: bool = False):
    try:
        store = get_skill_store()
        skills = store.list_skills(category=category, enabled_only=enabled_only)
        return {"skills": skills, "stats": store.get_stats(), "total": len(skills)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/skills/install")
async def install_skill(request: SkillInstallRequest):
    try:
        store = get_skill_store()
        if request.data:
            skill = store.install_skill(request.data, "data/skills")
        elif request.url:
            installer = SkillInstaller("data/skills")
            skill = installer.install_from_url(request.url)
            store.add_skill_dir("data/skills")
            store.discover_all()
            skill = store.get_skill(skill.name)
        else:
            raise HTTPException(status_code=400, detail="需要提供 url 或 data")
        return {"status": "success", "skill": skill.get_info() if skill else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/skills/{name}")
async def remove_skill(name: str):
    try:
        store = get_skill_store()
        if not store.remove_skill(name):
            raise HTTPException(status_code=404, detail=f"技能 {name} 不存在")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/skills/{name}/enable")
async def enable_skill(name: str):
    try:
        store = get_skill_store()
        if not store.enable_skill(name):
            raise HTTPException(status_code=404)
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/skills/{name}/disable")
async def disable_skill(name: str):
    try:
        store = get_skill_store()
        if not store.disable_skill(name):
            raise HTTPException(status_code=404)
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/skills/{name}/rate")
async def rate_skill(name: str, rating: float = Query(..., ge=1, le=5)):
    try:
        store = get_skill_store()
        if not store.rate_skill(name, rating):
            raise HTTPException(status_code=404)
        skill = store.get_skill(name)
        return {"status": "success", "rating": skill.rating, "count": skill.rating_count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/skills/search")
async def search_skills(query: str = Query(...)):
    try:
        store = get_skill_store()
        results = store.search(query)
        return {"query": query, "results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/skills/categories")
async def list_skill_categories():
    try:
        store = get_skill_store()
        return {"categories": store.get_categories()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
