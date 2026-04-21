<!-- From: /Users/vaycent/Documents/GitHub/smartRouter/AGENTS.md -->
# Smart Router — AGENTS.md

> 本文档供 AI 编码助手阅读，包含项目架构、开发约定和关键信息。

## 开发工作流约定

本项目使用 **sw-superpower** 技能集进行软件开发。所有代码修改必须遵循对应 skill 的流程：

### 可用 Skills (位于 `skills/sw-superpower/`)

| Skill | 用途 | 触发条件 |
|-------|------|----------|
| **sw-brainstorming** | 头脑风暴与需求分析 | 开始新功能开发 |
| **sw-writing-specs** | 创建详细的实现计划 | 设计已批准，需要执行计划 |
| **sw-subagent-development** | 使用子 Agent 执行计划 | 有实现计划，任务相对独立 |
| **sw-test-driven-dev** | 强制 RED-GREEN-REFACTOR 循环 | 实现任何功能或修复 Bug |
| **sw-code-review** | 两阶段代码审查 | 完成任务或功能后 |
| **sw-systematic-debugging** | 系统化 Bug 调查 | 发现 Bug 或测试失败 |
| **sw-verification-before-completion** | 标记完成前验证 | 准备标记任务完成 |
| **sw-finishing-branch** | 验证、决策、清理分支 | 所有任务完成 |

### 铁律

1. **所有代码修改必须通过 sw-test-driven-dev**: RED → GREEN → REFACTOR
2. **新功能必须先 sw-brainstorming**: 产出设计文档到 `specs/active/`
3. **任务完成后必须 sw-code-review**: 两阶段审查后才能标记完成
4. **完成前必须 sw-verification-before-completion**: 验证测试、文档、规范一致性

### 标准工作流

```
开始新功能
    ↓
sw-brainstorming → 输出: specs/active/YYYY-MM-DD--feature.md
    ↓
sw-writing-specs → 输出: specs/active/plans/YYYY-MM-DD--feature-plan.md
    ↓
sw-subagent-development (使用 TDD 开发每个子任务)
    ↓
sw-code-review (两阶段审查)
    ↓
sw-verification-before-completion
    ↓
sw-finishing-branch (如需合并)
```

### 参考资料

- [sw-superpower README](./skills/sw-superpower/README.zh.md)

## 项目概述

Smart Router（智能模型路由网关）是一个基于 LiteLLM Proxy 的本地 CLI 工具，对外暴露统一的 OpenAI API 接口，根据任务类型、难度和阶段标记自动将请求路由到最合适的底层大模型。

**核心能力**:
- 统一入口：一个 API Key 管理多个服务商（OpenAI、Anthropic、DeepSeek、Qwen、Kimi、MiniMax、GLM 等）
- 智能路由：自动识别任务类型（brainstorming/code_review/writing/reasoning/chat）并选择最优模型
- 阶段标记：支持 `[stage:code_review]` 等显式标记控制路由
- 多种策略：auto/speed/cost/quality 四种路由策略
- 自动 Fallback：模型失败时自动升级重试

## 项目结构

```
├── script/                       # 安装/卸载脚本
│   ├── install.sh               # 本地一键安装脚本（开发环境）
│   ├── install-remote.sh        # 远程一键安装脚本（PyPI + curl）
│   ├── download-config.py       # curl 下载配置脚本
│   ├── uninstall.sh             # 一键卸载脚本
│   └── verify.py                # 快速验证脚本（备用）
├── src/                          # 核心源码包
│   └── smart_router/
│       ├── cli.py               # CLI 入口（Typer 框架）
│       ├── plugin.py            # SmartRouter 插件（继承 LiteLLM Router）
│       ├── server.py            # LiteLLM Proxy 封装和启动
│       ├── server_main.py       # 后台服务入口
│       ├── daemon.py            # 后台进程管理（启动/停止/状态/日志）
│       ├── config/              # 配置系统
│       │   ├── schema.py        # Pydantic 配置模型
│       │   └── loader.py        # YAML 加载与验证
│       ├── classifier/          # 任务分类器
│       │   ├── __init__.py      # TaskClassifier（L1→L2 流水线）
│       │   ├── types.py         # 分类结果数据类
│       │   ├── rule_engine.py   # L1 正则规则引擎
│       │   └── embedding.py     # L2 向量相似度匹配（TF-IDF 风格）
│       ├── selector/            # 模型选择器
│       │   └── strategies.py    # 四种策略实现
│       └── utils/               # 工具函数
│           └── markers.py       # 阶段标记解析器
├── tests/                       # 单元测试
│   ├── test_classifier.py       # 分类器测试
│   ├── test_selector.py         # 选择器测试
│   ├── test_markers.py          # 标记解析测试
│   └── test_integration.py      # 集成测试
├── config/                      # 配置相关
│   └── examples/                # V3 三文件配置示例
├── docs/                        # 文档
│   ├── GUIDE.md                 # 详细使用指南
│   └── README.zh.md             # 中文 README
├── specs/                       # 技术规格文档
│   ├── active/                  # 活跃规格
│   ├── archived/                # 已归档规格
│   └── plans/                   # 实现计划
├── pyproject.toml               # 项目配置（Python 3.9+）
└── verify.py                    # 快速验证脚本
```

