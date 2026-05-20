# Smart Router Docker 镜像
# 多阶段构建：先构建前端，再构建 Python 包

# =================== 阶段 1：构建前端 ===================
FROM node:20-slim AS frontend-builder

WORKDIR /build/frontend

# 复制前端依赖文件
COPY frontend/package*.json ./
RUN npm ci

# 复制前端源码并构建
COPY frontend/ ./
RUN npm run build

# =================== 阶段 2：构建 Python 包 ===================
FROM python:3.11-slim AS python-builder

WORKDIR /build

# 安装构建依赖
RUN pip install --no-cache-dir build hatchling

# 复制项目文件
COPY pyproject.toml README.md LICENSE ./
COPY core/ ./core/
COPY config/ ./config/
COPY script/ ./script/
COPY docs/ ./docs/

# 从前端构建阶段复制产物到 Python 包的 static 目录
RUN mkdir -p core/smart_router/web/static
COPY --from=frontend-builder /build/frontend/dist/ core/smart_router/web/static/

# 构建 wheel
RUN python -m build --wheel

# =================== 阶段 3：运行环境 ===================
FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖（可选，如需在容器内编译某些包）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 wheel 并安装
COPY --from=python-builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# 创建配置目录
RUN mkdir -p /app/config

# 暴露服务端口
EXPOSE 4000

# 设置环境变量
ENV SMART_ROUTER_HOST=0.0.0.0
ENV SMART_ROUTER_PORT=4000
ENV PYTHONUNBUFFERED=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:4000/api/health')" || exit 1

# 入口命令（前台运行）
ENTRYPOINT ["smart-router"]
CMD ["start", "--foreground", "--config", "/app/config"]
