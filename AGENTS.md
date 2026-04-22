# Smart Router — AGENTS.md

> 本文档供 AI 编码助手阅读，包含项目架构、开发约定和关键信息。
> 项目语言：中文（注释与文档使用中文，代码标识符使用英文）。

---

## 项目概述

Smart Router（智能模型路由网关，PyPI 包名 `smart-router`）是一个基于 LiteLLM Proxy 的本地 CLI 工具，对外暴露统一的 OpenAI API 接口，根据任务类型、难度和阶段标记自动将请求路由到最合适的底层大模型。

**版本**: 1.0.2  
**Python 要求**: >= 3.9  
**许可证**: MIT  
**构建后端**: hatchling

### 核心能力

- **统一入口**：一个 API Key 管理多个服务商（OpenAI、Anthropic、Moonshot、Qwen、Zhipu、MiniMax、LM Studio 等）
- **智能路由**：自动识别任务类型（coding/code_review/writing/creative/reasoning/analysis/explanation/translation/chat/brainstorming）并选择最优模型
- **阶段标记**：支持 `[stage:code_review] [difficulty:hard]` 等显式标记控制路由
- **多种策略**：auto/quality/cost/balanced/reasoning/creative/vision/long_context/latest 九种路由策略
- **自动 Fallback**：模型失败时按 quality 相似度自动升级重试，支持 provider 隔离
- **上下文感知**：根据输入 token 估算过滤不满足上下文窗口的模型

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 语言 | Python 3.9+ |
| CLI 框架 | Typer（基于 Click） |
| 代理层 | LiteLLM（MIT License） |
| 配置验证 | Pydantic 2.x |
| 终端输出 | Rich |
| 配置格式 | YAML |
| 测试 | pytest + pytest-asyncio |
| HTTP 服务 | FastAPI + uvicorn |
| 构建 | hatchling |

---

## 项目结构