## 技术栈

- **Python**: 3.9+
- **CLI 框架**: Typer (基于 Click)
- **配置验证**: Pydantic 2.x
- **代理层**: LiteLLM (MIT License)
- **终端输出**: Rich
- **配置格式**: YAML
- **测试**: pytest + pytest-asyncio
- **构建**: hatchling

## 安装方式

### 方式一：PyPI + curl（推荐）

```bash
# 1. 通过 PyPI 安装
pip install smart-router

# 2. 下载默认配置文件
curl -sSL https://raw.githubusercontent.com/vaycentsun/smartRouter/main/script/download-config.py | python3

# 或使用 CLI 命令
smart-router init
```

### 方式二：远程一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/vaycentsun/smartRouter/main/script/install-remote.sh | bash
```

### 方式三：本地开发安装

```bash
git clone https://github.com/vaycentsun/smartRouter.git
cd smartRouter
./script/install.sh
```

### 配置 API Key

编辑 `~/.smart-router/providers.yaml`，配置环境变量名：

```yaml
providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: os.environ/OPENAI_API_KEY
    timeout: 30
```

确保对应的环境变量已设置：

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-..."
# 其他服务商...
```

## 卸载（一键卸载）

```bash
./script/uninstall.sh
```

卸载脚本会自动完成：
1. 停止服务（如果正在运行）
2. 卸载 Python 包
3. 清理日志和 PID 文件

## 运行服务

安装后提供两个等价的命令：
- `smart-router` - 完整命令名
- `smr` - 短命令名（推荐日常使用）

