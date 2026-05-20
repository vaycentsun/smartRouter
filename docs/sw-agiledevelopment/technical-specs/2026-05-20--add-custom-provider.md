# 添加自定义 Provider 与 Model - 技术规范

## 设计概述

在 Dashboard `/models` 页面通过两个新增 Modal（`AddProviderModal`、`AddModelModal`）提供可视化添加能力。后端通过 `dashboard_api.py` 暴露两个 FastAPI 接口，由 `ConfigLoader` 负责 YAML 文件的追加写入、备份与回滚。整体遵循现有前后端交互模式（Zustand + Axios + FastAPI + YAML）。

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (/models)                    │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │ProviderSidebar│      │ProviderModels│      │ModelsExplorer│
│  │  + "+ Add"    │      │  Panel       │      │  (state   │ │
│  │    button     │      │  + "+ Add"   │      │   mgmt)   │ │
│  └──────┬────────┘      └──────┬───────┘      └─────┬─────┘ │
│         │                      │                    │       │
│  ┌──────▼────────┐      ┌──────▼───────┐            │       │
│  │ AddProvider   │      │ AddModelModal│            │       │
│  │    Modal      │      │              │            │       │
│  └──────┬────────┘      └──────┬───────┘            │       │
│         │                      │                    │       │
│         └──────────────┬───────┘                    │       │
│                        │                            │       │
│              ┌─────────▼──────────┐                 │       │
│              │ useDashboardStore  │                 │       │
│              │ createProvider()   │                 │       │
│              │ addModel()         │                 │       │
│              └─────────┬──────────┘                 │       │
│                        │                            │       │
│              ┌─────────▼──────────┐                 │       │
│              │   api/client.ts    │                 │       │
│              │ createProvider()   │                 │       │
│              │ addModel()         │                 │       │
│              └─────────┬──────────┘                 │       │
└────────────────────────┼────────────────────────────┼───────┘
                         │                            │
                    POST /api/providers         POST /api/providers/{name}/models
                         │                            │
┌────────────────────────┼────────────────────────────┼───────┐
│                        │      Backend (FastAPI)     │       │
│              ┌─────────▼──────────┐    ┌────────────▼─────┐ │
│              │ create_provider()  │    │   add_model()    │ │
│              │   (handler)        │    │    (handler)     │ │
│              └─────────┬──────────┘    └────────┬─────────┘ │
│                        │                        │           │
│              ┌─────────▼────────────────────────▼─────┐     │
│              │           ConfigLoader                 │     │
│              │ create_provider()  │  add_model()      │     │
│              │ validate()         │  validate()       │     │
│              │ save_providers()   │  (custom write)   │     │
│              └─────────┬────────────────────────┬─────┘     │
│                        │                        │           │
│              ┌─────────▼────────┐    ┌──────────▼────────┐  │
│              │  providers.yaml  │    │ models/{name}.yaml│  │
│              │  (append)        │    │  (append/create)  │  │
│              └──────────────────┘    └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 组件设计

### 前端组件

#### AddProviderModal

**Props:**
```typescript
interface AddProviderModalProps {
  isOpen: boolean
  onClose: () => void
}
```

**内部状态:**
```typescript
interface ProviderFormState {
  name: string
  api_base: string
  api_key: string
  timeout: number
}
```

**行为:**
- 表单提交时调用 `useDashboardStore().createProvider(data)`。
- 成功关闭 Modal 并清空表单；失败显示错误提示（不关闭）。
- 前端校验：`name` 非空、`api_base` 非空且为合法 URL、`timeout` 为 1-300 的整数。

#### AddModelModal

**Props:**
```typescript
interface AddModelModalProps {
  providerName: string
  isOpen: boolean
  onClose: () => void
}
```

**内部状态:**
```typescript
interface ModelFormState {
  name: string
  litellm_model: string
  quality: number
  cost: number
  context: number
  supported_tasks: string[]
  enabled: boolean
}
```

**行为:**
- 表单提交时调用 `useDashboardStore().addModel(providerName, data)`。
- 成功关闭 Modal；失败显示错误提示。
- 前端校验：`name` 非空、`litellm_model` 非空、`quality/cost` 为 1-10 的整数、`context` 为正整数、`supported_tasks` 至少一项。