```
smartRouter/
├── pyproject.toml                  # 项目配置与依赖
├── README.md                       # 英文 README
├── CHANGELOG.md                    # 变更日志
├── AGENTS.md                       # 本文档
│
├── src/smart_router/               # 核心源码包
│   ├── __init__.py                 # 版本号: 1.0.2
│   ├── cli.py                      # CLI 入口（Typer），所有命令定义
│   ├── server.py                   # LiteLLM Proxy 封装和前台服务启动
│   ├── server_main.py              # 后台服务入口（argparse）
│   ├── daemon.py                   # 后台进程管理（PID 文件、启动/停止/状态/日志）
│   ├── plugin.py                   # SmartRouter 核心插件（继承 LiteLLM Router，使用 V3 配置）
│   ├── plugin_v3_adapter.py        # V3 配置适配器（备用，当前主流程使用 plugin.py）
│   ├── coffee_qr.py                # 赞助二维码（`smr coffee` 命令）
│   │
│   ├── config/                     # 配置系统
│   │   ├── schema.py               # Pydantic 配置模型（ProviderConfig/ModelConfig/RoutingConfig/Config）
│   │   ├── loader.py               # ConfigLoader：从三文件加载 YAML 并验证
│   │   ├── v3_schema.py            # 向后兼容别名（重导出 schema.py）
│   │   └── v3_loader.py            # 向后兼容别名（重导出 loader.py）
│   │
│   ├── classifier/                 # 任务分类器
│   │   ├── __init__.py             # 导出 TaskClassifier, ClassificationResult
│   │   ├── task_classifier.py      # TaskClassifier（规则引擎 + TaskTypeClassifier）
│   │   ├── difficulty_classifier.py # DifficultyClassifier（基于规则动态评估难度）
│   │   └── types.py                # ClassificationResult 数据类
│   │
│   ├── selector/                   # 模型选择器
│   │   ├── __init__.py             # 导出 ModelSelector
│   │   ├── model_selector.py       # v2 模型选择器（priority/quality/cost 策略）
│   │   ├── strategies.py           # 兼容模块（重导出 model_selector）
│   │   └── v3_selector.py          # V3ModelSelector（9 种策略 + 多维度能力）
│   │
│   ├── utils/                      # 工具函数
│   │   ├── __init__.py
│   │   ├── markers.py              # 阶段标记解析器 `[stage:xxx] [difficulty:xxx]`
│   │   └── token_counter.py        # 轻量级 token 估算（中英文字符加权）
│   │
│   ├── templates/                  # `smart-router init` 生成的默认配置模板
│   │   ├── providers.yaml
│   │   ├── models.yaml
│   │   └── routing.yaml
│   │
│   └── assets/
│       └── coffee_qr.png           # 赞助二维码图片
│
├── tests/                          # 单元测试与集成测试
│   ├── test_classifier.py
│   ├── test_cli.py
│   ├── test_cli_list.py
│   ├── test_config_schema.py
│   ├── test_context_aware.py
│   ├── test_integration.py         # V3 集成测试（标记解析 → 分类 → 选择）
│   ├── test_markers.py
│   ├── test_plugin.py
│   ├── test_plugin_v3_adapter.py
│   ├── test_v3_integration.py      # V3 端到端场景测试
│   ├── test_v3_loader.py
│   ├── test_v3_schema.py
│   └── test_v3_selector.py
│
├── config/examples/                # 配置示例（提交到 Git）
│   ├── v3/
│   │   ├── providers.yaml          # 服务商配置示例
│   │   ├── models.yaml             # 模型能力声明示例（覆盖主流国内外模型）
│   │   └── routing.yaml            # 路由策略示例（10 任务 × 4 难度 × 9 策略）
│   ├── minimal.yaml                # V2 遗留最小配置
│   └── multi-provider.yaml         # V2 遗留多服务商配置
│
├── script/                         # 安装/卸载/验证脚本
│   ├── install.sh                  # 本地开发一键安装（pip install -e）
│   ├── install-remote.sh           # 远程一键安装（PyPI + curl）
│   ├── download-config.py          # curl 下载配置脚本
│   ├── uninstall.sh                # 一键卸载
│   ├── verify.py                   # 快速验证脚本
│   └── make-portable.sh            # 构建便携版
│
├── docs/                           # 项目文档
│   ├── GUIDE.md                    # 完整使用指南（命令速查表、客户端集成）
│   ├── ROUTING_GUIDE.md            # 路由策略详解
│   ├── FILE_ORGANIZATION.md        # 文件组织规范
│   ├── ARCHITECTURE_V2.md          # V2 架构文档
│   ├── README.zh.md                # 中文 README
│   └── ...
│
├── specs/                          # 技术规格文档
│   ├── active/                     # 活跃规格
│   │   ├── 2026-04-19--config-v3-refactor.md
│   │   ├── 2026-04-21--routing-architecture-fix.md
│   │   └── plans/                  # 实现计划
│   └── archived/                   # 已归档规格
│
├── skills/sw-superpower/           # AI 编码 Agent 软件工程技能集
│   ├── sw-brainstorming/           # 头脑风暴与需求分析
│   ├── sw-writing-specs/           # 编写实现计划
│   ├── sw-subagent-development/    # 子 Agent 驱动开发
│   ├── sw-test-driven-dev/         # 测试驱动开发（RED-GREEN-REFACTOR）
│   ├── sw-code-review/             # 两阶段代码审查
│   ├── sw-systematic-debugging/    # 系统化调试
│   ├── sw-verification-before-completion/ # 完成前验证
│   ├── sw-finishing-branch/        # 分支收尾
│   └── ...
│
├── homebrew/
│   └── smart-router.rb             # Homebrew Formula
│
└── .github/workflows/
    └── publish.yml                 # GitHub Actions: 打 tag 时自动构建并发布到 PyPI
```

---

## V3 三文件解耦配置架构

运行时配置目录默认位于 `~/.smart-router/`（可通过 `--config` 指定）。

