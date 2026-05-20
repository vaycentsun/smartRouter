# Provider 一键开关 - 实施计划

## 任务概览

| 编号 | 任务 | 文件 | 依赖 |
|------|------|------|------|
| 1 | ProviderConfig 增加 enabled 字段 | `core/smart_router/config/schema.py` | - |
| 2 | ProviderConfig enabled 测试 | `core/smart_router/config/tests/test_schema.py` | 1 |
| 3 | ConfigLoader 增加 save_provider_enabled | `core/smart_router/config/loader.py` | 1 |
| 4 | save_provider_enabled 测试 | `core/smart_router/config/tests/test_loader.py` | 3 |
| 5 | V3ModelSelector 增加 Provider enabled 过滤 | `core/smart_router/selector/v3_selector.py` | 1 |
| 6 | Provider enabled 过滤测试 | `core/smart_router/selector/tests/test_v3_selector.py` | 5 |
| 7 | Dashboard API 新增 toggle_provider | `core/smart_router/gateway/dashboard_api.py` | 3 |
| 8 | toggle_provider API 测试 | `core/smart_router/gateway/tests/test_dashboard_api.py` | 7 |
| 9 | ProviderInfo 类型增加 enabled | `frontend/src/types/index.ts` | - |
| 10 | api/client 增加 toggleProvider | `frontend/src/api/client.ts` | 9 |
| 11 | Store 增加 toggleProvider action | `frontend/src/store/useDashboardStore.ts` | 10 |
| 12 | ProviderModelsPanel 增加总开关 | `frontend/src/components/ProviderModelsPanel.tsx` | 9, 11 |
| 13 | ProviderModelsPanel 总开关测试 | `frontend/src/components/ProviderModelsPanel.test.tsx` | 12 |

---

### 任务 1: ProviderConfig 增加 enabled 字段

**文件**: `core/smart_router/config/schema.py`

**动作**: 在 `ProviderConfig` 类中增加 `enabled: bool = Field(default=True, description="Provider 是否启用")`

**详情**:
```python
class ProviderConfig(BaseModel):
    api_base: str
    api_key: str
    timeout: int = 30
    default_headers: Dict[str, str] = Field(default_factory=dict)
    rate_limit: Optional[int] = None
    enabled: bool = Field(default=True, description="Provider 是否启用")   # 新增
```

**验证**:
- [ ] `ProviderConfig` 可实例化且 `enabled` 默认为 `True`
- [ ] 显式传入 `enabled=False` 后字段值为 `False`
- [ ] 不影响现有 Config 加载测试

**依赖**: 无

---

### 任务 2: ProviderConfig enabled 测试

**文件**: `core/smart_router/config/tests/test_schema.py`

**动作**: 为 ProviderConfig 的 enabled 字段编写/补充测试

**详情**:
- 场景 1: `ProviderConfig(api_base="...", api_key="...")` 的 `enabled` 默认为 `True`
- 场景 2: `ProviderConfig(api_base="...", api_key="...", enabled=False)` 的 `enabled` 为 `False`
- 场景 3: 完整的 `Config` 加载时，缺少 `enabled` 字段的 Provider 默认视为 `True`

**验证**:
- [ ] 测试可运行
- [ ] 未修改代码前，场景 3 通过（向后兼容验证）
- [ ] 全部通过后，schema 层变更完成

**依赖**: 任务 1

---

### 任务 3: ConfigLoader 增加 save_provider_enabled 方法

**文件**: `core/smart_router/config/loader.py`

**动作**: 在 `ConfigLoader` 类中新增 `save_provider_enabled` 方法

**详情**:
参考已有的 `save_model` 方法实现，新增方法：
```python
def save_provider_enabled(self, provider_name: str, enabled: bool) -> None:
    """保存 Provider 的 enabled 状态到 providers.yaml
    
    使用 ruamel.yaml 保留注释（若可用），否则回退到标准 yaml 写入。
    写入后执行全量验证，验证失败则回滚备份。
    """
    filepath = self.config_dir / "providers.yaml"
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

    providers = data.get("providers", {})
    if provider_name not in providers:
        raise ConfigError(f"Provider '{provider_name}' not found in {filepath.name}")

    providers[provider_name]["enabled"] = enabled

    # 尝试使用 ruamel.yaml 保留注释
    try:
        from ruamel.yaml import YAML
        ruamel_yaml = YAML()
        ruamel_yaml.preserve_quotes = True
        ruamel_yaml.width = 4096
        with open(filepath, "r", encoding="utf-8") as f:
            doc = ruamel_yaml.load(f)
        doc["providers"][provider_name]["enabled"] = enabled
        with open(filepath, "w", encoding="utf-8") as f:
            ruamel_yaml.dump(doc, f)
    except Exception:
        # ruamel 失败时回退到标准 yaml
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        except Exception as e:
            raise ConfigError(f"Failed to write {filepath}: {e}") from e

    # 写入后验证
    errors = self.validate()
    if errors:
        if backup_path.exists():
            try:
                filepath.write_text(backup_path.read_text(), encoding="utf-8")
            except IOError:
                pass
        raise ConfigError(f"Config validation failed after save: {'; '.join(errors)}")
```

