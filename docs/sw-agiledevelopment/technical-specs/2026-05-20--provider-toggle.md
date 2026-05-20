# Provider 一键开关 - 技术规范

## 设计概述
在 Provider 配置层级引入 `enabled` 布尔字段，作为该 Provider 下所有模型的"总闸"。前端在 ProviderModelsPanel 顶部提供总开关 UI；后端在 Config Schema、ConfigLoader、V3ModelSelector 及 Dashboard API 中同步支持该字段的读写与过滤逻辑。

## 架构概述

```
前端 (React + Zustand)
  ├── ProviderModelsPanel ── 总开关 UI + 模型列表状态展示
  ├── useDashboardStore ── toggleProvider action
  └── api/client.ts ── PUT /api/providers/{name}/toggle

后端 (Python FastAPI)
  ├── dashboard_api.py ── 新增 toggle_provider 接口
  ├── config/schema.py ── ProviderConfig.enabled (默认 True)
  ├── config/loader.py ── save_provider_enabled 方法
  └── selector/v3_selector.py ── _filter_candidates 增加 Provider enabled 检查
```

数据流：用户点击总开关 → 前端调用批量 toggle API → 后端修改 providers.yaml → 触发热重载 → 路由引擎过滤禁用 Provider 的模型。

## 组件设计

### 1. 前端类型扩展 (`frontend/src/types/index.ts`)

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

### 2. 前端 API 扩展 (`frontend/src/api/client.ts`)

```typescript
toggleProvider: (provider: string, enabled: boolean) =>
  client.put<{ success: boolean; provider: string; enabled: boolean }>(
    `/api/providers/${provider}/toggle`,
    { enabled }
  ).then((r) => r.data),
```

### 3. 前端 Store 扩展 (`frontend/src/store/useDashboardStore.ts`)

新增字段：
```typescript
isTogglingProvider: Record<string, boolean>
```

新增 Action：
```typescript
toggleProvider: async (providerName: string, enabled: boolean) => {
  set((state) => ({ isTogglingProvider: { ...state.isTogglingProvider, [providerName]: true } }))
  try {
    await api.toggleProvider(providerName, enabled)
    set((state) => ({
      providers: state.providers.map((p) =>
        p.name === providerName ? { ...p, enabled } : p
      ),
      // 同步更新 models 的展示状态：Provider 禁用时，其下模型在UI上表现为 disabled
      toast: { message: `Provider ${providerName} 已${enabled ? '启用' : '禁用'}`, type: 'success' },
    }))
  } catch (err) {
    set({ error: (err as Error).message, toast: { message: '操作失败', type: 'error' } })
  } finally {
    set((state) => ({ isTogglingProvider: { ...state.isTogglingProvider, [providerName]: false } }))
  }
}
```

### 4. 前端 UI 变更 (`frontend/src/components/ProviderModelsPanel.tsx`)

- 在 Provider 名称右侧、EDIT 按钮左侧增加总开关（Toggle Switch）
- 总开关样式与现有模型级 ENABLED 开关保持一致
- 总开关状态：`provider.enabled`（后端返回，缺失时默认 true）
- 点击总开关调用 `toggleProvider(provider.name, !provider.enabled)`
- `isTogglingProvider[provider.name]` 为 true 时，总开关置灰并显示 loading
- Provider 禁用时：
  - 下方模型列表的 `getModelHealthDisplay` 返回 DISABLED（Provider disabled）
  - 模型的 ENABLED 单独开关保持可见但 `disabled={true}`， tooltip 提示"Provider 已禁用"

### 5. 后端配置模型扩展 (`core/smart_router/config/schema.py`)

```python
class ProviderConfig(BaseModel):
    api_base: str
    api_key: str
    timeout: int = 30
    default_headers: Dict[str, str] = Field(default_factory=dict)
    rate_limit: Optional[int] = None
    enabled: bool = Field(default=True, description="Provider 是否启用")   # 新增
```

**向后兼容**：`enabled` 默认值为 `True`，旧版 providers.yaml 未包含该字段时自动视为启用。

### 6. 后端配置加载器扩展 (`core/smart_router/config/loader.py`)

新增方法：
```python
def save_provider_enabled(self, provider_name: str, enabled: bool) -> None:
    """保存 Provider 的 enabled 状态到 providers.yaml
    
    使用 ruamel.yaml 保留注释（若可用），否则回退到标准 yaml 写入。
    写入后执行全量验证，验证失败则回滚备份。
    """
    filepath = self.config_dir / "providers.yaml"
    # 备份 → 读取 → 修改 providers[provider_name].enabled → 写入 → 验证
```

实现参考 `save_model` 的备份/回滚/验证模式。

### 7. 后端路由引擎变更 (`core/smart_router/selector/v3_selector.py`)

在 `_filter_candidates` 方法中，模型过滤逻辑增加 Provider enabled 检查：

```python
for name, model in self.config.models.items():
    # ... 现有过滤条件 ...
    
    # 检查模型所属 Provider 是否被禁用
    provider = self.config.providers.get(model.provider)
    if provider and not getattr(provider, 'enabled', True):
        continue
    
    # 检查模型是否被禁用
    if not getattr(model, 'enabled', True):
        continue
    
    candidates.append((name, model))
```

> **注意**：Provider enabled 检查**优先于**模型 enabled 检查。Provider 被禁用时代码直接 `continue`，不进入后续模型级判断。

### 8. 后端 Dashboard API 扩展 (`core/smart_router/gateway/dashboard_api.py`)

#### 8.1 请求/响应模型

```python
class ProviderToggleRequest(BaseModel):
    enabled: bool
```

