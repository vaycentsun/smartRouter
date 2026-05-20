# Smart Router Docker 使用指南

本文档说明如何使用 Docker 和 Docker Compose 构建、运行 Smart Router 服务。

---

## 前提条件

- 安装 [Docker](https://docs.docker.com/get-docker/)（>= 20.10）
- 安装 [Docker Compose](https://docs.docker.com/compose/install/)（>= 2.0）
- 准备 Smart Router 配置文件（详见下文）

---

## 快速开始

### 1. 准备配置

在 `config/` 目录下放置三文件配置（也可放在其他位置）：

```
config/
├── providers.yaml   # Provider 与 API Key 配置（Key 通过 os.environ/xxx 引用）
├── models.yaml      # 模型能力声明
└── routing.yaml     # 路由策略配置
```

**示例配置**可参考 `config/examples/v3/`。

> **安全提示**：`providers.yaml` 中的 API Key 必须写成 `os.environ/KEY_NAME` 形式，不要写明文。实际密钥通过环境变量或 `.env` 文件传入容器。

---

### 方式一：从 Docker Hub 拉取（推荐）

如果你不需要修改源码，直接从 Docker Hub 拉取预构建镜像是最快的方式：

#### 使用 Docker Compose

修改 `docker-compose.yml`，将 `build` 部分注释掉，改用 `image`：

```yaml
services:
  smart-router:
    # build:
    #   context: .
    #   dockerfile: Dockerfile
    image: your-dockerhub-username/smartrouter:latest
    container_name: smart-router
    # ... 其余配置不变
```

然后启动：

```bash
export SMART_ROUTER_MASTER_KEY="your-strong-master-key"
docker-compose up -d
```

#### 使用纯 Docker 命令

```bash
# 拉取并运行（无需本地构建）
docker run -d \
  --name smart-router \
  -p 4000:4000 \
  -p 8080:8080 \
  -e SMART_ROUTER_MASTER_KEY="your-strong-master-key" \
  -e OPENAI_API_KEY="sk-..." \
  -v "$(pwd)/config:/app/config:ro" \
  your-dockerhub-username/smartrouter:latest
```

> **注意**：需要同时暴露 `4000`（Proxy API）和 `8080`（Dashboard）两个端口。

### 方式二：本地构建（适合自定义修改）

如果你想修改源码或前端，可以在本地构建镜像：

#### 使用 Docker Compose

```bash
# 设置主密钥（必须）
export SMART_ROUTER_MASTER_KEY="your-strong-master-key"

# 可选：设置各 Provider API Key
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# 启动服务（会自动构建）
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### 使用纯 Docker 命令

```bash
# 构建镜像
docker build -t smartrouter:latest .

# 运行容器（同时暴露 4000 和 8080 端口）
docker run -d \
  --name smart-router \
  -p 4000:4000 \
  -p 8080:8080 \
  -e SMART_ROUTER_MASTER_KEY="your-strong-master-key" \
  -e OPENAI_API_KEY="sk-..." \
  -v "$(pwd)/config:/app/config:ro" \
  smartrouter:latest

# 查看日志
docker logs -f smart-router

# 停止并删除
docker stop smart-router && docker rm smart-router
```

服务启动后：
- **Proxy API**：`http://localhost:4000`（OpenAI 兼容接口）
- **Dashboard**：`http://localhost:8080`（Web 管理界面）

---

## 配置说明

### 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `SMART_ROUTER_MASTER_KEY` | **是** | 服务主密钥，用于 API 请求认证 |
| `SMART_ROUTER_HOST` | 否 | 监听地址，容器内默认 `0.0.0.0` |
| `SMART_ROUTER_PORT` | 否 | 监听端口，默认 `4000` |
| `OPENAI_API_KEY` | 按需 | OpenAI Provider 密钥（示例） |
| `ANTHROPIC_API_KEY` | 按需 | Anthropic Provider 密钥（示例） |
| `ALIYUN_API_KEY` | 按需 | 阿里云 Provider 密钥（示例） |
| `ZHIPU_API_KEY` | 按需 | 智谱 Provider 密钥（示例） |

> 具体需要哪些 Provider 环境变量，取决于你的 `providers.yaml` 配置。

### 使用 .env 文件（推荐）

将环境变量写入 `.env` 文件：

```bash
# .env
SMART_ROUTER_MASTER_KEY=your-strong-master-key
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

然后启动：

```bash
docker-compose --env-file .env up -d
```

---

## 镜像标签说明

Docker Hub 镜像使用以下标签策略，方便你根据需求选择：

| 标签 | 说明 | 适用场景 |
|------|------|----------|
| `latest` | 始终指向最新的稳定版本 | 开发测试、快速体验 |
| `v1.1.8` | 具体完整版本 | 生产环境，确保版本固定 |
| `v1.1` | 次版本号，自动包含该版本的补丁更新 | 希望自动获取 bugfix |
| `v1` | 主版本号，自动包含该主版本的所有更新 | 希望自动获取新功能 |
| `main-abc1234` | main 分支的某次提交 | 体验最新开发版本 |

**推荐生产使用**：`your-dockerhub-username/smartrouter:v1.1.8`（替换为实际版本号）

```bash
# 拉取指定版本
docker pull your-dockerhub-username/smartrouter:v1.1.8

# 使用指定版本运行
docker run -d \
  --name smart-router \
  -p 4000:4000 \
  -p 8080:8080 \
  -e SMART_ROUTER_MASTER_KEY="your-strong-master-key" \
  -v "$(pwd)/config:/app/config:ro" \
  your-dockerhub-username/smartrouter:v1.1.8
```

---

## 镜像构建说明

Dockerfile 采用**多阶段构建**，最终镜像体积较小：

1. **阶段 1（frontend-builder）**：基于 `node:20-slim`，安装前端依赖并构建，产物输出到 `frontend/dist/`。
2. **阶段 2（python-builder）**：基于 `python:3.11-slim`，将前端产物复制到 `core/smart_router/web/static/`，然后使用 `hatchling` 构建 Python wheel。
3. **阶段 3（runtime）**：基于 `python:3.11-slim`，仅安装构建好的 wheel，不包含 Node.js 和构建工具，镜像更干净。

镜像支持 **linux/amd64** 和 **linux/arm64** 双架构。

---

## 故障排查

| 现象 | 排查方法 |
|------|----------|
| 容器无法启动 | `docker-compose logs` 查看是否缺少 `SMART_ROUTER_MASTER_KEY` 或配置文件错误 |
| Web 界面 404 | 检查前端是否已正确构建并嵌入；可尝试重新执行 `docker build` |
| 模型返回 401/403 | 确认对应 Provider 的环境变量已正确传入容器 |
| 端口冲突 | 修改 `docker-compose.yml` 中的端口映射，如 `"4001:4000"` |
| 配置不生效 | 确认 `config/` 目录已正确挂载，且文件路径为 `/app/config/*.yaml` |

---

## 相关文档

- [CLI 使用指南](../docs/GUIDE.md)
- [路由策略指南](../docs/ROUTING_GUIDE.md)
- [项目根目录 AGENTS.md](../AGENTS.md)