**验证**:
- [ ] `save_provider_enabled` 方法可被调用
- [ ] 调用后 providers.yaml 中对应 provider 出现 enabled 字段
- [ ] 验证失败时自动回滚备份文件

**依赖**: 任务 1

---

### 任务 4: save_provider_enabled 测试

**文件**: `core/smart_router/config/tests/test_loader.py`

**动作**: 为 `save_provider_enabled` 编写单元测试

**详情**:
- 场景 1: `save_provider_enabled("openai", False)` 正确修改 providers.yaml 中的 enabled 字段为 false
- 场景 2: `save_provider_enabled("openai", True)` 正确修改 providers.yaml 中的 enabled 字段为 true
- 场景 3: `save_provider_enabled("unknown", False)` 抛出 `ConfigError`
- 场景 4: 修改导致验证失败（如删除 providers 节点后调用）时，备份文件被恢复

**验证**:
- [ ] 测试可运行
- [ ] RED（先失败，因为方法尚未实现）
- [ ] 任务 3 完成后重新运行，GREEN

**依赖**: 任务 3

---

### 任务 5: V3ModelSelector 增加 Provider enabled 过滤

**文件**: `core/smart_router/selector/v3_selector.py`

**动作**: 在 `_filter_candidates` 方法中，模型 enabled 检查之前增加 Provider enabled 检查

**详情**:
在 `_filter_candidates` 的循环中，在 `if not getattr(model, 'enabled', True)` 之前插入：
```python
# 检查模型所属 Provider 是否被禁用
provider = self.config.providers.get(model.provider)
if provider and not getattr(provider, 'enabled', True):
    continue
```

**验证**:
- [ ] 代码语法正确
- [ ] 现有 selector 测试不因此变更而失败

**依赖**: 任务 1

---

### 任务 6: Provider enabled 过滤测试

**文件**: `core/smart_router/selector/tests/test_v3_selector.py`

**动作**: 为 `_filter_candidates` 的 Provider enabled 过滤逻辑编写测试

**详情**:
- 场景 1: Provider enabled=False 时，其下所有模型被排除在候选列表外
- 场景 2: Provider enabled=True（或缺失）时，模型按原有 enabled 逻辑过滤
- 场景 3: Provider 禁用时，即使某个模型自身 enabled=True，也不出现在候选列表
- 场景 4: Provider 启用时，模型自身 enabled=False 仍然被排除

**验证**:
- [ ] 测试可运行
- [ ] 任务 5 代码未添加时，场景 1 应该失败（RED）
- [ ] 任务 5 完成后全部通过（GREEN）

**依赖**: 任务 5

---

### 任务 7: Dashboard API 新增 toggle_provider 接口

**文件**: `core/smart_router/gateway/dashboard_api.py`

**动作**: 
1. 新增 `ProviderToggleRequest` Pydantic 模型
2. 新增 `toggle_provider` 接口函数
3. 修改 `providers()` 函数，返回结果中增加 `enabled` 字段
4. 在路由注册处增加 `app.put("/api/providers/{provider_name}/toggle")(toggle_provider)`

**详情**:
```python
class ProviderToggleRequest(BaseModel):
    enabled: bool

async def toggle_provider(request: Request, provider_name: str, body: ProviderToggleRequest):
    config_dir = Path.home() / ".smart-router"
    loader = ConfigLoader(config_dir)
    try:
        cfg = loader.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置加载失败: {e}")
    if provider_name not in cfg.providers:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_name}")
    try:
        loader.save_provider_enabled(provider_name, body.enabled)
    except ConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))
    router = getattr(request.app.state, "router", None)
    if router and hasattr(router, "reload_config"):
        try:
            router.reload_config()
        except Exception:
            pass
    return {"success": True, "provider": provider_name, "enabled": body.enabled}
```