### 文件职责

| 文件 | 职责 | 是否含敏感信息 |
|------|------|--------------|
| `providers.yaml` | 服务商连接信息（api_base, api_key, timeout） | API Key 通过 `os.environ/KEY_NAME` 引用，不含明文 |
| `models.yaml` | 模型能力声明（quality/cost/context/reasoning/creative/vision 等）、支持任务、难度等级 | 否 |
| `routing.yaml` | 任务定义与 capability_weights、难度等级定义、策略定义、fallback 配置 | 否 |

### 关键设计

- **Provider 隔离**：修改 API Key 只需改 `providers.yaml`，无需动模型列表
- **动态能力评分**：`routing.yaml` 中每个任务配置 `capability_weights`（如 code_review: quality 0.7 + cost 0.3），`auto` 策略按加权评分选模型
- **Fallback 自动推导**：`Config._derive_fallback_chains()` 基于 quality 差异阈值（默认 2）自动计算 fallback 链，支持 `provider_isolation` 模式
- **可用模型过滤**：`Config.get_available_models()` 只返回 API Key 已配置的 provider 所对应的模型，未配置 provider 的模型自动灰度

---

## 核心架构流程

```
用户请求 (OpenAI API 格式, model="auto")
    ↓
LiteLLM Proxy (FastAPI, 端口 4000)
    ↓
SmartRouter Middleware (server.py)
    ├──→ parse_markers(messages)          # 解析 [stage:xxx] [difficulty:xxx]
    │    ├── 命中 stage? → 直接使用
    │    └── 未命中 → 继续
    │
    ├──→ TaskClassifier.classify()        # 规则引擎 + 动态难度评估
    │    ├── TaskTypeClassifier: 关键词/正则匹配
    │    └── DifficultyClassifier: 基于文本长度、关键词、对话轮数
    │
    ├──→ ModelSelector.select()           # 根据策略选择模型
    │    ├── 筛选: task_type ∈ supported_tasks, difficulty ∈ difficulty_support
    │    ├── 筛选: required_context <= model.context
    │    └── 排序: auto(加权评分) / quality / cost / reasoning / creative / ...
    │
    └──→ 修改请求体 model 字段 → 添加响应头 X-Smart-Router-Model
         ↓
    LiteLLM 父类路由到目标模型
         ↓
    目标模型 Provider
```

---

## 关键组件说明

### 1. CLI (`cli.py`)

主要命令：
- `smart-router init [--output DIR] [--force]` — 生成默认三文件配置
- `smart-router start [--foreground] [--config DIR]` — 后台/前台启动服务
- `smart-router stop / restart / status / logs` — 服务生命周期管理
- `smart-router dry-run "prompt" [--strategy auto|quality|cost]` — 测试路由决策（不调用模型）
- `smart-router doctor [--config DIR]` — 健康检查（Python 版本、配置加载、配置验证、服务状态）
- `smart-router list [--config DIR]` — 列出 providers 和模型（含 API Key 可用性状态）
- `smart-router version [--short]` — 版本信息
- `smart-router coffee [--open] [--ascii]` — 赞助二维码

> 等价短命令：`smr`（如 `smr start`、`smr doctor`）

### 2. SmartRouter 插件 (`plugin.py`)

继承 `litellm.router.Router`，重写 `get_available_deployment()` 注入智能路由逻辑。

- `select_model()`：统一路由决策入口，解析 `model_hint` 中的 `stage:` 和 `strategy-` 前缀
- `_get_classification()`：优先使用 stage marker，否则走 TaskClassifier
- 上下文过滤：通过 `estimate_messages_tokens()` 估算输入 token，+4000 预留输出，过滤不满足 context 窗口的模型

### 3. 配置加载 (`config/loader.py` + `config/schema.py`)

