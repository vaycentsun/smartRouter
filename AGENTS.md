# Smart Router — AGENTS.md

> 本文档供 AI 编码助手阅读，包含项目架构、开发约定和关键信息。
> 项目语言：中文（注释与文档使用中文，代码标识符使用英文）。
> AI 对话语言：中文

**版本**: 1.1.0 · **Python**: >= 3.9 · **构建后端**: hatchling · **PyPI**: `smartRouter`

---

## 开发必知命令

```bash
# 开发安装（含测试依赖）
pip install -e ".[dev]"

# 运行全部测试
pytest tests/ -v

# 运行单个子包测试
pytest tests/selector/ -v
pytest tests/integration/ -v

# 前台启动服务（调试）
smart-router start --foreground
# 或
smr start --foreground

# 快速健康检查
smr doctor

# 测试路由决策（不调用模型）
smr dry-run "Review this Python code" --strategy quality
```

> 等价短命令：`smr` = `smart-router`

---

## 源码结构（实际路径）

```
src/smart_router/
├── cli.py                    # CLI 入口（Typer），__version__ 需与 pyproject.toml 同步
├── gateway/
│   ├── server.py             # LiteLLM Proxy 封装、前台服务启动
│   ├── server_main.py        # 后台服务入口（argparse）
│   └── daemon.py             # 后台进程管理（PID 文件、start/stop/status/logs）
├── router/
│   ├── plugin.py             # SmartRouter 核心插件（继承 litellm.router.Router）
│   └── plugin_v3_adapter.py  # V3 配置适配器（备用）
├── classifier/
│   ├── task_classifier.py    # TaskTypeClassifier（规则引擎）
│   ├── difficulty_classifier.py
│   ├── embedding_matcher.py  # L2 简单词频相似度匹配（TF + 余弦）
│   └── types.py
├── selector/
│   ├── v3_selector.py        # 主模型选择器（9 种策略）
│   ├── model_selector.py     # v2 遗留选择器
│   └── strategies.py         # 兼容重导出
├── config/
│   ├── schema.py             # Pydantic 配置模型
│   ├── loader.py             # ConfigLoader：三文件 YAML 加载与验证
│   ├── v3_schema.py          # 向后兼容别名
│   └── v3_loader.py          # 向后兼容别名
├── utils/
│   ├── markers.py            # [stage:xxx] [difficulty:xxx] 解析
│   └── token_counter.py      # 轻量级 token 估算
├── misc/
│   └── coffee_qr.py          # smr coffee 命令
└── templates/                # smart-router init 生成的默认配置
    ├── providers.yaml
    ├── models.yaml
    └── routing.yaml
```

**测试目录已按源码子包拆分**，切勿假设所有测试都在 `tests/test_*.py`：
```
tests/
├── classifier/
├── cli/
├── config/
├── gateway/
├── integration/
├── misc/
├── router/
├── selector/
└── utils/
```

---

## 架构要点（容易踩坑）

### 1. 路由插件实际使用的是 V3ModelSelector
旧文档称主流程使用 `ModelSelector`，但 `router/plugin.py` 已完全切换到 `V3ModelSelector`，从 V3 Config 动态构建 `model_pool`。

### 2. 三文件解耦配置
运行时配置默认在 `~/.smart-router/`（可通过 `--config` 指定）：
- `providers.yaml` — API Key 通过 `os.environ/KEY_NAME` 引用，**禁止写明文**
- `models.yaml` — 模型能力声明（quality/cost/context/…）
- `routing.yaml` — 任务定义、capability_weights、fallback 配置

关键校验：`capability_weights` 总和必须为 1.0（±0.01）；models 引用的 provider 必须存在。

### 3. Fallback 自动推导
`Config._derive_fallback_chains()` 基于 quality 差异阈值（默认 2）自动计算 fallback 链，支持 `provider_isolation` 模式。修改模型 quality 分数会静默改变 fallback 行为。

### 4. 上下文过滤逻辑
`plugin.py` 中通过 `estimate_messages_tokens()` 估算输入 token，**+4000 预留输出**，再过滤不满足 context 窗口的模型。若长文本被路由到小窗口模型，先检查 token 估算是否溢出。

---

## 版本同步规则

发布新版本时，**三处必须同步**：
1. `pyproject.toml` 的 `version`
2. `src/smart_router/__init__.py` 的 `__version__`
3. `src/smart_router/cli.py` 的 `__version__`

CI（`.github/workflows/publish.yml`）在 `push tags v*` 时自动构建并发布到 PyPI（trusted publishing），同时更新 Homebrew Formula。

---

## 安全约束

- **Master Key 强制要求**：启动服务必须设置 `SMART_ROUTER_MASTER_KEY`，不设默认值
- **默认只绑定 127.0.0.1**：可通过 `SMART_ROUTER_HOST` / `SMART_ROUTER_PORT` 修改
- **临时配置文件安全**：`gateway/server.py` 将 LiteLLM 配置写入临时 JSON，初始化后立即 `os.unlink()` 删除
- **不收集遥测数据**

---

## 测试约定

- 使用 pytest + pytest-asyncio
- 测试中通过 `monkeypatch.setenv()` 设置虚拟 API Key，避免依赖真实环境变量
- 集成测试（`tests/integration/`）覆盖完整链路：加载 → 分类 → 选择 → LiteLLM 参数生成
- 环境隔离优先：不要假设 `~/.smart-router/` 存在真实配置

---

## 故障排查（高频率问题）

| 现象 | 最可能原因 / 快速定位 |
|------|----------------------|
| 服务无法启动 | `lsof -i :4000` 端口占用；`smr start --foreground` 看前台报错 |
| 路由不生效 / 模型被过滤 | `smr dry-run "文本"` 测试决策链路；检查 provider 环境变量是否缺失 |
| 后台进程残留 | 删除 `~/.smart-router/smart-router.pid`；`ps aux \| grep smart_router` 后 kill |
| 模型返回 401/403 | `smr list` 查看 Auth 列；确认对应 provider 环境变量已 export |

---

## 相关文档索引

| 文档 | 内容 |
|------|------|
| `docs/GUIDE.md` | 完整 CLI 命令、配置详解、客户端集成 |
| `docs/ROUTING_GUIDE.md` | 路由策略编写指南 |
| `config/examples/v3/` | 三文件配置示例（提交到 Git） |
| `specs/active/` | 活跃技术规格（V3 重构、路由架构修复） |