#### ProviderSidebar 修改点

在组件顶部（`NO PROVIDERS` 分支之外）增加一个固定按钮：
- 位置：在 provider 列表上方，与标题同行或独立一行。
- 样式：`tech-btn tech-btn-primary`，文本 "+ Add Provider"。
- 点击：触发 `ModelsExplorer` 中管理的 `addProviderModalOpen` 状态。

#### ProviderModelsPanel 修改点

在头部区域（`EDIT` 按钮旁）增加一个按钮：
- 样式：`tech-btn tech-btn-primary`，文本 "+ Add Model"。
- 仅在 `provider` 非 null 时显示。
- 点击：触发 `ModelsExplorer` 中管理的 `addModelModalOpen` 状态。

#### ModelsExplorer 修改点

新增两个 state：
```typescript
const [addProviderOpen, setAddProviderOpen] = useState(false)
const [addModelOpen, setAddModelOpen] = useState(false)
```

渲染新增的两个 Modal 组件。

#### useDashboardStore 新增 Action

```typescript
createProvider: async (data: CreateProviderRequest) => {
  set({ isSavingProviders: true, error: null, toast: null })
  try {
    const result = await api.createProvider(data)
    if (result.success) {
      set({ toast: { message: 'Provider 已创建', type: 'success' } })
      await get().fetchAll()
    } else {
      set({ error: result.error || '创建失败', toast: { message: result.error || '创建失败', type: 'error' } })
    }
  } catch (err) {
    const msg = (err as Error).message
    set({ error: msg, toast: { message: msg, type: 'error' } })
  } finally {
    set({ isSavingProviders: false })
  }
}

addModel: async (providerName: string, data: AddModelRequest) => {
  set({ isLoading: true, error: null, toast: null })
  try {
    const result = await api.addModel(providerName, data)
    if (result.success) {
      set({ toast: { message: 'Model 已添加', type: 'success' } })
      await get().fetchAll()
    } else {
      set({ error: result.error || '添加失败', toast: { message: result.error || '添加失败', type: 'error' } })
    }
  } catch (err) {
    const msg = (err as Error).message
    set({ error: msg, toast: { message: msg, type: 'error' } })
  } finally {
    set({ isLoading: false })
  }
}
```

#### api/client.ts 新增方法

```typescript
export const api = {
  // ... 现有方法
  createProvider: (data: { name: string; api_base: string; api_key: string; timeout: number }) =>
    client.post<{ success: boolean; provider: ProviderInfo; error?: string }>('/api/providers', data).then((r) => r.data),
  addModel: (providerName: string, data: { name: string; litellm_model: string; quality: number; cost: number; context: number; supported_tasks: string[]; enabled?: boolean }) =>
    client.post<{ success: boolean; model: ModelInfo; error?: string }>(`/api/providers/${providerName}/models`, data).then((r) => r.data),
}
```

### 后端组件

#### dashboard_api.py 新增 Handler

```python
class CreateProviderRequest(BaseModel):
    name: str
    api_base: str
    api_key: str
    timeout: int = 30

class AddModelRequest(BaseModel):
    name: str
    litellm_model: str
    quality: int
    cost: int
    context: int
    supported_tasks: list[str]
    enabled: bool = True
```

**create_provider handler:**
1. 读取当前 `providers.yaml`。
2. 校验 `name` 是否已存在（全局唯一）→ 存在则返回 `400`。
3. 校验 `name` 格式（合法 YAML 键名，不允许空格、冒号等）→ 非法则返回 `400`。
4. 构造 provider 节点：`{ "api_base": ..., "api_key": ..., "timeout": ... }`。
5. 调用 `loader.create_provider(name, ...)` 写入。
6. 返回 `{ "success": True, "provider": <ProviderInfo> }`。

**add_model handler:**
1. 读取当前配置验证 `provider_name` 存在 → 不存在返回 `404`。
2. 校验 `name` 是否已存在于全局 `cfg.models` → 存在返回 `400`。
3. 校验 `name` 格式（合法 YAML 键名）。
4. 构造 model 节点（符合 `schema.py` 的 `ModelConfig` 结构）。
5. 调用 `loader.add_model(provider_name, name, ...)` 写入。
6. 返回 `{ "success": True, "model": <ModelInfo> }`。