- `ConfigLoader(config_dir)`：从目录加载三文件 YAML
- `Config`（Pydantic）：聚合根，含运行时 fallback 链预计算、provider 可用性检查、LiteLLM 参数组装
- 校验规则：`capability_weights` 总和必须为 1.0（±0.01）；models 引用的 provider 必须存在

### 4. 任务分类器 (`classifier/`)

- **TaskTypeClassifier**：基于关键词/正则匹配（从 V3 routing.tasks 动态构建关键词）
- **DifficultyClassifier**：基于规则列表（condition 支持 `keyword:xxx|yyy`、`length > N`、`length < N`），按 priority 排序
- **TaskClassifier**：组合以上两者，支持多轮对话难度提升（user 消息 > 3 轮时难度升一档）

### 5. 模型选择器 (`selector/`)

- **ModelSelector** (`model_selector.py`)：v2 选择器，支持 auto/priority/quality/cost 策略，含上下文过滤和默认模型回退
- **V3ModelSelector** (`v3_selector.py`)：支持 9 种策略（auto/quality/cost/reasoning/creative/vision/long_context/latest/balanced），按 capability 维度排序

> 当前主流程（`plugin.py`、`cli.py dry-run`）实际使用的是 `ModelSelector`，但从 V3 Config 动态构建 `model_pool`。

---

## 构建与测试命令

```bash
# 开发安装（含测试依赖）
pip install -e ".[dev]"

# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_integration.py -v
pytest tests/test_v3_selector.py -v

# 构建分发包
python -m build

# 检查包
twine check dist/*

# 快速健康检查
smart-router doctor
# 或
smr doctor
```

---

## 代码风格指南

1. **类型注解**：所有函数参数和返回值使用类型注解
2. **文档字符串**：类和重要函数使用中文文档字符串，说明职责、参数、返回值
3. **命名规范**：
   - 类名: PascalCase
   - 函数/变量: snake_case
   - 常量: UPPER_SNAKE_CASE
   - 模块名: snake_case
4. **字符串与注释**：中文项目，代码注释和文档字符串使用中文；代码标识符使用英文
5. **导入顺序**：stdlib → third-party → local
6. **错误处理**：使用 `try/except` 捕获具体异常，CLI 中通过 Rich 输出友好的错误信息
7. **向后兼容**：重大重构时保留兼容别名模块（如 `v3_schema.py`、`v3_loader.py` 重导出）

---

## 测试策略

1. **单元测试**：每个模块对应 `tests/test_*.py`
2. **测试命名**：`test_功能_场景` 或 `test_类名_方法名`
3. **Fixtures**：使用 pytest fixtures 创建临时配置目录和内存中的 `Config` 对象
4. **集成测试**：`test_integration.py`、`test_v3_integration.py` 测试完整流程（加载 → 分类 → 选择 → LiteLLM 参数生成）
5. **环境隔离**：测试中通过 `monkeypatch.setenv()` 设置虚拟 API Key，避免依赖真实环境变量

---

## CI/CD 与发布

- **GitHub Actions**（`.github/workflows/publish.yml`）：
  - 触发条件：`push tags v*` 或手动 `workflow_dispatch`
  - 流程：build → check → upload artifact → publish to PyPI（使用 trusted publishing）→ create GitHub Release
- **PyPI 包名**: `smart-router`
- **版本管理**：`pyproject.toml` 和 `src/smart_router/__init__.py` 以及 `cli.py` 中的 `__version__` 需同步更新

---

## 安全考虑

- **API Key 只通过环境变量引用**：配置文件中使用 `os.environ/KEY_NAME` 格式，不出现明文 Key；`schema.py` 和 `loader.py` 在运行时解析为实际值
- **Master Key 强制要求**：启动服务时必须设置 `SMART_ROUTER_MASTER_KEY` 环境变量，不设默认值，避免未授权访问
- **默认只绑定 127.0.0.1**：可通过 `SMART_ROUTER_HOST`/`SMART_ROUTER_PORT` 环境变量修改
- **临时配置文件安全**：`server.py` 将 LiteLLM 配置写入临时 JSON 文件，初始化后立即 `os.unlink()` 删除
- **不收集遥测数据**

---

## 开发工作流约定（skills/sw-superpower）

本项目内嵌 **sw-superpower** 技能集，定义了完整的软件开发工作流。AI 编码 Agent 修改代码时应遵循：

| Skill | 用途 | 触发条件 |
|-------|------|----------|
| **sw-brainstorming** | 头脑风暴与需求分析 | 开始新功能开发 |
| **sw-writing-specs** | 创建详细的实现计划 | 设计已批准 |
| **sw-subagent-development** | 使用子 Agent 执行计划 | 有实现计划 |
| **sw-test-driven-dev** | 强制 RED-GREEN-REFACTOR | 实现任何功能或修复 Bug |
| **sw-code-review** | 两阶段代码审查 | 完成任务后 |
| **sw-systematic-debugging** | 系统化 Bug 调查 | 发现 Bug |
| **sw-verification-before-completion** | 标记完成前验证 | 准备标记完成 |
| **sw-finishing-branch** | 验证、决策、清理分支 | 所有任务完成 |

### 铁律

1. **所有代码修改必须通过 sw-test-driven-dev**: RED → GREEN → REFACTOR
2. **新功能必须先 sw-brainstorming**: 产出设计文档到 `specs/active/`
3. **任务完成后必须 sw-code-review**: 两阶段审查后才能标记完成
4. **完成前必须 sw-verification-before-completion**: 验证测试、文档、规范一致性

---

## 故障排查速查

| 现象 | 排查步骤 |
|------|----------|
| 服务无法启动 | `lsof -i :4000` 检查端口占用；`smart-router logs` 查看日志；`smart-router start --foreground` 前台调试 |
| 配置错误 | `smart-router doctor` 查看详细错误；检查 `~/.smart-router/` 下三文件是否存在且 YAML 语法正确 |
| 路由不生效 | `smart-router dry-run "提示文本"` 测试决策链路；检查模型是否因 provider API Key 缺失被过滤 |
| 后台进程残留 | 手动删除 `~/.smart-router/smart-router.pid`；`ps aux | grep smart_router` 查找后 kill |
| 模型返回 401/403 | 检查对应 provider 的环境变量是否已设置；`smart-router list` 查看 Auth 列状态 |

---

## 扩展指南

### 添加新的路由策略

在 `src/smart_router/selector/v3_selector.py` 的 `V3ModelSelector` 类中添加 `_select_by_xxx()` 方法，并在 `select()` 中注册分支。

### 添加新的分类规则

在 `src/smart_router/classifier/task_classifier.py` 的 `TaskClassifier` 中，`rules` 参数来自 V3 `routing.yaml` 的动态构建。如需静态规则，直接修改 `DEFAULT_DIFFICULTY_RULES`。

### 支持新的服务商

LiteLLM 原生支持 100+ 服务商。只需在 `config/examples/v3/providers.yaml` 和 `models.yaml` 中按 LiteLLM 格式添加即可（`litellm_model: openai/xxx` 或 `anthropic/xxx` 等）。

---

## 相关文档索引

| 文档 | 内容 |
|------|------|
| `docs/GUIDE.md` | 完整 CLI 命令、配置详解、客户端集成（Python/JS/Cursor/Claude Code） |
| `docs/ROUTING_GUIDE.md` | 路由策略编写指南、stage_routing 详解、classification_rules 最佳实践 |
| `docs/FILE_ORGANIZATION.md` | 文件组织规范、Git 管理建议 |
| `docs/ARCHITECTURE_V2.md` | V2 架构设计文档 |
| `specs/active/2026-04-19--config-v3-refactor.md` | V3 配置架构设计规格与迁移指南 |
| `specs/active/2026-04-21--routing-architecture-fix.md` | 路由架构修复规格 |
| `skills/sw-superpower/README.zh.md` | 软件工程技能集说明 |
