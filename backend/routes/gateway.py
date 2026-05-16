"""
多通道网关API路由
飞书、Discord、Telegram等多平台消息接入
"""
from fastapi import APIRouter, Request, HTTPException, Query
from typing import Dict, Any, Optional

router = APIRouter(prefix="/api/gateway", tags=["多通道网关"])


@router.post("/initialize")
async def initialize_gateways(request: Request):
    """初始化所有启用的网关平台"""
    try:
        from gateways import get_gateway_manager
        data = await request.json()
        manager = get_gateway_manager()
        results = await manager.initialize(data.get("platforms", {}))
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def gateway_health_check():
    """网关健康检查"""
    try:
        from gateways import get_gateway_manager
        manager = get_gateway_manager()
        return await manager.health_check()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send")
async def send_gateway_message(request: Request):
    """发送消息到指定平台"""
    try:
        from gateways import get_gateway_manager, Response
        data = await request.json()
        platform = data.get("platform")
        message = data.get("message", "")
        msg_type = data.get("msg_type", "text")
        target = data.get("target", {})
        
        if not platform:
            raise HTTPException(status_code=400, detail="缺少platform参数")
        
        manager = get_gateway_manager()
        response = Response(message=message, msg_type=msg_type)
        success = await manager.send_message(platform, response, target)
        
        return {"status": "success" if success else "failed", "platform": platform}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/broadcast")
async def broadcast_message(request: Request):
    """广播消息到多个平台"""
    try:
        from gateways import get_gateway_manager, Response
        data = await request.json()
        platforms = data.get("platforms", [])
        message = data.get("message", "")
        msg_type = data.get("msg_type", "text")
        targets = data.get("targets", {})
        
        manager = get_gateway_manager()
        response = Response(message=message, msg_type=msg_type)
        results = await manager.broadcast(platforms, response, targets)
        
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register-handler")
async def register_message_handler(request: Request):
    """注册消息处理器"""
    try:
        from gateways import get_message_router
        data = await request.json()
        platform = data.get("platform")
        handler_path = data.get("handler")
        
        if not platform:
            raise HTTPException(status_code=400, detail="缺少platform参数")
        
        router_instance = get_message_router()
        # TODO: 实现动态导入handler
        return {"status": "success", "platform": platform}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def gateway_health_check():
    """网关健康检查"""
    try:
        from gateways import get_gateway_manager
        manager = get_gateway_manager()
        
        # 检查所有已注册的适配器
        adapters = {}
        for name, adapter in manager._adapters.items():
            try:
                adapters[name] = "healthy" if adapter else "error"
            except Exception:
                adapters[name] = "error"
        
        all_healthy = all(v == "healthy" for v in adapters.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "adapters": adapters
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }