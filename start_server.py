"""
SerpentAI 启动脚本
自动配置 PYTHONPATH 并启动 FastAPI 服务器
"""
import sys
import os
from pathlib import Path

# 配置 PYTHONPATH - 关键：同时添加项目根目录和 backend 目录
project_root = Path(__file__).resolve().parent
backend_dir = project_root / "backend"

# 添加到 sys.path（backend 优先，这样 core/tools/routes 等相对导入能找到）
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print(f"Python path configured:")
print(f"  - Project root: {project_root}")
print(f"  - Backend dir:  {backend_dir}")
print()

# 启动 uvicorn
import uvicorn
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=8000,
    reload=False,
    log_level="info",
)
