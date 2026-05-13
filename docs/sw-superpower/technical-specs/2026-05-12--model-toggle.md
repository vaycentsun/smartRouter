# 模型单独开关（Model Toggle）- 技术规范

## 版本
- **business-spec**: `docs/sw-superpower/business-specs/2026-05-12--model-toggle.md`
- **日期**: 2026-05-12
- **状态**: 定稿

---

## 架构概述

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ProviderModelsPanel ──► Toggle Switch ──► API Client      │
│       ▲                                          │          │
│       │                                          ▼          │
│  ModelsTable ◄────── Zustand Store ◄──── useDashboardStore │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP
┌─────────────────────────────────────────────────────────────┐
│                      Gateway (FastAPI)                       │
│  GET /api/models  ──► dashboard_api.models()               │
│  PUT /api/models/{provider}/{model}                         │
│       ──► dashboard_api.toggle_model()                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                              │
│  ConfigLoader.save_model() ──► models/{provider}.yaml      │
│       ▲                                                     │
│       │ Config 热重载                                        │
│  Config.schema.ModelConfig.enabled = True (default)         │
│       │                                                     │
│       ▼                                                     │
│  V3ModelSelector._filter_candidates() ──► 过滤 enabled=False│
└─────────────────────────────────────────────────────────────┘
```

---

## 组件设计

### 1. 配置层

#### `config/schema.py` — `ModelConfig`

```python
class ModelConfig(BaseModel):
    provider: str
    litellm_model: str
    capabilities: ModelCapabilities
    supported_tasks: List[str]
    difficulty_support: List[Literal["easy", "medium", "hard", "expert"]]
    price: Optional[ModelPrice] = Field(default=None)
    enabled: bool = Field(default=True, description="模型是否启用")
```

**向后兼容**: Pydantic 的 `default=True` 确保旧配置（无 `enabled` 字段）加载时默认启用。

#### `config/loader.py` — `ConfigLoader.save_model()`

```python
def save_model(self, provider_name: str, model_name: str, enabled: bool) -> None:
    """保存单个模型的 enabled 状态到对应 YAML 文件

    Args:
        provider_name: Provider 名称，用于定位文件 models/{provider_name}.yaml
        model_name: 模型名称
        enabled: 开关状态

    Raises:
        ConfigError: 文件不存在、模型不存在、写入失败或验证失败
    """
```

**实现细节**:
1. 定位文件：`self.config_dir / "models" / f"{provider_name}.yaml"`
2. 读取 YAML（优先 ruamel.yaml 保留注释，回退 yaml.safe_load）
3. 检查 `data["models"][model_name]` 是否存在，不存在则抛 `ConfigError`
4. 设置 `data["models"][model_name]["enabled"] = enabled`
5. 写回文件（优先 ruamel.yaml，回退 yaml.safe_dump）
6. 调用 `self.validate()` 验证整体配置
7. 验证失败则恢复备份

**错误类型**:
- `ConfigError("Model 'xxx' not found in models/{provider}.yaml")`
- `ConfigError("Configuration file not found: models/{provider}.yaml")`
- `ConfigError("Config validation failed after save: ...")`

### 2. 选择器层

#### `selector/v3_selector.py` — `_filter_candidates()`

在现有过滤逻辑之后、加入 `candidates` 之前，增加一行：

```python
if not getattr(model, 'enabled', True):
    continue
```

**影响范围**:
- `select()` — 主路由选择
- `select_ranked()` — 排序候选列表
- `get_available_models()` — fallback 候选
- `get_candidates()` — 兼容接口

**注意**: `get_provider_fallback_chain()` 不调用 `_filter_candidates`，因此 fallback 链推导不受 `enabled` 影响。这是预期行为——fallback 链是静态配置推导，实际 fallback 时由 `get_available_models()` 过滤。

### 3. API 层

#### `gateway/dashboard_api.py`

**新增请求体 Schema**:

```python
class ModelToggleRequest(BaseModel):
    enabled: bool
```

**新增 API 处理函数**:

```python
async def toggle_model(request: Request, provider_name: str, model_name: str, body: ModelToggleRequest):
    """切换模型启用/禁用状态

    Args:
        provider_name: Provider 名称
        model_name: 模型名称
        body: { enabled: bool }

    Returns:
        { "success": True, "provider": str, "model": str, "enabled": bool }

    Raises:
        HTTPException(404): Provider 或 Model 不存在
        HTTPException(500): 保存或验证失败
    """
