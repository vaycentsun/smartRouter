# Smart Router 源码目录划分指南

> 本文档介绍 `src/smart_router/` 的目录组织原则与模块职责划分。

---

## 目录总览

```
src/smart_router/
├── __init__.py                 # 包入口，版本号
├── cli.py                      # CLI 门面：Typer 命令定义
│
├── gateway/                    # 网关层：服务生命周期管理
│   ├── __init__.py
│   ├── server.py               # FastAPI 前台服务 + 智能路由中间件
│   ├── server_main.py          # 后台服务入口（argparse）
│   └── daemon.py               # PID 文件、进程启动/停止/状态/日志
│
├── router/                     # 路由层：核心路由插件
│   ├── __init__.py
│   ├── plugin.py               # SmartRouter V3 主插件（继承 LiteLLM Router）
│   └── plugin_v3_adapter.py    # V3 配置适配器（备用路径）
│
├── classifier/                 # 业务层：任务分类器
│   ├── __init__.py
│   ├── task_classifier.py
│   ├── difficulty_classifier.py
│   └── types.py
│
├── selector/                   # 业务层：模型选择器
│   ├── __init__.py
│   ├── model_selector.py       # v2 选择器
│   ├── v3_selector.py          # V3 选择器（9 种策略）
│   └── strategies.py           # 兼容重导出
│
├── config/                     # 业务层：配置系统
│   ├── __init__.py
│   ├── schema.py               # Pydantic 模型
│   ├── loader.py               # YAML 加载与验证
│   ├── v3_schema.py            # 向后兼容别名
│   └── v3_loader.py            # 向后兼容别名
│
├── utils/                      # 工具层：通用工具函数
│   ├── __init__.py
│   ├── markers.py              # 阶段标记解析器
│   └── token_counter.py        # 轻量级 token 估算
│
├── templates/                  # 资源层：默认配置模板
│   ├── providers.yaml
│   ├── models.yaml
│   └── routing.yaml
│
├── assets/                     # 资源层：静态资源
│   └── coffee_qr.png
│
└── misc/                       # 杂项层：非核心功能
    ├── __init__.py
    └── coffee_qr.py            # 赞助二维码（运营功能）
```

---

## 分层设计原则

### 1. 门面层（Root: `cli.py`）

**保留在根目录的唯一理由**：CLI 是整个包的单一入口。外部（如 `pyproject.toml` 的 console scripts）通过 `smart_router.cli:app` 直接引用，放在根级最符合 Python 包惯例。

- 聚合所有用户命令：`init`、`start`、`stop`、`dry-run`、`doctor`、`list`、`coffee`
- 负责参数解析、用户输出（Rich）、命令分发
- 不承载业务逻辑，只调用下层模块

### 2. 网关层（`gateway/`）

**职责边界**：与"进程/网络生命周期"相关的一切。

| 文件 | 职责 |
|------|------|
| `server.py` | 前台服务启动：加载配置 → 初始化 SmartRouter → 启动 uvicorn → 注册 FastAPI 中间件 |
| `server_main.py` | 后台进程入口：接收 `--config` 参数，调用 `start_server()` |
| `daemon.py` | 后台进程管理：PID 文件读写、端口占用检测、`subprocess.Popen` 启动、`SIGTERM/SIGKILL` 停止、日志查看 |

**为什么聚合在一起**：`daemon.start_daemon()` 最终执行 `python -m smart_router.gateway.server_main`，`server_main` 调用 `server.start_server()`，三者是同一生命周期的上下游，不应散落在根目录。

### 3. 路由层（`router/`）

**职责边界**：在 LiteLLM 原生路由前注入"智能选择"逻辑。

| 文件 | 职责 |
|------|------|
| `plugin.py` | `SmartRouter` 类：继承 `litellm.router.Router`，重写 `get_available_deployment()`，整合分类器 + 选择器 + 上下文过滤 |
| `plugin_v3_adapter.py` | `SmartRouterV3Adapter` 类：备用适配路径，直接使用 V3 三文件配置初始化 |

**为什么单独成层**：路由决策是项目的核心差异化能力，与"服务如何启动"（gateway）属于不同抽象层次。将两者分离后，`gateway/server.py` 可以无歧义地 `from ..router.plugin import SmartRouter`。

### 4. 业务层（`classifier/`、`selector/`、`config/`）

这三个目录在重构前已经存在，职责清晰，无需调整：

- **`classifier/`**：将用户输入文本分类为 `task_type` + `difficulty`
- **`selector/`**：根据分类结果和策略从模型池中选择最优模型
- **`config/`**：Pydantic 模型定义、YAML 加载、运行时配置验证

### 5. 工具层（`utils/`）

与业务无关的通用工具：

- `markers.py`：解析 `[stage:xxx] [difficulty:xxx]` 标记
- `token_counter.py`：基于字符加权的轻量级 token 估算

### 6. 资源层（`templates/`、`assets/`）

- `templates/`：`smart-router init` 命令复制的默认 YAML 配置
- `assets/`：静态图片等资源

### 7. 杂项层（`misc/`）

**设计意图**：隔离与核心功能完全无关的代码。

- `coffee_qr.py`：赞助二维码的显示、复制、生成逻辑
- 放在根目录会污染核心代码的视觉焦点；放在 `utils/` 又不符合"工具函数"的语义
- 单独 `misc/` 明确表示：此处代码不参与主流程，可安全忽略

---

## 导入路径规范

### 相对导入层级

```python
# gateway/server.py 引用 router 层的插件
from ..router.plugin import SmartRouter

# router/plugin.py 引用同包其他子模块
from ..classifier import TaskClassifier
from ..selector.v3_selector import V3ModelSelector
from ..config.schema import Config

# cli.py 引用所有子模块（根级 → 子模块，用单点）
from .gateway.daemon import start_daemon
from .router.plugin import SmartRouter
from .misc.coffee_qr import get_qr_code_path
```

### 绝对导入（测试文件优先）

```python
# 测试文件统一使用绝对导入，便于独立运行
from smart_router.gateway.server import start_server
from smart_router.router.plugin import SmartRouter
from smart_router.misc.coffee_qr import QR_CODE_PATH
```

---

## 扩展指南

### 添加新的服务启动方式

如果未来需要支持 Docker、Systemd 或其他启动方式：

1. 在 `gateway/` 下新增模块（如 `docker_entry.py`、`systemd.py`）
2. 在 `cli.py` 中添加命令，从 `gateway.xxx` 导入并调用

### 添加新的路由策略

1. 在 `selector/v3_selector.py` 的 `V3ModelSelector` 中添加 `_select_by_xxx()` 方法
2. 在 `router/plugin.py` 的 `select_model()` 中确保策略名可被解析

### 添加运营/工具功能

1. 如果与核心流程无关，优先放入 `misc/`
2. 如果涉及通用工具函数，放入 `utils/`

---

## 重构历史

- **2026-04-23**：将原本平铺在 `src/smart_router/` 根目录的 `server.py`、`server_main.py`、`daemon.py`、`plugin.py`、`plugin_v3_adapter.py`、`coffee_qr.py` 按职责归入 `gateway/`、`router/`、`misc/` 三个子模块。
- **影响范围**：仅内部导入路径调整，无 API/行为变更。
- **验证方式**：全量 261 个单元测试 + 集成测试通过。
