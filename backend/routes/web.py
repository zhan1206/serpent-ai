"""
Web界面路由
HTML页面和API端点
"""
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Web界面"])

# 模板目录
TEMPLATE_DIR = Path(__file__).parent.parent / "web" / "templates"


def read_template(template_name: str) -> str:
    """读取HTML模板"""
    template_path = TEMPLATE_DIR / template_name
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return "<h1>Template not found</h1>"


@router.get("/", response_class=HTMLResponse)
async def index():
    return read_template("index.html")


@router.get("/console", response_class=HTMLResponse)
async def console():
    return read_template("console.html")


@router.get("/chat", response_class=HTMLResponse)
async def chat():
    return read_template("chat.html")


@router.get("/settings", response_class=HTMLResponse)
async def settings():
    return read_template("settings.html")


@router.get("/api/status")
async def api_status():
    return {"status": "online", "version": "1.0.0"}


@router.get("/api/sessions")
async def api_sessions():
    return {"sessions": []}


@router.post("/api/chat")
async def api_chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
        session_id = data.get("session_id")
        
        # TODO: 接入AI处理
        response = {"message": f"Echo: {message}", "session_id": session_id}
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/memory/stats")
async def api_memory_stats():
    return {
        "instant": {"count": 0},
        "short_term": {"count": 0},
        "long_term": {"count": 0},
        "archive": {"count": 0}
    }


@router.get("/api/tools")
async def api_tools():
    return {"tools": []}