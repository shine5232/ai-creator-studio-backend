# AI Creator Studio Server

AI 短视频创作平台 - 后端服务，基于 FastAPI + SQLAlchemy + Celery。

## 技术栈

- **FastAPI** — 异步 Web 框架
- **SQLAlchemy** (async + aiosqlite) — ORM & 数据库
- **Celery + Redis** — 异步任务队列
- **Pydantic v2** — 数据校验
- **SQLite** — 数据库（开发环境）

## 环境要求

- Python 3.11+
- Redis（Celery 消息队列）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example`（如有）或直接编辑 `.env`：

```env
# 数据库
DATABASE_URL=sqlite+aiosqlite:///./openclaw.db

# JWT
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Redis
REDIS_URL=redis://localhost:6379/0

# AI 服务（按需配置）
ZHIPU_API_KEY=
DOUBAO_API_KEY=
```

### 3. 启动服务

按以下顺序依次启动（每个命令在独立终端中执行）：

#### 启动 Redis

```bash
redis-server
```

#### 启动后端 API（端口 8090）

```bash
python run.py
```

或使用 uvicorn 直接启动：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
```

#### 启动 Celery Worker（异步任务，如 AI 生成）

```bash
python worker.py
```

### 4. 验证服务

```bash
curl http://localhost:8090/api/v1/health
```

## API 文档

启动后访问：

- Swagger UI: `http://localhost:8090/docs`
- ReDoc: `http://localhost:8090/redoc`

## 项目结构

```
openclaw-server/
├── app/
│   ├── api/v1/           # 路由（auth, projects, scripts, knowledge 等）
│   ├── core/             # 配置、安全、数据库
│   ├── models/           # SQLAlchemy 模型
│   ├── schemas/          # Pydantic 请求/响应模型
│   ├── services/         # 业务逻辑层
│   ├── worker/           # Celery 任务
│   └── main.py           # 应用入口
├── run.py                # 启动脚本（端口 8090）
├── requirements.txt
└── .env
```

## AI 服务提供商

| 提供商 | 服务 | 说明 |
|--------|------|------|
| 智谱 GLM | 文本生成 | 脚本生成、分镜描述 |
| 豆包 Seedream | 文生图 | 分镜图片生成 |
| 通义万相 | 图生视频 | 分镜转视频 |
| 豆包 Seedance | 视频生成 | 视频创作 |