#### ConfigLoader 新增方法

**create_provider:**
```python
def create_provider(self, name: str, api_base: str, api_key: str, timeout: int = 30) -> None:
    filepath = self.config_dir / "providers.yaml"
    
    # 读取现有
    current = self._load_yaml("providers.yaml")
    providers = current.get("providers", {})
    
    if name in providers:
        raise ConfigError(f"Provider '{name}' already exists")
    
    providers[name] = {
        "api_base": api_base,
        "api_key": api_key,
        "timeout": timeout,
    }
    
    self.save_providers(providers)
```

**add_model:**
```python
def add_model(self, provider_name: str, name: str, litellm_model: str, 
              quality: int, cost: int, context: int, 
              supported_tasks: list[str], enabled: bool = True) -> None:
    # 先验证整体配置中 model name 是否唯一
    cfg = self.load()
    if name in cfg.models:
        raise ConfigError(f"Model '{name}' already exists")
    
    filepath = self.config_dir / "models" / f"{provider_name}.yaml"
    
    # 读取或创建
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {"models": {}}
    
    models = data.get("models", {})
    
    models[name] = {
        "provider": provider_name,
        "litellm_model": litellm_model,
        "capabilities": {
            "quality": quality,
            "cost": cost,
            "context": context,
        },
        "supported_tasks": supported_tasks,
        "enabled": enabled,
    }
    
    data["models"] = models
    
    # 备份
    backup_path = filepath.with_suffix(".yaml.bak")
    if filepath.exists():
        try:
            backup_path.write_text(filepath.read_text(encoding="utf-8"), encoding="utf-8")
        except IOError:
            pass
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    except Exception as e:
        raise ConfigError(f"Failed to write {filepath}: {e}") from e
    
    # 验证
    errors = self.validate()
    if errors:
        if backup_path.exists():
            try:
                filepath.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
            except IOError:
                pass
        raise ConfigError(f"Config validation failed after save: {'; '.join(errors)}")
```

## 数据流

### 创建 Provider 数据流

1. 用户点击 "+ Add Provider" → `setAddProviderOpen(true)`。
2. 填写表单 → 点击 Save → `createProvider(formData)`。
3. `api.createProvider` → `POST /api/providers`。
4. FastAPI handler 校验 name 唯一性 → 调用 `ConfigLoader.create_provider`。
5. `create_provider` 读取 `providers.yaml` → 追加节点 → 调用 `save_providers`（自带备份+验证+回滚）。
6. 返回 `200 { success: True, provider: ... }`。
7. `useDashboardStore` 收到成功 → `fetchAll()` 重新拉取状态 → Sidebar 刷新。

### 添加 Model 数据流

1. 用户选中 Provider → 点击 "+ Add Model" → `setAddModelOpen(true)`。
2. 填写表单 → 点击 Save → `addModel(providerName, formData)`。
3. `api.addModel` → `POST /api/providers/{name}/models`。
4. FastAPI handler 校验 provider 存在、model name 全局唯一 → 调用 `ConfigLoader.add_model`。
5. `add_model` 读取或创建 `models/{provider_name}.yaml` → 追加节点 → 写入 → 验证 → 回滚。
6. 返回 `200 { success: True, model: ... }`。
7. `useDashboardStore` 收到成功 → `fetchAll()` → 模型列表刷新。

### 错误回滚数据流

- 若 `save_providers` 或 `add_model` 中写入后 `validate()` 失败：
  - 自动将备份文件写回原路径。
  - 抛出 `ConfigError`。
  - FastAPI handler 捕获并返回 `500 { success: False, error: "Config validation failed: ..." }`。
  - 前端显示 toast 错误，不关闭 Modal，保留用户输入。

## 错误处理

### 前端错误

| 场景 | 处理 |
|------|------|
| 必填字段为空 | 按钮 disabled 或提交时前端提示 |
| timeout 非数字/越界 | 前端校验，提示 "Timeout 范围 1-300" |
| quality/cost 越界 | 前端校验，提示 "范围 1-10" |
| 网络错误 | 显示通用错误 toast |

### 后端错误

