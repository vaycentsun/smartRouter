# 模型单独开关（Model Toggle）- 实施计划

**technical-spec**: `docs/sw-superpower/technical-specs/2026-05-12--model-toggle.md`  
**任务数**: 18  
**预计总时间**: 90 分钟

---

## 任务清单

| # | 任务 | 文件 | 类型 | 依赖 |
|---|------|------|------|------|
| 1 | Schema: ModelConfig 增加 enabled 字段 | `config/schema.py` | 修改 | — |
| 2 | Schema 测试: ModelConfig 默认值与显式值 | `config/tests/test_schema.py` | 测试 | 1 |
| 3 | Loader: 新增 save_model() 方法 | `config/loader.py` | 修改 | 1 |
| 4 | Loader 测试: save_model() 场景覆盖 | `config/tests/test_loader.py` | 测试 | 3 |
| 5 | Selector: _filter_candidates 过滤 enabled=False | `selector/v3_selector.py` | 修改 | 1 |
| 6 | Selector 测试: 禁用模型不参与选择 | `selector/tests/test_v3_selector.py` | 测试 | 5 |
| 7 | Dashboard API: 新增 toggle_model + models() 返回 enabled | `gateway/dashboard_api.py` | 修改 | 3 |
| 8 | Dashboard API 测试: toggle_model 接口 | `gateway/tests/test_dashboard_api.py` | 测试 | 7 |
| 9 | 默认模板: 所有 models/*.yaml 增加 enabled: true | `templates/models/*.yaml` | 修改 | 1 |
| 10 | 前端类型: ModelInfo 增加 enabled | `src/types/index.ts` | 修改 | — |
| 11 | 前端 API: client.ts 新增 toggleModel | `src/api/client.ts` | 修改 | 10 |
| 12 | 前端 API 测试: toggleModel 调用 | `src/api/client.test.ts` | 测试 | 11 |
| 13 | 前端 Store: useDashboardStore 新增 toggleModel | `src/store/useDashboardStore.ts` | 修改 | 11 |
| 14 | 前端 Store 测试: toggleModel action | `src/store/useDashboardStore.test.ts` | 测试 | 13 |
| 15 | 前端 UI: ProviderModelsPanel 新增开关列 | `src/components/ProviderModelsPanel.tsx` | 修改 | 13 |
| 16 | 前端 UI 测试: ProviderModelsPanel 开关交互 | `src/components/ProviderModelsPanel.test.tsx` | 测试 | 15 |
| 17 | 前端 UI: ModelsTable 显示禁用状态 | `src/components/ModelsTable.tsx` | 修改 | 10 |
| 18 | 集成测试: 禁用模型后 dry-run 不选中 | `tests/integration/test_v3_integration.py` | 测试 | 5,7 |

---

## 详细任务

### 任务 1: Schema — ModelConfig 增加 enabled 字段

**文件**: `core/smart_router/config/schema.py`

**动作**: 在 `ModelConfig` 类末尾增加 `enabled` 字段

**详情**:
在 `price` 字段之后插入：
```python
    enabled: bool = Field(default=True, description="模型是否启用")
```

需要 `from pydantic import Field` 已在文件顶部导入，无需额外导入。

**验证**:
- [ ] `pytest core/smart_router/config/tests/ -k test_model_config` 先失败（RED）
- [ ] 实现后通过（GREEN）

---

### 任务 2: Schema 测试 — ModelConfig 默认值与显式值

**文件**: `core/smart_router/config/tests/test_schema.py`（若不存在则创建）

**动作**: 编写测试验证 `enabled` 字段行为

**详情**:
测试场景：
1. 不传入 `enabled` 时默认 `True`
2. 显式传入 `enabled=False` 时生效
3. `enabled` 不是字符串或其他类型

```python
import pytest
from smart_router.config.schema import ModelConfig, ModelCapabilities

def test_model_config_enabled_default():
    model = ModelConfig(
        provider="test",
        litellm_model="openai/test",
        capabilities=ModelCapabilities(quality=5, cost=5, context=32000),
        supported_tasks=["chat"],
        difficulty_support=["easy"],
    )
    assert model.enabled is True

def test_model_config_enabled_explicit_false():
    model = ModelConfig(
        provider="test",
        litellm_model="openai/test",
        capabilities=ModelCapabilities(quality=5, cost=5, context=32000),
        supported_tasks=["chat"],
        difficulty_support=["easy"],
        enabled=False,
    )
    assert model.enabled is False
```

**验证**:
- [ ] `pytest core/smart_router/config/tests/test_schema.py -v` 全部通过

---

### 任务 3: Loader — 新增 save_model() 方法

**文件**: `core/smart_router/config/loader.py`

**动作**: 在 `ConfigLoader` 类中新增 `save_model()` 方法

**详情**:
在 `save_routing()` 方法之后、`ConfigError` 类之前插入：

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
        filepath = self.config_dir / "models" / f"{provider_name}.yaml"
        if not filepath.exists():
            raise ConfigError(f"Configuration file not found: {filepath}")

        # 备份原文件
        backup_path = filepath.with_suffix(".yaml.bak")
        if filepath.exists():
            try:
                backup_path.write_text(filepath.read_text(encoding="utf-8"), encoding="utf-8")
            except IOError:
                pass

        # 读取并修改
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigError(f"Failed to read {filepath}: {e}") from e

        models = data.get("models", {})
        if model_name not in models:
            raise ConfigError(f"Model '{model_name}' not found in {filepath.name}")

        models[model_name]["enabled"] = enabled

        # 尝试使用 ruamel.yaml 保留注释
        try:
            from ruamel.yaml import YAML
            yaml_inst = YAML()
            yaml_inst.preserve_quotes = True
            yaml_inst.default_flow_style = False

            with open(filepath, "r", encoding="utf-8") as f:
                existing = yaml_inst.load(f)
            existing["models"][model_name]["enabled"] = enabled

            with open(filepath, "w", encoding="utf-8") as f:
                yaml_inst.dump(existing, f)
        except ImportError:
            # 回退到标准 yaml
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    yaml.safe_dump(
                        data,
                        f,
                        allow_unicode=True,
                        sort_keys=False,
                        default_flow_style=False,
                    )
            except Exception as e:
                raise ConfigError(f"Failed to write {filepath}: {e}") from e

        # 写入后验证
        errors = self.validate()
        if errors:
            if backup_path.exists():
                try:
                    filepath.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
                except IOError:
                    pass
            raise ConfigError(f"Config validation failed after save: {'; '.join(errors)}")
```

**验证**:
- [ ] `pytest core/smart_router/config/tests/ -k test_save_model` 先失败（RED）
- [ ] 实现后通过（GREEN）

---

### 任务 4: Loader 测试 — save_model() 场景覆盖

**文件**: `core/smart_router/config/tests/test_loader.py`

**动作**: 为 `save_model()` 编写单元测试

**详情**:
测试场景：
1. 正常保存 `enabled=False`，验证 YAML 文件内容
2. 正常保存 `enabled=True`，验证 YAML 文件内容
3. 模型不存在时抛 `ConfigError`
4. 文件不存在时抛 `ConfigError`
5. 保存后整体配置验证失败时恢复备份

使用 `tmp_path` fixture 创建临时配置目录结构：
```
tmp_path/
  providers.yaml
  models/
    test.yaml
  routing.yaml
```

**验证**:
- [ ] `pytest core/smart_router/config/tests/test_loader.py -v` 全部通过

---

### 任务 5: Selector — _filter_candidates 过滤 enabled=False

**文件**: `core/smart_router/selector/v3_selector.py`

**动作**: 在 `_filter_candidates()` 中加入 `enabled` 过滤

**详情**:
在现有过滤逻辑之后（`requires_vision` 检查之后、`candidates.append` 之前）插入：

```python
            # 检查模型是否被禁用
            if not getattr(model, 'enabled', True):
                continue
```

**验证**:
- [ ] `pytest core/smart_router/selector/tests/ -k test_filter_candidates` 先失败（RED）
- [ ] 实现后通过（GREEN）

---

### 任务 6: Selector 测试 — 禁用模型不参与选择

**文件**: `core/smart_router/selector/tests/test_v3_selector.py`

**动作**: 编写测试验证 `_filter_candidates` 排除禁用模型

**详情**:
测试场景：
1. 两个模型支持相同任务和难度，其中一个 `enabled=False`，只返回启用的模型
2. 全部模型 `enabled=False` 时返回空列表
3. 旧配置（无 `enabled` 字段）的模型默认被包含

**验证**:
- [ ] `pytest core/smart_router/selector/tests/test_v3_selector.py -v` 全部通过

---

### 任务 7: Dashboard API — 新增 toggle_model + models() 返回 enabled

**文件**: `core/smart_router/gateway/dashboard_api.py`

**动作**: 
1. 在 `models()` 函数返回字典中增加 `"enabled": model.enabled`
2. 新增 `ModelToggleRequest` Schema
3. 新增 `toggle_model()` 处理函数
4. 在 `register_routes()` 中注册新路由

**详情**:

**新增 Schema**（在文件顶部 Pydantic 模型区域）：
```python
class ModelToggleRequest(BaseModel):
    enabled: bool
```

**修改 `models()`**:
在 `result.append({...})` 中添加 `"enabled": model.enabled`。

**新增 `toggle_model()`**（放在 `provider_models()` 之后）：
```python
async def toggle_model(request: Request, provider_name: str, model_name: str, body: ModelToggleRequest):
    config_dir = Path.home() / ".smart-router"
    loader = ConfigLoader(config_dir)

    try:
        cfg = loader.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置加载失败: {e}")

    if provider_name not in cfg.providers:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_name}")

    if model_name not in cfg.models:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

    model = cfg.models[model_name]
    if model.provider != provider_name:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' does not belong to provider '{provider_name}'")

    try:
        loader.save_model(provider_name, model_name, body.enabled)
    except ConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 触发配置热重载
    router = getattr(request.app.state, "router", None)
    if router and hasattr(router, "reload_config"):
        try:
            router.reload_config()
        except Exception:
            pass  # 热重载失败不阻塞 API 响应

    return {
        "success": True,
        "provider": provider_name,
        "model": model_name,
        "enabled": body.enabled,
    }
```

**注册路由**（在 `register_routes()` 中）：
在 `app.get("/api/providers/{provider_name}/models")(provider_models)` 之后插入：
```python
    app.put("/api/models/{provider_name}/{model_name}")(toggle_model)
```

**验证**:
- [ ] `pytest core/smart_router/gateway/tests/ -k test_toggle_model` 先失败（RED）
- [ ] 实现后通过（GREEN）

---

### 任务 8: Dashboard API 测试 — toggle_model 接口

**文件**: `core/smart_router/gateway/tests/test_dashboard_api.py`

**动作**: 为 `PUT /api/models/{provider}/{model}` 和 `GET /api/models` 的 `enabled` 字段编写测试

**详情**:
测试场景：
1. `PUT /api/models/openai/gpt-4o {enabled:false}` 成功，返回 200
2. `GET /api/models` 返回的模型中包含 `"enabled": false`
3. `PUT` 不存在的 provider 返回 404
4. `PUT` 不存在的 model 返回 404
5. `PUT` 不属于该 provider 的 model 返回 404
6. `PUT` 保存后验证失败返回 500

**验证**:
- [ ] `pytest core/smart_router/gateway/tests/test_dashboard_api.py -v` 全部通过

---

### 任务 9: 默认模板 — 所有 models/*.yaml 增加 enabled: true

**文件**: `core/smart_router/templates/models/*.yaml`（共 9 个文件）

**动作**: 在每个模型配置中 `litellm_model` 之后插入 `enabled: true`

**详情**:
文件列表：
- `_virtual.yaml`
- `aliyun.yaml`
- `anthropic.yaml`
- `lmstudio.yaml`
- `minimax.yaml`
- `moonshot-ai.yaml`
- `moonshot-cn.yaml`
- `openai.yaml`
- `zhipu.yaml`

每个文件中的每个模型在 `litellm_model` 行后插入 `enabled: true`。

**验证**:
- [ ] `smr init` 生成的默认配置中所有模型包含 `enabled: true`
- [ ] `pytest core/smart_router/tests/cli/ -k test_init` 通过（若存在相关测试）

---

### 任务 10: 前端类型 — ModelInfo 增加 enabled

**文件**: `frontend/src/types/index.ts`

**动作**: 在 `ModelInfo` 接口中增加 `enabled: boolean`

**详情**:
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

**验证**:
- [ ] `cd frontend && npx tsc --noEmit` 无类型错误

---

### 任务 11: 前端 API — client.ts 新增 toggleModel

**文件**: `frontend/src/api/client.ts`

**动作**: 在 `api` 对象中新增 `toggleModel` 方法

**详情**:
```typescript
  toggleModel: (provider: string, model: string, enabled: boolean) =>
    client.put<{ success: boolean; provider: string; model: string; enabled: boolean }>(
      `/api/models/${provider}/${model}`,
      { enabled }
    ).then((r) => r.data),
```

插入位置：在 `api` 对象内部，`getModelOverrides` 之后或 `getModelOverride` 之前。

**验证**:
- [ ] `cd frontend && npx tsc --noEmit` 无类型错误

---

### 任务 12: 前端 API 测试 — toggleModel 调用

**文件**: `frontend/src/api/client.test.ts`

**动作**: 编写测试验证 `api.toggleModel` 调用正确的 URL 和 body

**详情**:
测试场景：
1. `api.toggleModel("aliyun", "qwen3.5-flash", false)` 发起 `PUT /api/models/aliyun/qwen3.5-flash` 请求
2. 请求 body 为 `{ enabled: false }`
3. 成功时返回 `{ success: true, provider: "aliyun", model: "qwen3.5-flash", enabled: false }`

mock axios 的 `put` 方法。

**验证**:
- [ ] `cd frontend && npm test -- src/api/client.test.ts` 通过

---

### 任务 13: 前端 Store — useDashboardStore 新增 toggleModel

**文件**: `frontend/src/store/useDashboardStore.ts`

**动作**: 
1. 在 `DashboardState` 接口中新增 `isTogglingModel`
2. 在 `useDashboardStore` 的默认状态中初始化
3. 新增 `toggleModel` action

**详情**:

**接口新增**:
```typescript
  isTogglingModel: Record<string, boolean>
  toggleModel: (provider: string, model: string, enabled: boolean) => Promise<void>
```

**默认状态**:
```typescript
  isTogglingModel: {},
```

**Action 实现**:
```typescript
  toggleModel: async (provider: string, model: string, enabled: boolean) => {
    const key = `${provider}/${model}`
    set((state) => ({ isTogglingModel: { ...state.isTogglingModel, [key]: true } }))
    try {
      await api.toggleModel(provider, model, enabled)
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
  },
```

**验证**:
- [ ] `cd frontend && npx tsc --noEmit` 无类型错误

---

### 任务 14: 前端 Store 测试 — toggleModel action

**文件**: `frontend/src/store/useDashboardStore.test.ts`

**动作**: 编写测试验证 `toggleModel` action 的成功和失败路径

**详情**:
测试场景：
1. toggleModel 成功：本地 models 列表更新、显示成功 Toast
2. toggleModel 失败：显示错误 Toast、models 列表不变
3. isTogglingModel 状态在请求期间为 true，结束后为 false

mock `api.toggleModel`。

**验证**:
- [ ] `cd frontend && npm test -- src/store/useDashboardStore.test.ts` 通过

---

### 任务 15: 前端 UI — ProviderModelsPanel 新增开关列

**文件**: `frontend/src/components/ProviderModelsPanel.tsx`

**动作**: 
1. 在表格中新增"启用"列
2. 每行渲染 Toggle Switch
3. 绑定 `onChange` 到 `store.toggleModel`
4. 显示 loading 状态

**详情**:

**表格表头新增**（在 `<th onClick={() => handleSort('status')}>` 之后）：
```tsx
                <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">
                  启用
                </th>
```

**表格行新增**（在 `</td>` 状态列之后）：
```tsx
                    <td className="px-4 py-3">
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          className="sr-only peer"
                          checked={model.enabled}
                          onChange={() => {
                            const store = useDashboardStore.getState()
                            store.toggleModel(model.provider, model.name, !model.enabled)
                          }}
                          disabled={isToggling}
                        />
                        <div className={`w-9 h-5 rounded-full peer after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-4 after:w-4 after:transition-all ${model.enabled ? 'bg-[#34C759] after:translate-x-full after:border-white' : 'bg-gray-200 after:border-gray-300'} ${isToggling ? 'opacity-50' : ''}`} />
                      </label>
                    </td>
```

**注意**: `isToggling` 从 store 的 `isTogglingModel` 状态获取。

**验证**:
- [ ] `cd frontend && npx tsc --noEmit` 无类型错误
- [ ] 开发服务器中 Provider 详情页显示开关列

---

### 任务 16: 前端 UI 测试 — ProviderModelsPanel 开关交互

**文件**: `frontend/src/components/ProviderModelsPanel.test.tsx`

**动作**: 编写测试验证开关渲染和点击行为

**详情**:
测试场景：
1. 每个模型行渲染 checkbox input
2. checkbox 的 checked 状态与 `model.enabled` 一致
3. 点击 checkbox 触发 `store.toggleModel`
4. 切换中禁用 checkbox

mock `useDashboardStore`。

**验证**:
- [ ] `cd frontend && npm test -- src/components/ProviderModelsPanel.test.tsx` 通过

---

### 任务 17: 前端 UI — ModelsTable 显示禁用状态

**文件**: `frontend/src/components/ModelsTable.tsx`

**动作**: 在"状态"列中叠加显示禁用状态

**详情**:
修改状态列渲染逻辑：
```tsx
                <td className="px-4 py-3">
                  {!model.enabled ? (
                    <span className="inline-flex items-center gap-1.5 text-[#86868b] text-sm">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#86868b]" />
                      已禁用
                    </span>
                  ) : model.available ? (
                    <span className="inline-flex items-center gap-1.5 text-[#34C759] text-sm">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#34C759] pulse-glow" />
                      在线
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-[#FF3B30] text-sm">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#FF3B30] pulse-glow-red" />
                      离线
                    </span>
                  )}
                </td>
```

**验证**:
- [ ] `cd frontend && npx tsc --noEmit` 无类型错误
- [ ] 开发服务器中 ModelsTable 禁用模型显示"已禁用"

---

### 任务 18: 集成测试 — 禁用模型后 dry-run 不选中

**文件**: `core/smart_router/tests/integration/test_v3_integration.py`

**动作**: 编写端到端测试验证禁用模型后不再被选中

**详情**:
测试场景：
1. 配置两个模型支持相同任务，一个 `enabled=False`
2. 调用 `dry-run` 或 `selector.select()`，验证返回的模型不是被禁用的那个
3. 禁用所有模型时抛出 `NoModelAvailableError`

**验证**:
- [ ] `pytest core/smart_router/tests/integration/test_v3_integration.py -v` 通过

---

## 深度自检

| # | 检查项 | 状态 |
|---|--------|------|
| 1 | 完整性：无 TODO/占位符 | 通过 |
| 2 | 规范对齐：所有 spec 需求都有对应任务 | 通过 |
| 3 | 任务分解：每个任务能在 10 分钟内完成 | 通过 |
| 4 | 可构建性：文件路径明确、详情足够 | 通过 |
| 5 | 验收标准覆盖：18 条验收标准全部对应 | 通过 |
| 6 | 明确性：每个任务有路径、详情、验证 | 通过 |
| 7 | 可验证性：验证步骤可执行 | 通过 |
| 8 | 顺序合理性：实现+测试成对相邻，基础优先 | 通过 |