修改 `providers()`：
```python
result.append({
    "name": name,
    "api_base": provider.api_base,
    "timeout": provider.timeout,
    "key_type": key_type,
    "has_key": has_key,
    "masked_key": masked_key,
    "health": health_data,
    "enabled": getattr(provider, 'enabled', True),   # 新增
})
```

**验证**:
- [ ] `ProviderToggleRequest` 可导入
- [ ] `toggle_provider` 可注册到 FastAPI app
- [ ] `providers()` 返回的 JSON 包含 enabled 字段

**依赖**: 任务 3

---

### 任务 8: toggle_provider API 测试

**文件**: `core/smart_router/gateway/tests/test_dashboard_api.py`

**动作**: 为 `PUT /api/providers/{provider}/toggle` 编写集成测试

**详情**:
- 场景 1: 正常切换 Provider enabled=False，返回 200 和正确 JSON
- 场景 2: 正常切换 Provider enabled=True，返回 200 和正确 JSON
- 场景 3: 切换不存在的 Provider，返回 404
- 场景 4: GET /api/providers 返回的列表中包含 enabled 字段且值正确

**验证**:
- [ ] 测试可运行
- [ ] 任务 7 完成前，场景 1 失败（RED）
- [ ] 任务 7 完成后全部通过（GREEN）

**依赖**: 任务 7

---

### 任务 9: ProviderInfo 类型增加 enabled

**文件**: `frontend/src/types/index.ts`

**动作**: 在 `ProviderInfo` 接口中增加 `enabled: boolean`

**详情**:
```typescript
export interface ProviderInfo {
  name: string
  api_base: string
  timeout: number
  key_type: string
  has_key: boolean
  masked_key?: string
  health?: ProviderHealth
  enabled: boolean          // 新增
}
```

**验证**:
- [ ] TypeScript 编译通过
- [ ] 无类型错误

**依赖**: 无

---

### 任务 10: api/client 增加 toggleProvider

**文件**: `frontend/src/api/client.ts`

**动作**: 在 `api` 对象中增加 `toggleProvider` 方法

**详情**:
```typescript
toggleProvider: (provider: string, enabled: boolean) =>
  client.put<{ success: boolean; provider: string; enabled: boolean }>(
    `/api/providers/${provider}/toggle`,
    { enabled }
  ).then((r) => r.data),
```

**验证**:
- [ ] TypeScript 编译通过
- [ ] `api.toggleProvider` 可被调用

**依赖**: 任务 9

---

### 任务 11: Store 增加 toggleProvider action

**文件**: `frontend/src/store/useDashboardStore.ts`

**动作**: 
1. 在 `DashboardState` 接口中增加 `isTogglingProvider: Record<string, boolean>`
2. 在 `create<DashboardState>` 初始状态中增加 `isTogglingProvider: {}`
3. 增加 `toggleProvider` action

**详情**:
```typescript
// State 扩展
isTogglingProvider: Record<string, boolean>

// Actions 扩展
toggleProvider: (providerName: string, enabled: boolean) => Promise<void>

// 初始值
isTogglingProvider: {}

// Action 实现
toggleProvider: async (providerName, enabled) => {
  set((state) => ({ isTogglingProvider: { ...state.isTogglingProvider, [providerName]: true } }))
  try {
    await api.toggleProvider(providerName, enabled)
    set((state) => ({
      providers: state.providers.map((p) =>
        p.name === providerName ? { ...p, enabled } : p
      ),
      toast: { message: `Provider ${providerName} 已${enabled ? '启用' : '禁用'}`, type: 'success' },
    }))
  } catch (err) {
    set({ error: (err as Error).message, toast: { message: '操作失败', type: 'error' } })
  } finally {
    set((state) => ({ isTogglingProvider: { ...state.isTogglingProvider, [providerName]: false } }))
  }
}
```

**验证**:
- [ ] TypeScript 编译通过
- [ ] Store 初始化后包含 `isTogglingProvider` 和 `toggleProvider`

**依赖**: 任务 10

---

### 任务 12: ProviderModelsPanel 增加总开关

**文件**: `frontend/src/components/ProviderModelsPanel.tsx`

**动作**: 
1. 从 store 读取 `toggleProvider` 和 `isTogglingProvider`
2. 在 Provider 名称区域（EDIT 按钮左侧）增加总开关 UI
3. 修改 `getModelHealthDisplay`，Provider 禁用时返回 DISABLED（Provider disabled）
4. Provider 禁用时，模型单独开关 disabled 并显示 tooltip

**详情**:
- 总开关代码（放置在 EDIT 按钮左侧）：
```tsx
const toggleProvider = useDashboardStore((state) => state.toggleProvider)
const isTogglingProvider = useDashboardStore((state) => state.isTogglingProvider)
const providerToggling = isTogglingProvider[provider.name] || false
```

