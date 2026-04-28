# Smart Router — AGENTS.md

> 本文档供 AI 编码助手阅读。此为**全局导航入口**，技术细节请查看子目录 AGENTS.md。
> 项目语言：中文（注释与文档使用中文，代码标识符使用英文）。
> AI 对话语言：中文

**版本**: 1.1.0 · **Python**: >= 3.9 · **构建后端**: hatchling · **PyPI**: `smartrouter`

---

## 项目结构

| 目录 | 技术栈 | 职责 | 详细文档 |
|------|--------|------|----------|
| `core/` | Python 3.9+ | 路由引擎、CLI、网关服务 | [core/AGENTS.md](./core/AGENTS.md) |
| `frontend/` | Vite + TypeScript | Web 管理界面 | [frontend/AGENTS.md](./frontend/AGENTS.md) |
| `docs/` | Markdown | 用户指南与路由策略文档 | — |
| `config/examples/` | YAML | 三文件配置示例 | — |

---

## 全局开发命令（跨模块）

> 所有命令均在项目根目录执行。

```bash
# 安装全部依赖（Python + Node）
make install          # Python 开发安装
cd frontend && npm ci # 前端依赖（或 make dev-web 自动处理）

# 开发模式
make dev-core         # Python 后端（含热重载）
make dev-web          # 前端 Vite 开发服务器

# 构建（前后端一体）
make build            # 先 build-web，再 Python wheel/sdist
make build-web        # 前端构建 → 嵌入 core/smart_router/web/static/
make test             # 运行全部测试（当前仅 Python）
make clean            # 清理 frontend/dist、web/static、dist/
```

---

## 关键跨模块耦合

- **前端产物嵌入后端**：`make build-web` 将 `frontend/dist/` 复制到 `core/smart_router/web/static/`，作为网关的 Web 管理界面静态资源。
- **版本单源**：仅修改 `pyproject.toml` 的 `version`，Python 通过 `importlib.metadata` 读取。
- **CI**：`.github/workflows/publish.yml` 在 `push tags v*` 时自动发布 PyPI 并更新 Homebrew Formula。

---

## 通用规范

- **Git 分支**：`main` 为主干，功能分支开发。
- **提交语言**：中文或英文均可，但需清晰描述变更意图。
- **安全约束**：
  - 启动服务必须设置 `SMART_ROUTER_MASTER_KEY`
  - 默认只绑定 `127.0.0.1`
  - `providers.yaml` 中 API Key 禁止明文，必须通过 `os.environ/KEY_NAME` 引用

---

## 故障排查（跨模块）

| 现象 | 定位 |
|------|------|
| Web 界面 404 | 检查 `make build-web` 是否执行；确认 `core/smart_router/web/static/` 存在产物 |
| 端口冲突 | 后端默认 `4000`，前端 Vite 默认 `5173`（查看各自 AGENTS.md 修改方式） |

---

## 相关文档索引

| 文档 | 内容 |
|------|------|
| `docs/GUIDE.md` | 完整 CLI 命令、配置详解、客户端集成 |
| `docs/ROUTING_GUIDE.md` | 路由策略编写指南 |
| `config/examples/v3/` | 三文件配置示例（提交到 Git） |
| `specs/active/` | 活跃技术规格（V3 重构、路由架构修复） |