```

**流程**:
1. 加载当前配置 `loader.load()`
2. 验证 `provider_name` 存在于 `cfg.providers`
3. 验证 `model_name` 存在于 `cfg.models` 且 `model.provider == provider_name`
4. 调用 `loader.save_model(provider_name, model_name, body.enabled)`
5. 触发配置热重载：`request.app.state.router.reload_config()`（若存在）
6. 返回成功响应

**修改现有 API `models()`**:
在返回的每个模型字典中增加 `"enabled": model.enabled`。

**API 注册**（在 `register_routes(app)` 中）:
```python
app.put("/api/models/{provider_name}/{model_name}")(toggle_model)
```

### 4. 前端层

#### `frontend/src/types/index.ts`

```typescript
export interface ModelInfo {
  name: string
  provider: string
  available: boolean
  health_status: HealthStatus
  quality: number
  cost: number
  context: number
  supported_tasks: string[]
  enabled: boolean  // 新增
}
```

#### `frontend/src/api/client.ts`

```typescript
export const api = {
  // ... existing methods
  toggleModel: (provider: string, model: string, enabled: boolean) =>
    client.put<{ success: boolean; provider: string; model: string; enabled: boolean }>(
      `/api/models/${provider}/${model}`,
      { enabled }
    ).then((r) => r.data),
}
```

#### `frontend/src/store/useDashboardStore.ts`

**新增状态**:
```typescript
isTogglingModel: Record<string, boolean>  // key: `${provider}/${model}`
```

**新增 Action**:
```typescript
toggleModel: async (provider: string, model: string, enabled: boolean) => {
  const key = `${provider}/${model}`
  set((state) => ({ isTogglingModel: { ...state.isTogglingModel, [key]: true } }))
  try {
    await api.toggleModel(provider, model, enabled)
    // 乐观更新：直接修改本地 models 列表
    set((state) => ({
      models: state.models.map((m) =>
        m.name === model && m.provider === provider ? { ...m, enabled } : m
      ),
      toast: { message: `模型 ${model} 已${enabled ? '启用' : '禁用'}`, type: 'success' },
    }))
  } catch (err) {
    set({ error: (err as Error).message, toast: { message: '操作失败', type: 'error' } })
  } finally {
    set((state) => ({ isTogglingModel: { ...state.isTogglingModel, [key]: false } }))
  }
}
```

#### `frontend/src/components/ProviderModelsPanel.tsx`

**表格列调整**:
- 在"状态"列右侧新增"启用"列
- 每行渲染一个 Toggle Switch 组件（自定义样式或原生 `<input type="checkbox">`）
- Switch 的 `checked` 绑定 `model.enabled`
- `onChange` 调用 `store.toggleModel(model.provider, model.name, !model.enabled)`
- 切换时显示 loading（`isTogglingModel[key]`）

**Switch 样式**（Tailwind）：
```tsx
<label className="relative inline-flex items-center cursor-pointer">
  <input
    type="checkbox"
    className="sr-only peer"
    checked={model.enabled}
    onChange={...}
    disabled={isToggling}
  />
  <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[#34C759]" />
</label>
```

#### `frontend/src/components/ModelsTable.tsx`

在"状态"列中增加启用状态：
- 如果 `model.enabled === false`，状态显示为"已禁用"（灰色）
- 或者新增独立列显示启用状态

**推荐**：在现有"状态"列中叠加显示：
```
{model.enabled ? (原有 available 逻辑) : (
  <span className="inline-flex items-center gap-1.5 text-[#86868b] text-sm">
    <span className="w-1.5 h-1.5 rounded-full bg-[#86868b]" />
    已禁用
  </span>
)}
```

---

## 数据流

### 开关关闭流程

```
User clicks Switch in ProviderModelsPanel
    │
    ▼
useDashboardStore.toggleModel(provider, model, false)
    │
    ▼ PUT /api/models/{provider}/{model} { enabled: false }
Gateway.dashboard_api.toggle_model()
    │
    ▼
ConfigLoader.save_model(provider, model, false)
    │
    ├──► 读取 models/{provider}.yaml
    ├──► 修改 models[model].enabled = false
    ├──► 写回 YAML
    └──► validate() → 整体配置验证通过
    │
    ▼
app.state.router.reload_config() (if exists)
    │
    ▼
V3ModelSelector 重新构建，_filter_candidates 排除 enabled=False
    │
    ▼
Gateway 返回 { success: true, ... }
    │
    ▼
Frontend 乐观更新本地 models 列表，显示 Toast
```

### 配置热重载流程（文件系统变更）

```
File watcher detects models/{provider}.yaml change
    │
    ▼
SmartRouter.reload_config()
    │
    ▼
ConfigLoader.load() → 新 Config 包含 enabled=False
    │
    ▼
V3ModelSelector 重建，自动排除禁用模型
```

---

## 错误处理

| 场景 | 错误类型 | 前端行为 | 后端行为 |
|------|---------|---------|---------|
| 模型不存在 | HTTP 404 | Toast 错误提示 | 返回 `{ detail: "Model not found" }` |
| Provider 不存在 | HTTP 404 | Toast 错误提示 | 返回 `{ detail: "Provider not found" }` |
| YAML 写入失败 | HTTP 500 | Toast 错误提示 | 返回 `{ detail: "Failed to save model config" }` |
| 保存后验证失败 | HTTP 500 | Toast 错误提示 | 恢复备份，返回验证错误详情 |
| 前端网络错误 | Error | Toast 错误提示，不修改本地状态 | — |

---

## 安全考虑

- **输入校验**: `ModelToggleRequest.enabled` 由 Pydantic 严格校验为 `bool`
- **路径校验**: `provider_name` 和 `model_name` 通过配置加载验证存在性，防止路径遍历
- **Master Key**: 所有 Dashboard API 已受现有认证中间件保护
- **YAML 安全**: 使用 `yaml.safe_load` / `yaml.safe_dump`，禁止自定义构造器

---

## 默认模板更新

所有 `core/smart_router/templates/models/*.yaml` 中的模型配置增加 `enabled: true`：

```yaml
models:
  qwen3.5-flash:
    provider: aliyun
    litellm_model: openai/qwen3.5-flash
    enabled: true          # 新增
    capabilities:
      ...
```

---

## 测试策略

### 后端测试

| 测试文件 | 测试内容 |
|---------|---------|
| `config/tests/test_loader.py` | `save_model()` 正常保存、模型不存在抛错、验证失败恢复备份 |
| `config/tests/test_schema.py` | `ModelConfig` 默认 `enabled=True`、显式 `enabled=False` 合法 |
| `selector/tests/test_v3_selector.py` | `_filter_candidates` 排除 `enabled=False`、其他过滤逻辑不受影响 |
| `gateway/tests/test_dashboard_api.py` | `PUT /api/models/{provider}/{model}` 成功、404、500 场景；`GET /api/models` 返回 `enabled` |
| `tests/integration/test_v3_integration.py` | 端到端：禁用模型后 `dry-run` 不再选中 |

### 前端测试

| 测试文件 | 测试内容 |
|---------|---------|
| `src/components/ProviderModelsPanel.test.tsx` | 开关渲染、点击触发 API、loading 状态、错误处理 |
| `src/store/useDashboardStore.test.ts` | `toggleModel` action 成功/失败路径、乐观更新 |
| `src/api/client.test.ts` | `toggleModel` API 调用参数正确 |

---

## 验收标准（完整版）

- [ ] `config/schema.py::ModelConfig` 增加 `enabled: bool = Field(default=True)`
- [ ] `config/loader.py` 新增 `save_model()` 方法，支持 ruamel.yaml / yaml.safe_dump 双路径
- [ ] `selector/v3_selector.py::_filter_candidates` 排除 `enabled=False` 模型
- [ ] `gateway/dashboard_api.py` 新增 `PUT /api/models/{provider}/{model}` 和 `ModelToggleRequest`
- [ ] `GET /api/models` 返回字段包含 `enabled`
- [ ] 所有默认模板 `models/*.yaml` 增加 `enabled: true`
- [ ] 前端 `ModelInfo` 类型增加 `enabled: boolean`
- [ ] 前端 `api/client.ts` 新增 `toggleModel()`
- [ ] 前端 `useDashboardStore.ts` 新增 `toggleModel` action 和 `isTogglingModel` 状态
- [ ] `ProviderModelsPanel.tsx` 表格新增开关列，支持点击切换
- [ ] `ModelsTable.tsx` 显示禁用状态
- [ ] 未设置 `enabled` 的旧配置默认视为启用
- [ ] 禁用模型后 `smr dry-run` 不再选中
- [ ] 禁用模型后实际请求不再路由到该模型
- [ ] 配置热重载生效，无需重启
- [ ] 现有 pytest 测试全部通过
- [ ] 新增测试覆盖 Schema、Loader、Selector、API 层