- 在 header flex 区域插入开关组件：
```tsx
<label className="relative inline-flex items-center cursor-pointer mr-2">
  <input
    type="checkbox"
    className="sr-only peer"
    checked={provider.enabled}
    onChange={() => toggleProvider(provider.name, !provider.enabled)}
    disabled={providerToggling}
  />
  <div className={`w-9 h-5 rounded-sm peer relative border transition-all ${provider.enabled ? 'bg-[rgba(0,212,170,0.15)] border-[rgba(0,212,170,0.3)]' : 'bg-[#1a1a2e] border-[#2a2a3e]'} ${providerToggling ? 'opacity-50' : ''}`}>
    <div className={`absolute top-[2px] left-[2px] w-4 h-4 rounded-sm transition-all ${provider.enabled ? 'translate-x-4 bg-[#00d4aa]' : 'bg-[#636366]'}`} />
  </div>
</label>
```

- 修改 `getModelHealthDisplay`：
```typescript
function getModelHealthDisplay(model: ModelInfo, provider?: ProviderInfo, providerHealth?: { status: string; error?: string | null }) {
  // Provider 级别总闸优先
  if (provider && !provider.enabled) {
    return { label: 'DISABLED', color: 'text-[#636366]', dotColor: 'bg-[#636366]', tooltip: 'Provider disabled by user' }
  }
  // ... 原有逻辑不变
}
```

- 修改模型行中的 ENABLED 开关：
```tsx
<label className="relative inline-flex items-center cursor-pointer" title={!provider.enabled ? 'Provider 已禁用' : ''}>
  <input
    type="checkbox"
    className="sr-only peer"
    checked={model.enabled}
    onChange={() => toggleModel(model.provider, model.name, !model.enabled)}
    disabled={isToggling || !provider.enabled}
  />
  {/* ... 开关样式 ... */}
</label>
```

**验证**:
- [ ] 页面渲染正常，总开关可见
- [ ] 点击总开关触发 API 调用
- [ ] Provider 禁用时所有模型显示 DISABLED
- [ ] Provider 禁用时模型单独开关不可点击

**依赖**: 任务 9, 11

---

### 任务 13: ProviderModelsPanel 总开关测试

**文件**: `frontend/src/components/ProviderModelsPanel.test.tsx`

**动作**: 为总开关 UI 和交互编写测试

**详情**:
- 场景 1: Provider enabled=true 时，总开关处于开启状态
- 场景 2: Provider enabled=false 时，总开关处于关闭状态
- 场景 3: 点击总开关触发 `toggleProvider` 调用
- 场景 4: Provider enabled=false 时，模型列表中模型状态显示 DISABLED
- 场景 5: Provider enabled=false 时，模型的 ENABLED 单独开关被 disabled
- 场景 6: Provider enabled=true 时，模型按自身 enabled 状态正常显示和交互

**验证**:
- [ ] 测试可运行
- [ ] 任务 12 完成前，场景 3/4/5 可能因 UI 缺失而失败（RED）
- [ ] 任务 12 完成后全部通过（GREEN）

**依赖**: 任务 12

---

## 深度自检清单

| # | 检查项 | 状态 |
|---|--------|------|
| 1 | **完整性** — 无待办、无占位符 | ✅ 通过 |
| 2 | **规范对齐** — 所有 technical-spec 组件都有对应任务 | ✅ 通过 |
| 3 | **任务分解** — 每个任务边界清晰，能在 10 分钟内完成 | ✅ 通过 |
| 4 | **可构建性** — 文件路径明确，详情足够实现 | ✅ 通过 |
| 5 | **验收标准覆盖** — 13 条验收标准均有对应验证任务 | ✅ 通过 |
| 6 | **明确性** — 每个任务有确切路径、详情、验证步骤 | ✅ 通过 |
| 7 | **可验证性** — 验证步骤可执行、可判断通过/失败 | ✅ 通过 |
| 8 | **顺序合理性** — 依赖正确，实现+测试成对相邻，基础优先 | ✅ 通过 |

---

## 备注

- **向后兼容**: `ProviderConfig.enabled` 默认值为 `True`，旧配置无需手动迁移。
- **前端默认值**: 后端旧版本未返回 enabled 时，前端可用 `provider.enabled ?? true` 兜底。
- **配置热重载**: `toggle_provider` API 和 `save_provider_enabled` 均复用现有热重载机制，无需额外改动。