#### 8.2 新增接口

```python
async def toggle_provider(request: Request, provider_name: str, body: ProviderToggleRequest):
    """切换 Provider 启用/禁用状态

    Args:
        provider_name: Provider 名称
        body: { enabled: bool }

    Returns:
        { "success": True, "provider": str, "enabled": bool }

    Raises:
        HTTPException(404): Provider 不存在
        HTTPException(500): 保存或验证失败
    """
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

    # 触发配置热重载
    router = getattr(request.app.state, "router", None)
    if router and hasattr(router, "reload_config"):
        try:
            router.reload_config()
        except Exception:
            pass

    return {
        "success": True,
        "provider": provider_name,
        "enabled": body.enabled,
    }
```

#### 8.3 修改现有 `providers()` 接口

在返回的 provider dict 中增加 `enabled` 字段：

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

#### 8.4 路由注册

```python
app.put("/api/providers/{provider_name}/toggle")(toggle_provider)
```

### 9. 后端模型健康检查影响

Provider 禁用时，其下模型的健康检查仍然可以执行（`checkProviderHealth` 不检查 enabled），但健康状态在 UI 上被 Provider enabled 状态覆盖显示为 DISABLED。

## 数据流

```
用户点击 Provider 总开关
    │
    ▼
useDashboardStore.toggleProvider(providerName, enabled)
    │
    ▼
PUT /api/providers/{provider_name}/toggle { enabled }
    │
    ▼
dashboard_api.toggle_provider
    ├── ConfigLoader.load() 验证配置
    ├── ConfigLoader.save_provider_enabled() 写入 providers.yaml
    └── router.reload_config() 热重载
    │
    ▼
返回 { success, provider, enabled }
    │
    ▼
Zustand 更新 providers 数组中对应 provider 的 enabled
Zustand 更新 toast 提示
    │
    ▼
ProviderModelsPanel 重新渲染
    ├── 总开关状态更新
    └── 模型列表：getModelHealthDisplay 优先检查 provider.enabled
```

## 错误处理

| 错误场景 | 前端表现 | 后端行为 |
|---------|---------|---------|
| Provider 不存在 | Toast 提示"操作失败" | 404 |
| providers.yaml 写入失败 | Toast 提示"操作失败" | 500，回滚备份 |
| 配置验证失败 | Toast 提示"操作失败" | 500，回滚备份 |
| 热重载失败 | 不影响（操作已成功） | 捕获异常，不阻塞响应 |
| 网络请求失败 | Toast 提示"操作失败" | — |

## 安全考虑

- 输入校验：Pydantic `ProviderToggleRequest` 自动校验 `enabled` 为布尔值
- Provider 存在性校验：写入前通过 `ConfigLoader.load()` 全量验证
- 配置备份：`save_provider_enabled` 执行写入前自动备份 providers.yaml，验证失败回滚

## 测试策略

### 前端测试
- `ProviderModelsPanel.test.tsx`：
  - 总开关渲染和点击行为
  - Provider 禁用时模型列表状态显示
  - Provider 禁用时模型单独开关被禁用
  - loading 状态覆盖

### 后端测试
- `core/smart_router/gateway/tests/test_dashboard_api.py`：
  - `PUT /api/providers/{provider}/toggle` 正常切换
  - 切换不存在 Provider 返回 404
  - 响应包含正确 enabled 值
- `core/smart_router/config/tests/`：
  - `save_provider_enabled` 正确读写 providers.yaml
  - 验证失败时回滚备份
- `core/smart_router/selector/tests/test_v3_selector.py`：
  - `_filter_candidates` 排除 disabled provider 下的模型
  - Provider 启用时模型级 enabled 仍然生效

## 验收标准（细化）

- [ ] `ProviderConfig` Schema 增加 `enabled: bool = True`，向后兼容旧配置
- [ ] `ConfigLoader` 增加 `save_provider_enabled` 方法，支持备份/回滚/验证
- [ ] `V3ModelSelector._filter_candidates` 优先过滤 disabled Provider 的模型
- [ ] Dashboard API `providers()` 返回包含 `enabled` 字段
- [ ] Dashboard API 新增 `PUT /api/providers/{provider_name}/toggle` 接口
- [ ] 前端 `ProviderInfo` 类型增加 `enabled: boolean`
- [ ] 前端 `api/client.ts` 增加 `toggleProvider` 方法
- [ ] 前端 `useDashboardStore` 增加 `toggleProvider` action 和 `isTogglingProvider` 状态
- [ ] `ProviderModelsPanel` 顶部增加总开关，样式与模型开关一致
- [ ] Provider 禁用时，其下所有模型显示为 DISABLED（状态标签灰色）
- [ ] Provider 禁用时，模型单独开关被禁用，tooltip 提示"Provider 已禁用"
- [ ] Provider 恢复启用后，模型按自身原有 enabled 状态恢复显示
- [ ] 禁用 Provider 后，dry-run / playground 不再路由到该 Provider 的模型
- [ ] 前后端对应测试用例通过

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| ruamel.yaml 未安装导致注释丢失 | 低 | 回退到标准 yaml 写入；providers.yaml 通常注释较少 |
| 旧配置无 enabled 字段导致前端 `undefined` | 中 | 前端用 `provider.enabled ?? true` 兜底；后端 Schema 默认值 True |
| 同时修改 providers.yaml 和 models.yaml 的并发写入 | 低 | 当前架构无并发写入场景；loader 的备份机制可部分缓解 |
| Provider 禁用后健康检查仍更新缓存，UI 状态短暂不一致 | 低 | `getModelHealthDisplay` 优先检查 provider.enabled，覆盖健康状态 |
