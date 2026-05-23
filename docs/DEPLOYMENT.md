# SerpentAI 生产环境部署文档

本文档提供 SerpentAI 在生产环境中的完整部署指南。

## 目录

1. [系统要求](#系统要求)
2. [快速部署](#快速部署)
3. [详细部署步骤](#详细部署步骤)
4. [配置管理](#配置管理)
5. [数据库配置](#数据库配置)
6. [安全加固](#安全加固)
7. [性能优化](#性能优化)
8. [监控与告警](#监控与告警)
9. [备份与恢复](#备份与恢复)
10. [故障排除](#故障排除)
11. [附录](#附录)

---

## 系统要求

### 最低配置（测试/小规模）

| 资源 | 要求 |
|------|------|
| CPU | 4 核 |
| 内存 | 8 GB |
| 存储 | 50 GB SSD |
| 网络 | 100 Mbps |

### 推荐配置（生产/中大规模）

| 资源 | 要求 |
|------|------|
| CPU | 8-16 核 |
| 内存 | 32-64 GB |
| 存储 | 500 GB SSD (RAID 1) |
| 网络 | 1 Gbps |

### 本地模型专用配置

| 资源 | 要求（7B 模型） | 要求（70B 模型） |
|------|-------------------|--------------------|
| CPU | 8 核 | 16 核 |
| 内存 | 16 GB | 64 GB |
| GPU | 可选（4GB+ VRAM） | 推荐（24GB+ VRAM） |
| 存储 | 10 GB | 50 GB |

### 软件要求

- **操作系统**: Ubuntu 22.04 LTS / CentOS 8 / Windows Server 2022
- **Python**: 3.10, 3.11, 3.12
- **Docker**: 24.0+ (可选，推荐)
- **数据库**: SQLite 3.35+ (内置), ChromaDB 0.4+ (可选), Neo4j 5.0+ (可选)
- **Redis**: 7.0+ (可选，用于分布式缓存)

---

## 快速部署

### 方式1：Docker 部署（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/zhan1206/serpent-ai.git
cd serpent-ai

# 2. 复制配置
cp .env.example .env

# 3. 编辑配置（填写 API Key 等）
vim .env

# 4. 启动服务
docker compose up -d

# 5. 查看日志
docker compose logs -f

# 6. 验证服务
curl http://localhost:8000/health
```

### 方式2：手动部署

```bash
# 1. 克隆仓库
git clone https://github.com/zhan1206/serpent-ai.git
cd serpent-ai

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt
pip install -r requirements-optional.txt  # 可选依赖

# 4. 复制配置
cp .env.example .env
vim .env  # 编辑配置

# 5. 初始化数据库
python -m backend.core.database init

# 6. 启动服务器
python start_server.py

# 或生产模式（使用 gunicorn）
gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 backend.main:app
```

---

## 详细部署步骤

### 步骤1：准备服务器

#### Ubuntu/Debian

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装依赖
sudo apt install -y python3.12 python3-pip python3-venv git docker.io docker-compose-v2

# 安装 Node.js（可选，用于前端开发）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 添加用户
sudo useradd -m -s /bin/bash serpent
sudo usermod -aG docker serpent

# 切换用户
su - serpent
```

#### CentOS/RHEL

```bash
# 更新系统
sudo dnf update -y

# 安装 Python 3.12
sudo dnf install -y python3.12 python3-pip python3-virtualenv git docker

# 启动 Docker
sudo systemctl enable --now docker

# 添加用户
sudo useradd -m -s /bin/bash serpent
sudo usermod -aG docker serpent

# 切换用户
su - serpent
```

### 步骤2：获取代码

```bash
# 克隆仓库
git clone https://github.com/zhan1206/serpent-ai.git
cd serpent-ai

# 切换到稳定分支
git checkout main  # 或指定版本标签：git checkout v0.1.0
```

### 步骤3：配置环境

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置
vim .env
```

**关键配置项**：

```bash
# .env

# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=false  # ⚠️ 生产环境必须为 false
LOG_LEVEL=WARNING  # 生产环境推荐 WARNING 或 ERROR

# 模型配置（至少配置一个）
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# 安全配置（⚠️ 必须修改！）
SECRET_KEY=your-secure-secret-key-here  # 使用 openssl rand -hex 32 生成
JWT_SECRET=your-jwt-secret-here

# 数据库配置
SQLITE_URL=sqlite+aiosqlite:///var/lib/serpent-ai/data/serpent-ai.db
CHROMADB_PERSIST_DIR=/var/lib/serpent-ai/data/chroma
NEO4J_PASSWORD=your-secure-neo4j-password

# Redis 配置（可选）
REDIS_PASSWORD=your-secure-redis-password

# CORS 配置（生产环境必须指定具体域名）
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### 步骤4：安装依赖

#### 方式1：使用 requirements.txt

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 安装可选依赖（根据需要）
pip install -r requirements-optional.txt  # ChromaDB, Neo4j, etc.
pip install gunicorn  # 生产服务器
```

#### 方式2：使用 Poetry

```bash
# 安装 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 安装依赖
poetry install

# 激活虚拟环境
poetry shell
```

#### 方式3：使用 Docker

```bash
# 构建镜像
docker build -t serpent-ai:latest .

# 运行容器
docker run -d \
  --name serpent-ai \
  -p 8000:8000 \
  --env-file .env \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  serpent-ai:latest
```

### 步骤5：初始化数据库

```bash
# SQLite（默认）
mkdir -p data logs
python -m backend.core.database init

# ChromaDB（向量数据库）
docker run -d \
  --name chromadb \
  -p 8000:8000 \
  -v ./data/chroma:/chroma/chroma \
  -e IS_PERSISTENT=TRUE \
  chromadb/chroma:latest

# Neo4j（知识图谱）
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -v ./data/neo4j:/data \
  -e NEO4J_AUTH=neo4j/your-secure-password \
  neo4j:5.0
```

### 步骤6：启动服务器

#### 方式1：使用 start_server.py（开发/测试）

```bash
python start_server.py
```

#### 方式2：使用 Gunicorn + Uvicorn（生产推荐）

```bash
# 安装 gunicorn 和 uvicorn
pip install gunicorn uvicorn

# 启动（4 个 worker）
gunicorn \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  --log-level warning \
  --timeout 120 \
  --keep-alive 5 \
  backend.main:app
```

#### 方式3：使用 systemd（Linux 服务）

创建服务文件 `/etc/systemd/system/serpent-ai.service`：

```ini
[Unit]
Description=SerpentAI API Server
After=network.target

[Service]
Type=simple
User=serpent
Group=serpent
WorkingDirectory=/home/serpent/serpent-ai
Environment="PATH=/home/serpent/serpent-ai/venv/bin"
ExecStart=/home/serpent/serpent-ai/venv/bin/gunicorn \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile /var/log/serpent-ai/access.log \
  --error-logfile /var/log/serpent-ai/error.log \
  --log-level warning \
  --timeout 120 \
  backend.main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
# 创建日志目录
sudo mkdir -p /var/log/serpent-ai
sudo chown -R serpent:serpent /var/log/serpent-ai

# 启用服务
sudo systemctl enable serpent-ai
sudo systemctl start serpent-ai

# 查看状态
sudo systemctl status serpent-ai

# 查看日志
sudo journalctl -u serpent-ai -f
```

#### 方式4：使用 Docker Compose（推荐）

```bash
# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down

# 重启服务
docker compose restart
```

### 步骤7：配置反向代理（Nginx）

安装 Nginx：

```bash
sudo apt install -y nginx  # Ubuntu/Debian
sudo dnf install -y nginx  # CentOS/RHEL
```

创建配置文件 `/etc/nginx/sites-available/serpent-ai`：

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL 证书（使用 Let's Encrypt）
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 请求限制
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # 代理配置
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # 静态文件（可选）
    location /static/ {
        alias /var/lib/serpent-ai/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 上传文件大小限制
    client_max_body_size 100M;
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/serpent-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 步骤8：配置 SSL 证书（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx  # Ubuntu/Debian
sudo dnf install -y certbot python3-certbot-nginx  # CentOS/RHEL

# 获取证书
sudo certbot --nginx -d api.yourdomain.com

# 自动续期
sudo systemctl enable certbot.timer
```

---

## 配置管理

### 环境变量管理

#### 方式1：使用 .env 文件（推荐）

```bash
# 复制模板
cp .env.example .env

# 编辑配置
vim .env

# 确保 .env 不在 Git 中
echo ".env" >> .gitignore
```

#### 方式2：使用 systemd 环境变量

```bash
# 创建环境变量文件
sudo mkdir -p /etc/serpent-ai
sudo vim /etc/serpent-ai/environment

# 内容：
# OPENAI_API_KEY=sk-xxx
# ANTHROPIC_API_KEY=sk-ant-xxx
# SECRET_KEY=xxx

# 在 systemd 服务文件中引用
# EnvironmentFile=/etc/serpent-ai/environment
```

#### 方式3：使用 Docker Secrets

```bash
# 创建 secrets
echo "sk-your-openai-key" | docker secret create openai_api_key -
echo "sk-ant-your-anthropic-key" | docker secret create anthropic_api_key -

# 在 docker-compose.yml 中引用
# secrets:
#   - openai_api_key
#   - anthropic_api_key
```

### 敏感数据管理

**⚠️ 绝对不要**：
- 提交 `.env` 到 Git
- 硬编码 API Key 在代码中
- 在日志中打印 API Key

**推荐做法**：
- 使用密钥管理服务（AWS Secrets Manager, Azure Key Vault, HashiCorp Vault）
- 使用环境变量
- 定期轮换 API Key

---

## 数据库配置

### SQLite（默认，适合小规模）

```bash
# 配置
SQLITE_URL=sqlite+aiosqlite:///var/lib/serpent-ai/data/serpent-ai.db

# 初始化
python -m backend.core.database init

# 备份
cp /var/lib/serpent-ai/data/serpent-ai.db /backup/serpent-ai-$(date +%Y%m%d).db

# 恢复
cp /backup/serpent-ai-20260523.db /var/lib/serpent-ai/data/serpent-ai.db
```

### ChromaDB（向量数据库，推荐）

#### 方式1：使用 Docker（推荐）

```bash
docker run -d \
  --name chromadb \
  -p 8000:8000 \
  -v ./data/chroma:/chroma/chroma \
  -e IS_PERSISTENT=TRUE \
  -e CHROMA_SERVER_AUTH_CREDENTIALS_PROVIDER="chromadb.auth.simple_password_admin_auth_provider.SimplePasswordAdminAuthProvider" \
  -e CHROMA_SERVER_AUTH_CREDENTIALS_FILE="/chroma/credentials.json" \
  chromadb/chroma:latest
```

#### 方式2：使用 Python 包

```bash
pip install chromadb

# 配置
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
CHROMADB_PERSIST_DIR=./data/chroma

# 启动服务器
chroma run --host 0.0.0.0 --port 8000 --path ./data/chroma
```

### Neo4j（知识图谱，可选）

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -v ./data/neo4j:/data \
  -v ./data/neo4j/logs:/logs \
  -e NEO4J_AUTH=neo4j/your-secure-password \
  -e NEO4J_PLUGINS='[{"name":"apoc"},{"name":"graph-data-science"}]' \
  neo4j:5.0
```

访问 Neo4j 浏览器：`http://your-server:7474`

### Redis（分布式缓存，推荐）

```bash
docker run -d \
  --name redis \
  -p 6379:6379 \
  -v ./data/redis:/data \
  -e REDIS_PASSWORD=your-secure-redis-password \
  redis:7.0 redis-server --requirepass your-secure-redis-password

# 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-secure-redis-password
REDIS_DB=0
```

---

## 安全加固

### 1. API 认证

#### 方式1：API Key 认证

```bash
# 配置
API_KEYS=key1-value,key2-value,key3-value

# 使用
curl -H "X-API-Key: key1-value" http://localhost:8000/api/chat
```

#### 方式2：JWT Token 认证

```bash
# 配置
JWT_SECRET=your-jwt-secret-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# 获取 Token
POST /api/auth/token
{
  "username": "admin",
  "password": "your-password"
}

# 使用 Token
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/chat
```

### 2. 输入验证和过滤

 SerpentAI 内置 5 层安全防御：

1. **输入验证层** (`backend/security/input_guard.py`)
   - 注入检测（SQL 注入、XSS、命令注入）
   - 内容过滤（敏感词、恶意代码）
   - 长度限制

2. **限流层** (`backend/security/rate_limiter.py`)
   - Token Bucket 算法
   - 按 IP/用户限流
   - 可配置速率

3. **认证层** (`backend/security/auth.py`)
   - API Key 认证
   - JWT Token 认证
   - OAuth2 支持（可选）

4. **访问控制层** (`backend/security/access_control.py`)
   - RBAC（基于角色的访问控制）
   - 细粒度权限管理
   - 资源级授权

5. **审计层** (`backend/security/audit_logger.py`)
   - 记录所有关键操作
   - 支持日志轮转
   - 审计日志查询

### 3. HTTPS/SSL 配置

**⚠️ 生产环境必须使用 HTTPS！**

```nginx
# Nginx SSL 配置
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers HIGH:!aNULL:!MD5;
}
```

### 4. CORS 配置

```bash
# .env
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# ⚠️ 不要使用 ALLOWED_ORIGINS=* （允许所有来源）
```

### 5. 安全 Headers

```nginx
# Nginx 配置
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
```

### 6. 沙箱隔离

```bash
# .env
SANDBOX_MODE=docker  # 推荐使用 docker 沙箱
SANDBOX_TIMEOUT=30  # 工具执行超时（秒）
SANDBOX_MEMORY_LIMIT=512  # 内存限制（MB）
```

使用 Docker 沙箱：

```bash
# 安装 Docker
sudo apt install -y docker.io

# 添加用户到 docker 组
sudo usermod -aG docker $USER

# 重启会话
logout
```

### 7. 定期安全审计

```bash
# 检查依赖漏洞
pip install safety
safety check

# 检查代码安全
pip install bandit
bandit -r backend/

# 扫描敏感信息
grep -r "sk-" . --include="*.py"
grep -r "password" . --include="*.py"
```

---

## 性能优化

### 1. Worker 数量优化

```bash
# 推荐 worker 数量：CPU 核心数 × 2 + 1
# 例如：4 核 CPU → 9 workers

gunicorn \
  --workers 9 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  backend.main:app
```

### 2. 启用缓存

```bash
# .env
CACHE_STRATEGY=two-tier  # memory + redis
CACHE_TTL=3600  # 默认缓存时间（秒）

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
```

### 3. 数据库连接池

```bash
# .env
DATABASE_POOL_SIZE=20  # 连接池大小
DATABASE_MAX_OVERFLOW=10  # 最大溢出连接数
DATABASE_POOL_TIMEOUT=30  # 获取连接超时（秒）
```

### 4. 异步任务队列

```bash
# 安装 Celery
pip install celery redis

# 启动 Worker
celery -A backend.core.tasks worker --loglevel=warning --concurrency=4

# 启动 Beat（定时任务）
celery -A backend.core.tasks beat --loglevel=warning
```

### 5. 使用本地模型（降低延迟）

```bash
# 安装 llama-cpp-python
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python

# 下载量化模型
from huggingface_hub import hf_hub_download
model_path = hf_hub_download(repo_id="TheBloke/Llama-3-8B-Instruct-GGUF", filename="llama-3-8b-instruct.q4_k_m.gguf", local_dir="./models")

# 配置
LLAMA_CPP_THREADS=8
LLAMA_CPP_GPU_LAYERS=32  # GPU 加速层数
```

### 6. 负载均衡

使用 Nginx 实现负载均衡：

```nginx
upstream serpent_ai_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://serpent_ai_backend;
        # ... 其他配置
    }
}
```

启动多个实例：

```bash
# 实例 1
gunicorn --workers 2 --bind 127.0.0.1:8000 backend.main:app &

# 实例 2
gunicorn --workers 2 --bind 127.0.0.1:8001 backend.main:app &

# 实例 3
gunicorn --workers 2 --bind 127.0.0.1:8002 backend.main:app &

# 实例 4
gunicorn --workers 2 --bind 127.0.0.1:8003 backend.main:app &
```

---

## 监控与告警

### 1. 健康检查

```bash
# 健康检查端点
curl http://localhost:8000/health

# 预期响应
{
  "status": "healthy",
  "service": "web",
  "timestamp": "2026-05-23T13:00:00"
}
```

### 2. 指标监控

#### 使用 Prometheus + Grafana

```bash
# 启用 Prometheus
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# 安装 Prometheus 和 Grafana
docker run -d --name prometheus -p 9090:9090 prom/prometheus
docker run -d --name grafana -p 3000:3000 grafana/grafana
```

访问 Grafana：`http://your-server:3000`（默认用户名/密码：admin/admin）

#### 使用 OpenTelemetry

```bash
# 启用 OpenTelemetry
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# 安装 OpenTelemetry Collector
docker run -d --name otel-collector -p 4317:4317 -p 8889:8889 otel/opentelemetry-collector-contrib
```

### 3. 日志监控

#### 使用 ELK Stack（Elasticsearch + Logstash + Kibana）

```bash
# 启动 ELK
docker compose -f docker-compose-elk.yml up -d

# 配置 Logstash 输入
input {
  file {
    path => "/var/log/serpent-ai/*.log"
    start_position => "beginning"
  }
}

# 配置 Logstash 输出
output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "serpent-ai-%{+YYYY.MM.dd}"
  }
}
```

#### 使用 Loki + Promtail + Grafana

```bash
# 启动 Loki 和 Promtail
docker run -d --name loki -p 3100:3100 grafana/loki
docker run -d --name promtail -v /var/log/serpent-ai:/var/log promtail/promtail
```

### 4. 告警配置

#### 使用 Alertmanager

```yaml
# alertmanager.yml
route:
  receiver: 'email-alerts'

receivers:
  - name: 'email-alerts'
    email_configs:
      - to: 'admin@yourdomain.com'
        from: 'alerts@yourdomain.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@yourdomain.com'
        auth_password: 'your-app-password'
```

#### 关键告警指标

| 指标 | 阈值 | 严重程度 |
|------|------|----------|
| CPU 使用率 | > 80% (5分钟) | 警告 |
| 内存使用率 | > 90% | 严重 |
| 磁盘使用率 | > 85% | 警告 |
| 磁盘使用率 | > 95% | 严重 |
| API 错误率 | > 5% (5分钟) | 警告 |
| API 错误率 | > 10% (5分钟) | 严重 |
| API 延迟 (P99) | > 5秒 | 警告 |
| API 延迟 (P99) | > 10秒 | 严重 |
| 健康检查失败 | 连续 3 次 | 严重 |

---

## 备份与恢复

### 1. 数据库备份

#### SQLite

```bash
# 备份
cp /var/lib/serpent-ai/data/serpent-ai.db /backup/serpent-ai-$(date +%Y%m%d-%H%M%S).db

# 或使用 sqlite3 命令
sqlite3 /var/lib/serpent-ai/data/serpent-ai.db ".backup /backup/serpent-ai-$(date +%Y%m%d-%H%M%S).db"

# 自动化备份（crontab）
0 2 * * * cp /var/lib/serpent-ai/data/serpent-ai.db /backup/serpent-ai-$(date +\%Y\%m\%d).db
```

#### ChromaDB

```bash
# 备份
tar -czf /backup/chroma-$(date +%Y%m%d-%H%M%S).tar.gz ./data/chroma

# 恢复
tar -xzf /backup/chroma-20260523-020000.tar.gz -C ./
```

#### Neo4j

```bash
# 备份
docker exec neo4j neo4j-admin database dump neo4j --to-path=/backup/neo4j-$(date +%Y%m%d-%H%M%S).dump

# 恢复
docker exec neo4j neo4j-admin database load neo4j --from-path=/backup/neo4j-20260523-020000.dump
```

### 2. 配置文件备份

```bash
# 备份配置文件
tar -czf /backup/config-$(date +%Y%m%d-%H%M%S).tar.gz .env docker-compose.yml nginx/ logs/

# 自动化备份
0 2 * * 0 tar -czf /backup/config-$(date +\%Y\%m\%d).tar.gz .env docker-compose.yml nginx/ logs/
```

### 3. 恢复演练

**定期（每季度）进行恢复演练**，确保备份可用。

```bash
# 恢复 SQLite
cp /backup/serpent-ai-20260523.db /var/lib/serpent-ai/data/serpent-ai.db
systemctl restart serpent-ai

# 恢复 ChromaDB
rm -rf ./data/chroma/*
tar -xzf /backup/chroma-20260523.tar.gz -C ./
systemctl restart serpent-ai

# 恢复 Neo4j
docker stop neo4j
docker rm neo4j
docker run -d --name neo4j -v /backup/neo4j-20260523.dump:/backup/neo4j.dump ... neo4j:5.0
docker exec neo4j neo4j-admin database load neo4j --from-path=/backup/neo4j.dump
```

---

## 故障排除

### 问题1：服务器无法启动

**症状**：`Error: [Errno 10048] error while attempting to bind on address`

**原因**：端口被占用

**解决方案**：

```bash
# 查找占用端口的进程
sudo netstat -tulpn | grep 8000

# 杀死进程
kill -9 <PID>

# 或使用其他端口
gunicorn --bind 0.0.0.0:8001 backend.main:app
```

### 问题2：API Key 无效

**症状**：`OpenAI适配器初始化失败: AuthenticationError`

**解决方案**：

1. 检查 `.env` 中的 API Key 是否正确
2. 检查 API Key 是否有余额
3. 测试 API Key：

```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### 问题3：内存不足

**症状**：`OutOfMemoryError: CUDA out of memory` 或服务器被杀死

**解决方案**：

1. 减少 Worker 数量
2. 启用虚拟内存（Swap）
3. 使用更小的模型
4. 限制并发请求数

```bash
# 创建 Swap 文件（4GB）
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久启用
echo "/swapfile swap swap defaults 0 0" | sudo tee -a /etc/fstab
```

### 问题4：API 响应慢

**原因1**：网络延迟

**解决方案**：使用本地模型或选择更近的 API 端点

**原因2**：模型太大

**解决方案**：使用更小的模型（`gpt-4o-mini` 而非 `gpt-4o`）

**原因3**：未启用缓存

**解决方案**：

```bash
# .env
CACHE_STRATEGY=two-tier
CACHE_TTL=3600
```

### 问题5：数据库连接失败

**症状**：`Database connection failed`

**解决方案**：

1. 检查数据库服务是否运行
2. 检查连接字符串是否正确
3. 检查防火墙规则

```bash
# 检查 PostgreSQL 是否运行
sudo systemctl status postgresql

# 检查连接
psql -h localhost -U serpent -d serpent_ai

# 检查防火墙
sudo ufw status
sudo ufw allow 5432/tcp  # PostgreSQL 默认端口
```

---

## 附录

### A. 环境变量完整列表

| 变量名 | 默认值 | 说明 |
|--------|---------|------|
| `HOST` | `0.0.0.0` | 服务器主机 |
| `PORT` | `8000` | 服务器端口 |
| `DEBUG` | `false` | 调试模式 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `OPENAI_API_KEY` | `None` | OpenAI API Key |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | OpenAI 自定义端点 |
| `ANTHROPIC_API_KEY` | `None` | Anthropic API Key |
| `ANTHROPIC_API_BASE` | `https://api.anthropic.com` | Anthropic 自定义端点 |
| `LLAMA_CPP_THREADS` | `4` | Llama.cpp CPU 线程数 |
| `LLAMA_CPP_GPU_LAYERS` | `0` | Llama.cpp GPU 加速层数 |
| `SECRET_KEY` | `your-secret-key-change-in-production` | 密钥（用于加密） |
| `JWT_SECRET` | `your-jwt-secret-here` | JWT 密钥 |
| `SQLITE_URL` | `sqlite+aiosqlite:///serpent_ai.db` | SQLite 数据库连接字符串 |
| `CHROMADB_PERSIST_DIR` | `./data/chroma` | ChromaDB 持久化目录 |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j 连接 URI |
| `NEO4J_PASSWORD` | `serpent_ai_2024` | Neo4j 密码 |
| `REDIS_HOST` | `localhost` | Redis 主机 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `REDIS_PASSWORD` | `None` | Redis 密码 |
| `CACHE_STRATEGY` | `two-tier` | 缓存策略（memory/redis/two-tier） |
| `CACHE_TTL` | `3600` | 默认缓存时间（秒） |
| `SANDBOX_MODE` | `docker` | 沙箱模式（subprocess/docker/gvisor） |
| `SANDBOX_TIMEOUT` | `30` | 工具执行超时（秒） |
| `MAX_UPLOAD_SIZE` | `100` | 最大上传文件大小（MB） |
| `ALLOWED_ORIGINS` | `http://localhost:8000` | CORS 允许的来源 |

### B. API 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页（API 文档） |
| `/health` | GET | 健康检查 |
| `/api/chat` | POST | 聊天端点 |
| `/api/models` | GET | 列出可用模型 |
| `/api/models/{model_name}/chat` | POST | 使用指定模型聊天 |
| `/api/tools` | GET | 列出可用工具 |
| `/api/memory/store` | POST | 存储记忆 |
| `/api/memory/retrieve` | GET | 检索记忆 |
| `/api/agent/task` | POST | 创建 Agent 任务 |
| `/api/workflow/create` | POST | 创建 workflow |
| `/api/voice/stt` | POST | 语音转文本 |
| `/api/voice/tts` | POST | 文本转语音 |
| `/docs` | GET | Swagger UI 文档 |
| `/redoc` | GET | ReDoc 文档 |
| `/openapi.json` | GET | OpenAPI 规范 |

### C. 性能调优建议

| 场景 | 建议 |
|------|------|
| 低延迟（实时聊天） | 使用 GPT-4o-mini 或本地模型；启用流式输出；启用缓存 |
| 高质量（内容生成） | 使用 GPT-4o 或 Claude 3 Opus；增加 max_tokens；禁用缓存 |
| 低成本（大规模调用） | 使用 GPT-4o-mini 或 Claude 3 Haiku；启用缓存；限制 max_tokens |
| 隐私保护（敏感数据） | 使用本地模型（Llama.cpp）；禁用日志记录；启用沙箱隔离 |
| 高并发（多用户） | 增加 Worker 数量；使用 Redis 缓存；使用负载均衡 |

### D. 参考资源

- **官方文档**: https://github.com/zhan1206/serpent-ai/docs
- **API 文档**: http://localhost:8000/docs
- **OpenAI API 文档**: https://platform.openai.com/docs
- **Anthropic API 文档**: https://docs.anthropic.com
- **Llama.cpp 文档**: https://github.com/ggerganov/llama.cpp
- **FastAPI 文档**: https://fastapi.tiangolo.com
- **Docker 文档**: https://docs.docker.com
- **Nginx 文档**: https://nginx.org/en/docs

---

**文档版本**: 1.0.0  
**更新日期**: 2026-05-23  
**维护者**: SerpentAI 团队
