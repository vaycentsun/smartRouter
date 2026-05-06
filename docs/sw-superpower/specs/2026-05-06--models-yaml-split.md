# Spec: models.yaml 按 Provider 拆分

**日期**: 2026-05-06  
**状态**: 设计完成  
**依赖**: 阶段一（Provider 健康检查）已完成

---

## 1. 背景与动机

当前 `models.yaml` 是一个聚合文件，包含所有 Provider 的模型配置。随着模型数量增加（>40 个），单文件维护困难。结合阶段一实现的 Provider 健康检查，需要支持：
- 通过 `/api/providers/{name}/health` 探测到的模型，自动写入对应 Provider 的配置文件
- 按 Provider 独立管理模型清单

## 2. 目标

1. 将 `models.yaml` 拆分为 `models/` 目录下的多个 YAML 文件（按 Provider）
2. 支持健康检查 API 自动将新发现的模型写入对应文件
3. 虚拟模型（`auto`、`smart-router` 等）独立到 `_virtual.yaml`
4. 不实现自动迁移，废弃 `models.yaml` 单文件

## 3. 非目标

- 不实现 `models.yaml` → `models/` 的自动迁移
- 不保留 `models.yaml` 向后兼容
- 不在探测时修改已有模型的能力值（quality/cost 等）

## 4. 文件结构

```
~/.smart-router/
├── providers.yaml          # 新增 _virtual provider
├── routing.yaml
├── models/                 # 新增目录
│   ├── openai.yaml
│   ├── anthropic.yaml
│   ├── aliyun.yaml
│   ├── moonshot-cn.yaml
│   ├── moonshot-ai.yaml
│   ├── zhipu.yaml
│   ├── minimax.yaml
│   ├── lmstudio.yaml
│   └── _virtual.yaml       # 虚拟模型
```

### 4.1 单文件格式

每个文件只包含该 Provider 的模型：

```yaml
# models/aliyun.yaml
models:
  qwen3.5-plus:
    provider: aliyun
    litellm_model: openai/qwen-plus
    capabilities:
      quality: 8
      cost: 10
      context: 128000
    supported_tasks: [coding, code_review, writing, creative, reasoning, analysis, explanation, translation, chat, brainstorming]
    difficulty_support: [easy, medium, hard]
```

### 4.2 虚拟模型文件

```yaml
# models/_virtual.yaml
models:
  auto:
    provider: _virtual
    litellm_model: openai/qwen3.6-plus  # fallback 模型：当 LiteLLM 直接处理 model=auto 时使用
    capabilities:
      quality: 9
      cost: 10
      context: 128000
    supported_tasks: [coding, code_review, writing, creative, reasoning, analysis, explanation, translation, chat, brainstorming]
    difficulty_support: [easy, medium, hard, expert]
```

> 注：虚拟模型的 `litellm_model` 是 fallback 真实模型。当用户请求 `model=auto` 时，SmartRouter 中间件会拦截并执行智能路由，但 LiteLLM 层面仍需一个有效的模型配置作为 fallback。

### 4.3 providers.yaml 变更

```yaml
providers:
  # ... 现有 providers ...
  _virtual:
    api_base: ""
    api_key: ""
    timeout: 30
```

## 5. 核心变更

### 5.1 ConfigLoader

- **`load()`**: 从 `models/` 目录遍历所有 `.yaml` 文件，合并 `models` 键
- **`_load_models()`**: 新增私有方法，负责目录遍历和合并
  - 遍历 `models/` 下所有 `.yaml` 文件
  - 合并各文件的 `models` 键
  - **键冲突检测**: 如果同名模型出现在多个文件中，报错说明冲突位置
- **验证**: 加载后校验所有 `model.provider` 存在于 `providers.yaml`
- **共存策略**: 如果 `models/` 目录存在，优先使用 `models/`，忽略 `models.yaml`；如果 `models/` 不存在且 `models.yaml` 存在，报错提示：
  > "models/ 目录不存在。models.yaml 单文件已废弃，请拆分到 models/ 目录。参考：`smr init` 生成新模板"

### 5.2 ConfigWatcher

无需修改。`watchdog` 监听 `config_dir` 已自动包含子目录变更。

### 5.3 HealthChecker 自动写入

**触发时机**: `GET /api/providers/{name}/health` 完成检查且状态为 `healthy` 后，自动将新发现的模型写入 `models/{name}.yaml`。

**写入逻辑**:
1. 读取 `models/{name}.yaml`（如果存在）
2. 对 Provider 返回的每个新模型 ID：
   - 如果已在文件中 → 保留现有配置（不动 quality/cost 等）
   - 如果不在文件中 → 使用默认值创建新条目
3. 写回 `models/{name}.yaml`
4. 触发配置重载（通过 `ConfigWatcher` 自动检测文件变更）

**默认模型模板**:
```yaml
{model_id}:
  provider: {provider_name}
  litellm_model: openai/{model_id}  # 默认值，用户需根据实际 Provider 调整
  capabilities:
    quality: 5
    cost: 5
    context: 32000
  supported_tasks: [chat]
  difficulty_support: [easy, medium]
```

> 注：`litellm_model` 使用 `openai/` 前缀作为默认值，因为多数 Provider 采用 OpenAI 兼容接口。用户应在 UI 中手动修正为实际值（如 `anthropic/claude-3`）。

### 5.4 虚拟模型处理

- `ProviderHealthChecker` 自动跳过 `_virtual` provider（`is_provider_available` 返回 False）
- Dashboard API 中 `_virtual` 的模型显示 `available: true`，但 `health_status: null`（不检查）

## 6. API 变更

### 6.1 新增/修改

| API | 变更 |
|-----|------|
| `GET /api/providers/{name}/models` | 检查完成后，若 healthy，自动写入 `models/{name}.yaml` |
| `GET /api/models` | 从 `models/` 目录加载 |

### 6.2 响应不变

所有 API 的响应格式保持不变，仅数据源从 `models.yaml` 改为 `models/` 目录。

## 7. 测试策略

| 测试文件 | 覆盖内容 |
|---------|---------|
| `test_config_loader.py` | `models/` 目录加载、多文件合并、验证错误 |
| `test_health_checker.py` | 自动写入逻辑、默认值填充、已有配置保留 |
| `test_dashboard_api.py` | `/api/providers/{name}/models` 自动写入后文件内容验证 |

## 8. 验收标准

- [ ] `ConfigLoader.load()` 能从 `models/` 目录正确加载并合并多个 YAML 文件
- [ ] `models.yaml` 不存在时，给出清晰的错误提示
- [ ] 虚拟模型位于 `_virtual.yaml`，provider 为 `"_virtual"`
- [ ] HealthChecker 跳过 `_virtual` provider
- [ ] `GET /api/providers/{name}/models` 在 healthy 后自动写入新模型到 `models/{name}.yaml`
- [ ] 已有模型的配置值在自动写入时不被覆盖
- [ ] ConfigWatcher 能监听 `models/*.yaml` 变更并触发重载（需新增测试验证）
- [ ] 所有现有测试通过

## 9. 风险

| 风险 | 缓解措施 |
|------|---------|
| 用户升级后 models.yaml 不工作 | 清晰的错误提示 + `smr init` 模板 |
| 自动写入覆盖用户手动配置 | 写入逻辑中检查已有模型，保留现有值 |
| 多文件合并时键冲突 | 加载时校验，冲突时报错（同名模型在不同文件中） |
