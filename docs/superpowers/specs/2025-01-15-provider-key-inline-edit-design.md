# Provider 模型清单页面 Key 内联编辑设计

**日期**: 2025-01-15
**需求来源**: 用户希望在 dashboard 的"模型清单"tab 中直接查看和修改每个 provider 配置的 API Key

---

## 背景

当前 Smart Router Dashboard 的"模型清单"页面（ModelsExplorer）采用左右布局：左侧 ProviderSidebar 列出所有 provider，右侧 ProviderModelsPanel 展示选中 provider 的模型列表。用户只能通过点击"编辑配置"按钮打开 ProviderEditModal 弹窗来修改 API Key，流程不够快捷。

## 目标

在 ProviderModelsPanel 的模型列表上方增加一个 API Key 的展示与内联编辑区域：
- 显示当前 key 的状态（已配置的掩码值 / 未设置）
- 支持直接修改 key，保存后立即生效
- 留空表示删除 key（后端将 api_key 设为空字符串，provider 变为不可用）
- 环境变量引用的 key（`env:xxx`）只读显示，不可编辑

## 架构设计

### 组件变更

| 组件 | 变更类型 | 说明 |
|------|---------|------|
| `ProviderModelsPanel.tsx` | 修改 | 新增 key 编辑行 UI，新增 `onSaveKey` / `isSaving` props |
| `ModelsExplorer.tsx` | 修改 | 新增 `handleSaveKey` 方法，传递给 ProviderModelsPanel |
| `ProviderModelsPanel.test.tsx` | 修改 | 补充 key 编辑区域的测试用例 |

### UI 布局

```
┌─ ProviderModelsPanel (glass-card) ───────────────────┐
│  Header: Provider名称          [编辑配置]              │
├───────────────────────────────────────────────────────┤
│  Key编辑行:                                            │
│  🔒 API Key: sk-***xxxx  [•••••••] [👁] [保存]        │
├───────────────────────────────────────────────────────┤
│  模型列表表格...                                       │
└───────────────────────────────────────────────────────┘
```

### 数据流

```
用户输入 → ProviderModelsPanel 本地 state (keyInput)
点击保存 → onSaveKey(apiKey) → ModelsExplorer.handleSaveKey
→ api.putProviders({ [name]: { api_key: apiKey } })
→ 后端更新 providers.yaml → success → fetchAll() 刷新
```

### 关键行为

1. **初始化**: 组件挂载时，将 `provider.masked_key` 作为 placeholder，输入框初始为空
2. **明文切换**: 眼睛图标切换 `type="text" / "password"`
3. **保存逻辑**:
   - 输入框非空 → 传新值给后端覆盖
   - 输入框为空 → 传空字符串 `''`，后端设 `api_key: ""`（效果等同删除）
4. **env 类型**: `key_type.startsWith('env:')` 时显示只读文本 "通过环境变量配置"，不显示输入框
5. **保存中**: 按钮禁用，显示 "保存中..."

## 后端兼容性

当前后端 `PUT /api/providers` 逻辑：
- `api_key` 字段为 `Optional[str]`，传 `''` 会将其设为空字符串
- 不传 `api_base` / `timeout` 则不会覆盖现有值

无需后端改动即可满足需求。

## 测试计划

- [ ] 已设置 key：显示 `masked_key`，输入框可操作，保存触发 onSaveKey
- [ ] 未设置 key：显示 "未设置"，输入框 placeholder 正确
- [ ] 清空保存：onSaveKey('') 被调用，表示删除 key
- [ ] env 类型：显示只读提示，无输入框
- [ ] 保存中状态：按钮禁用