> 📚 **命令速查表**: [docs/GUIDE.md#命令速查表](docs/GUIDE.md#命令速查表)

### 后台运行（推荐）

```bash
smart-router start
# 或
smr start
```

输出示例：
```
✓ Smart Router 已启动
  PID: 12345
  日志: ~/.smart-router/smart-router.log
  服务: http://127.0.0.1:4000
```

### 前台运行（调试）

```bash
smart-router start --foreground
# 或
smr start -f
```

### 指定配置文件

```bash
smart-router start --config /path/to/config-dir
```

## 停止服务

```bash
smart-router stop
```

输出示例：
```
✓ Smart Router 已停止
```

## 其他管理命令

### 查看状态

```bash
smart-router status
# 或
smr status
```

### 查看日志

```bash
# 最后 50 行
smart-router logs
# 或
smr logs

# 持续跟踪（tail -f）
smart-router logs --follow
# 或
smr logs -f
```

### 重启服务

```bash
smart-router restart
# 或
smr restart
```

### 运行健康检查（包含配置验证）

```bash
smart-router doctor
# 或
smr doctor
```

### 测试路由决策（dry-run）

```bash
smart-router dry-run "请帮我审查这段代码"
# 或
smr dry-run "请帮我审查这段代码"
```

## 构建与测试命令

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_classifier.py -v

# 快速健康检查
smart-router doctor
# 或
smr doctor

# 📚 完整命令速查表: docs/GUIDE.md#命令速查表

# 构建分发包（如需发布）
python -m build
```

## 核心架构流程

```
用户请求 (OpenAI API 格式)
    ↓
LiteLLM Proxy (端口 4000)
    ↓
SmartRouter.get_available_deployment()
    ├──→ parse_markers(messages)          # 解析 [stage:xxx] [difficulty:xxx]
    │    ├── 命中 stage? → 直接使用
    │    └── 未命中 → 继续
    │
    ├──→ TaskClassifier.classify()        # L1 规则 → L2 Embedding
    │    ├── L1 RuleEngine: 正则匹配（<1ms）
    │    └── L2 EmbeddingMatcher: 相似度匹配
    │
    ├──→ ModelSelector.select()           # 根据策略选择模型
    │    ├── auto: 使用 stage_routing 默认推荐
    │    ├── speed/cost: 选择列表第一个
    │    └── quality: 选择列表最后一个
    │
    └──→ LiteLLM 父类路由到目标模型
```

## 关键组件说明

### 1. CLI (cli.py)

主要命令：
- `smart-router init` - 生成默认配置文件
- `smart-router start [--foreground]` - 后台/前台启动服务
- `smart-router stop/restart/status/logs` - 服务管理
- `smart-router dry-run "prompt"` - 测试路由决策
- `smart-router doctor` - 运行健康检查
- `smart-router list` - 列出已配置的 Provider 和模型
- `smart-router version` - 显示版本信息
- `smart-router uninstall` - 卸载（停止服务并清理数据）

> 💡 **提示**: 也可以使用短命令 `smr`，例如 `smr start`、`smr status`

> 📚 **完整命令列表**: 详见 [docs/GUIDE.md#命令速查表](docs/GUIDE.md#命令速查表)

### 2. SmartRouter 插件 (plugin.py)

继承 `litellm.router.Router`，重写 `get_available_deployment()` 注入智能路由逻辑。

### 3. 任务分类器 (classifier/)

- **L1 RuleEngine**: 基于正则表达式，<1ms 延迟
- **L2 EmbeddingMatcher**: 基于 TF-IDF 向量的余弦相似度
- **降级策略**: 分类失败时返回 `chat` 类型

### 4. 模型选择器 (selector/strategies.py)

根据 `stage_routing` 配置表选择模型：
- 配置格式: `{stage: {easy: [...], medium: [...], hard: [...]}}`
- 策略:
  - `auto`: 使用 medium 列表第一个
  - `speed`/`cost`: 使用对应列表第一个
  - `quality`: 使用对应列表最后一个

## 配置系统

配置目录: `~/.smart-router/`

```
~/.smart-router/
├── providers.yaml    # API 服务商连接配置
├── models.yaml       # 模型能力声明配置
├── routing.yaml      # 任务路由策略配置
├── smart-router.pid  # 服务进程 PID 文件
└── smart-router.log  # 服务日志文件
```

### providers.yaml - 服务商配置

```yaml
providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: os.environ/OPENAI_API_KEY
    timeout: 30
    
  anthropic:
    api_base: https://api.anthropic.com
    api_key: os.environ/ANTHROPIC_API_KEY
    timeout: 30
```

### models.yaml - 模型能力配置

```yaml
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9      # 质量评分 (1-10)
      cost: 3         # 成本评分 (10=最便宜)
      context: 128000 # 上下文长度
    supported_tasks: [coding, code_review, writing, chat]
    difficulty_support: [easy, medium, hard, expert]
```

### routing.yaml - 路由策略配置

```yaml
tasks:
  coding:
    name: "代码生成"
    description: "编写代码、实现功能"
    capability_weights:
      quality: 0.60
      cost: 0.40

difficulties:
  easy:
    name: "简单"
    description: "基础问答"
    max_tokens: 2000

strategies:
  auto:
    name: "智能自动"
    description: "根据任务类型和难度动态计算最佳模型"

fallback:
  mode: auto
  similarity_threshold: 2
  max_attempts: 3
```

## 代码风格指南

1. **类型注解**: 所有函数参数和返回值使用类型注解
2. **文档字符串**: 类和重要函数使用中文文档字符串
3. **命名规范**:
   - 类名: PascalCase
   - 函数/变量: snake_case
   - 常量: UPPER_SNAKE_CASE
4. **字符串**: 中文项目，代码注释和文档使用中文
5. **导入顺序**: stdlib → third-party → local
6. **错误处理**: 使用 `try/except` 捕获具体异常，提供友好的错误信息

## 测试策略

1. **单元测试**: 每个模块对应 `tests/test_*.py`
2. **测试命名**: `test_功能_场景` 或 `test_类名_方法名`
3. ** fixtures**: 使用 pytest fixtures 创建测试配置
4. **健康检查**: `smart-router doctor` 命令用于快速诊断问题

## 安全考虑

- API Key 只通过环境变量引用（`os.environ/KEY_NAME`），配置文件中不出现明文
- 默认只绑定 `127.0.0.1`，不暴露到公网
- master_key 用于客户端认证
- 不收集任何遥测数据

## 故障排查

- **服务无法启动**: 检查端口占用 `lsof -i :4000`，查看日志 `smart-router logs`
- **配置错误**: 运行 `smart-router doctor` 查看详细错误
- **路由不生效**: 使用 `smart-router dry-run "提示文本"` 测试
- **后台进程残留**: 手动删除 `~/.smart-router/smart-router.pid`

## 两种卸载方式

方式一：使用卸载脚本（推荐）
```bash
./script/uninstall.sh
```

方式二：使用 CLI 命令
```bash
smart-router uninstall    # 交互式确认
smart-router uninstall -f # 强制卸载
```

## 扩展指南

### 添加新的路由策略

在 `src/smart_router/selector/strategies.py` 的 `ModelSelector` 类中添加：

```python
def _select_by_my_strategy(self, candidates: List[str]) -> str:
    # 实现选择逻辑
    return selected_model
```

然后在 `select()` 方法中添加策略分支。

### 添加新的分类规则

在配置文件的 `classification_rules` 中添加正则规则：

```yaml
classification_rules:
  - pattern: '(?i)(关键词1|关键词2)'
    task_type: 新类型
    difficulty: medium
```

或在 `src/smart_router/classifier/embedding.py` 的 `BUILTIN_TYPE_EXAMPLES` 中添加示例。

### 支持新的服务商

LiteLLM 原生支持 100+ 服务商，只需在 `model_list` 中按 LiteLLM 格式配置即可。
