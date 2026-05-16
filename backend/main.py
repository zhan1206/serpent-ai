"""
SerpentAI 主应用入口
FastAPI应用初始化、路由配置、中间件设置
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from core.config import settings, get_settings
from core.logging_config import setup_logging, get_logger
from core.database import init_db, check_db_health

# 初始化日志
setup_logging()
logger = get_logger(__name__)

# ==================== 生命周期管理 ====================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理
    启动时初始化资源，关闭时清理资源
    """
    logger.info("=" * 60)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 正在启动...")
    logger.info("=" * 60)
    
    try:
        # 初始化数据库
        logger.info("正在初始化数据库...")
        init_db()
        
        # 检查数据库连接
        db_health = check_db_health()
        logger.info(f"数据库健康检查: {db_health}")
        
        # 初始化Neo4j约束
        from core.database import init_neo4j_constraints
        try:
            init_neo4j_constraints()
        except Exception as e:
            logger.warning(f"Neo4j初始化失败（可稍后重试）: {e}")
        
        logger.info(f"{settings.APP_NAME} 启动完成！")
        logger.info(f"调试模式: {settings.DEBUG}")
        logger.info(f"环境: {settings.ENVIRONMENT}")
        
    except Exception as e:
        logger.error(f"启动失败: {e}")
        raise
    
    yield  # 应用运行期间
    
    # 关闭时清理资源
    logger.info("正在关闭应用...")
    
    from core.database import close_neo4j_driver
    close_neo4j_driver()
    
    logger.info("应用已关闭")

# ==================== FastAPI应用初始化 ====================

app = FastAPI(
    title=settings.APP_NAME,
    description="终极自托管全功能AI智能体框架",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# ==================== 中间件配置 ====================

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 路由配置 ====================

@app.get("/")
async def root():
    """根路由 - API信息"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "终极自托管全功能AI智能体框架",
        "documentation": "/api/docs",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """
    健康检查端点
    用于监控和负载均衡器探测
    """
    db_health = check_db_health()
    
    health_status = {
        "status": "healthy" if all(db_health.values()) else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_health,
    }
    
    return health_status

@app.get("/api/models")
async def list_models():
    """
    列出所有支持的模型
    """
    from models.base_model import list_supported_models
    return {
        "models": list_supported_models(),
        "count": len(list_supported_models())
    }

@app.post("/api/chat")
async def chat(request: Request):
    """
    聊天接口（简化版）
    接收消息，调用模型生成响应
    """
    try:
        data = await request.json()
        
        model_name = data.get("model", "gpt-3.5-turbo")
        messages = data.get("messages", [])
        
        if not messages:
            raise HTTPException(status_code=400, detail="消息列表不能为空")
        
        # 创建模型适配器
        from models.base_model import create_adapter
        from models.base_model import Message
        
        adapter = create_adapter(model_name)
        
        # 转换消息格式
        chat_messages = [
            Message(role=msg["role"], content=msg["content"])
            for msg in messages
        ]
        
        # 生成响应
        response = adapter.generate(chat_messages)
        
        return {
            "response": response.content,
            "model": response.model,
            "usage": {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "total_tokens": response.total_tokens,
            },
            "cost": response.cost,
            "latency_ms": response.latency_ms,
        }
        
    except Exception as e:
        logger.error(f"聊天接口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 错误处理 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": str(exc),
            "type": type(exc).__name__
        }
    )

# ==================== 启动脚本 ====================

if __name__ == "__main__":
    """
    本地开发启动入口
    生产环境应使用: uvicorn backend.main:app --host 0.0.0.0 --port 8000
    """
    logger.info("启动本地开发服务器...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