| 场景 | HTTP 状态码 | 响应体 |
|------|------------|--------|
| Provider name 已存在 | 400 | `{ success: False, error: "Provider 'x' already exists" }` |
| Model name 已存在 | 400 | `{ success: False, error: "Model 'x' already exists" }` |
| Provider name 格式非法 | 400 | `{ success: False, error: "Invalid provider name: ..." }` |
| Provider 不存在（添加 Model 时）| 404 | `{ success: False, error: "Provider not found: x" }` |
| 配置验证失败 | 500 | `{ success: False, error: "Config validation failed: ..." }` |
| 文件读写失败 | 500 | `{ success: False, error: "Failed to write ..." }` |

## 安全考虑

- **名称注入防护**：Provider name 和 Model name 只允许 `[a-zA-Z0-9_\-]`，禁止空格、冒号、`#` 等 YAML 特殊字符。后端用正则校验：`^[a-zA-Z0-9_\-]+$`。
- **API Key 存储**：与现有行为一致，明文写入 `providers.yaml`（用户知晓并接受）。同时支持 `os.environ/KEY_NAME` 格式，前端若检测到用户输入以此开头，原样传递。
- **路径遍历防护**：`provider_name` 用于拼接文件路径 `models/{provider_name}.yaml`，后端需校验 `provider_name` 不包含 `/` 或 `..`。
- **XSS 防护**：表单内容通过 `yaml.safe_dump` 序列化，自动处理特殊字符转义，无需额外 HTML escape。

## 依赖关系

| 新增/修改组件 | 依赖现有组件 |
|--------------|-------------|
| AddProviderModal | I18nProvider（翻译）、tech-btn / tech-input / tech-card 样式 |
| AddModelModal | I18nProvider、tech-btn / tech-input / tech-card 样式 |
| ProviderSidebar | 现有 props 不变，仅增加 onAddProvider 回调或 ModelsExplorer 直接管理 |
| ProviderModelsPanel | 现有 props 不变，仅增加 onAddModel 回调或 ModelsExplorer 直接管理 |
| useDashboardStore | 依赖 api.client.ts |
| api.client.ts | 依赖 axios |
| dashboard_api.py create_provider | 依赖 ConfigLoader、ProviderInfo schema |
| dashboard_api.py add_model | 依赖 ConfigLoader、ModelInfo schema |
| ConfigLoader.create_provider | 依赖 _load_yaml、save_providers |
| ConfigLoader.add_model | 依赖 _load_yaml、yaml.safe_dump、validate |

## 兼容性

- **向后兼容**：新增接口和 Modal 不影响现有 Provider 编辑、Model 切换等功能。
- **配置兼容**：新写入的 YAML 结构与现有 `schema.py` 完全一致，`ConfigLoader.load()` 无需修改。
- **API 兼容**：新增路由使用新的 URL 路径，不影响现有路由。

## 验收标准（细化）

- [ ] 在 `/models` 页面点击 "+ Add Provider" 弹出 `AddProviderModal`，包含 name、api_base、api_key、timeout 字段。
- [ ] 创建 Provider 时，name 已存在 → 前端显示错误 toast，Modal 不关闭，输入保留。
- [ ] 创建 Provider 后，`providers.yaml` 新增节点，整体配置通过 `ConfigLoader.validate()`。
- [ ] 创建 Provider 后，左侧 `ProviderSidebar` 立即显示新 Provider。
- [ ] 选中 Provider 后，点击 "+ Add Model" 弹出 `AddModelModal`，包含 name、litellm_model、quality、cost、context、supported_tasks 字段。
- [ ] 添加 Model 时，name 全局已存在 → 前端显示错误 toast，Modal 不关闭。
- [ ] 添加 Model 后，`models/{provider_name}.yaml` 新增节点，整体配置通过验证。
- [ ] 添加 Model 后，右侧模型列表立即显示新 Model。
- [ ] 若写入后验证失败，备份自动恢复，前端收到明确错误提示。
- [ ] 新 Provider 和 Model 能被 `ConfigLoader.load()` 正常加载，出现在 `/api/models` 和 `/api/providers` 响应中。
- [ ] 所有新增组件和修改均有 TypeScript 类型定义。
