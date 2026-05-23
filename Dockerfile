# SerpentAI Dockerfile
# 多阶段构建：开发/生产一体化

FROM python:3.12-slim-bookworm AS base

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash --uid 1000 serpent
WORKDIR /app

# 安装 Python 依赖
COPY --chown=serpent:serpent requirements.txt requirements-optional.txt* ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    (pip install -r requirements-optional.txt 2>/dev/null || true)

# 复制项目文件
COPY --chown=serpent:serpent . .

# 创建必要目录
RUN mkdir -p /app/data/chroma /app/backend/logs /app/models && \
    chown -R serpent:serpent /app

USER serpent

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "start_server.py"]
