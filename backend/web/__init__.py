"""
SerpentAI Web界面模块
FastAPI + Jinja2模板 + 静态文件
"""
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from core.config import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Web界面配置
WEB_UI_DIR = Path(__file__).parent / "static"

# 应用启动时间
APP_START_TIME = datetime.now()


def create_web_app() -> FastAPI:
    """创建Web界面应用"""
    app = FastAPI(
        title="SerpentAI Web Control",
        description="SerpentAI Web控制台",
        version="1.0.0"
    )
    
    # 静态文件
    if WEB_UI_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(WEB_UI_DIR)), name="static")
    
    # 模板引擎
    templates = Jinja2Templates(directory=str(WEB_UI_DIR / "templates"))
    
    return app, templates


# ==================== 页面路由 ====================

@app.get("/", name="index")
async def index(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "app_name": "SerpentAI",
        "version": "1.0.0"
    })


@app.get("/console")
async def console(request: Request):
    """控制台"""
    return templates.TemplateResponse("console.html", {
        "request": request
    })


@app.get("/chat")
async def chat(request: Request):
    """聊天界面"""
    return templates.TemplateResponse("chat.html", {
        "request": request
    })


@app.get("/settings")
async def settings_page(request: Request):
    """设置页面"""
    return templates.TemplateResponse("settings.html", {
        "request": request
    })


# ==================== API路由 ====================

@app.get("/api/status")
async def api_status():
    """API状态"""
    uptime_seconds = (datetime.now() - APP_START_TIME).total_seconds()
    # 格式化为可读格式
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"
    
    return {
        "status": "online",
        "version": "1.0.0",
        "uptime": uptime_str,
        "uptime_seconds": int(uptime_seconds)
    }


@app.get("/api/sessions")
async def api_sessions():
    """会话列表"""
    # TODO: 从数据库获取
    return {"sessions": []}


@app.post("/api/chat")
async def api_chat(request: Request):
    """聊天API"""
    try:
        data = await request.json()
        message = data.get("message", "")
        session_id = data.get("session_id")
        
        # TODO: 调用AI处理消息
        response = {
            "message": f"Echo: {message}",
            "session_id": session_id
        }
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory/stats")
async def api_memory_stats():
    """记忆统计"""
    # TODO: 从记忆系统获取
    return {
        "instant": {"count": 0},
        "short_term": {"count": 0},
        "long_term": {"count": 0},
        "archive": {"count": 0}
    }


@app.get("/api/tools")
async def api_tools():
    """工具列表"""
    # TODO: 从工具注册表获取
    return {"tools": []}


# ==================== WebSocket支持 ====================

@app.websocket("/ws/chat")
async def websocket_chat(websocket):
    """WebSocket聊天"""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            # TODO: 处理消息
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        await websocket.close()