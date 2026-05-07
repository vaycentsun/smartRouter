# Dashboard Tab 导航与模型清单页设计

> **日期**: 2026-04-28
> **范围**: frontend/ 目录
> **作者**: AI Assistant

---

## 1. 需求概述

在 Smart Router Dashboard 中引入 **Tab 导航**，将现有单页内容拆分为两个 Tab：

- **仪表盘 (Dashboard)**: 精简版，保留 `StatsOverview`、`StatusCard`、`DryRunPanel`
- **模型清单 (Models)**: 全新的 Master-Detail 页面，左侧为 Provider 列表（含配置摘要），右侧为该 Provider 的模型列表

---

## 2. 架构设计

采用 **App 内状态切换**（无路由库），理由：
- 现有代码无路由依赖，引入路由需修改构建配置与后端 SPA fallback
- Tab 切换是页面级视图管理，非深层导航需求
- URL 不变是可接受的（Dashboard 为内部管理面板）

核心状态：
- `App.tsx` 管理 `activeTab: 'dashboard' | 'models'`
- `useDashboardStore` 保留全局数据（status, models, providers），两个 Tab 共享同一套数据
- `ModelsExplorer` 组件内部管理 `selectedProvider: string | null`

---

## 3. 组件结构

### 3.1 现有组件调整

| 组件 | 变更 |
|------|------|
| `App.tsx` | 增加 Tab 栏 + 条件渲染页面内容；移除 `ProvidersTable`、`ModelsTable` 的直接引用 |
| `useDashboardStore.ts` | 无变更，数据层复用 |
| `api/client.ts` | 无变更 |
| `StatsOverview.tsx` | 无变更 |
| `StatusCard.tsx` | 无变更 |
| `DryRunPanel.tsx` | 无变更 |
| `ProvidersTable.tsx` | 暂时保留在文件系统中，但不再被 `App.tsx` 直接引用（后续可删除或作为备用） |
| `ModelsTable.tsx` | 暂时保留在文件系统中，但不再被 `App.tsx` 直接引用 |

### 3.2 新建组件

| 组件 | 职责 |
|------|------|
| `DashboardPage.tsx` | 仪表盘 Tab 内容容器，组合 `StatsOverview` + `StatusCard` + `DryRunPanel` |
| `ModelsExplorer.tsx` | 模型清单 Tab 内容容器，管理左右分栏布局与 `selectedProvider` 状态 |
| `ProviderSidebar.tsx` | 左侧边栏：Provider 列表卡片，展示名称、api_base、key 状态、模型数量 |
| `ProviderModelsPanel.tsx` | 右侧面板：选中 Provider 的模型列表表格（从 `ModelsTable` 复用渲染逻辑） |
| `ProviderEditModal.tsx` | 弹窗：编辑 Provider 配置（api_base、api_key、timeout），复用 `ProvidersTable` 的编辑逻辑 |
| `TabNav.tsx` | Tab 导航栏（可选内联在 App.tsx 中，若复杂则独立组件） |

---

## 4. 布局设计

### 4.1 Tab 导航栏

位置：`Header` 下方，`main` 容器顶部。

样式：
- 背景：`glass-card` 风格（毛玻璃 + 白色半透明）
- Tab 项：圆角 pill 形状，选中时 `bg-[rgba(0,122,255,0.08)] text-[#007AFF]`
- 过渡：`transition-all duration-200`
- 内容：两个 Tab 项，带图标（仪表盘图标 + 列表图标）

### 4.2 仪表盘页 (DashboardPage)

与现有 `App.tsx` 中 `main` 内的上半部分完全一致：
```
StatsOverview (3 列网格)
StatusCard (左 1/3) + DryRunPanel (右 2/3)
```

### 4.3 模型清单页 (ModelsExplorer)

左右分栏：
```
grid grid-cols-1 lg:grid-cols-3 gap-6
├── ProviderSidebar (lg:col-span-1)
│   └── Provider 卡片列表（垂直堆叠）
│       ├── 名称 + 状态圆点
│       ├── api_base（截断显示）
│       ├── Key 状态标签
│       └── 模型数量徽章
└── ProviderModelsPanel (lg:col-span-2)
    ├── 顶部：Provider 标题 + 编辑配置按钮
    └── 模型表格（复用 ModelsTable 渲染逻辑）
        ├── 名称、可用状态、Quality、Cost、Context、支持任务
        └── 空状态：该 Provider 暂无模型
```

---

## 5. 交互设计

### 5.1 Tab 切换
- 点击 Tab 项 → `activeTab` 状态变更 → 条件渲染对应页面
- 切换时保持全局数据（status, models, providers）不变，不触发额外请求

### 5.2 Provider 选择
- 点击左侧 `ProviderSidebar` 中的卡片 → `selectedProvider` 更新
- 首次进入 Models Tab 时，默认选中第一个 Provider（若 providers 数组非空）
- 右侧面板根据 `selectedProvider` 过滤 `models` 数组并渲染

### 5.3 Provider 配置编辑
- 点击右侧面板「编辑配置」按钮 → 打开 `ProviderEditModal`
- Modal 内展示表单：api_base (input)、api_key (password input + 显示/隐藏切换)、timeout (number input)
- 保存时调用 `useDashboardStore.saveProviders()`
- 保存成功后关闭 Modal，Toast 提示

### 5.4 数据刷新
- 保留现有的 5 秒自动刷新机制（在 `App.tsx` 的 useEffect 中）
- 两个 Tab 共享同一套自动刷新数据

---

## 6. 数据流

```
App.tsx (activeTab)
  ├── DashboardPage (纯展示，消费 store)
  └── ModelsExplorer (selectedProvider)
        ├── ProviderSidebar (props: providers, selectedProvider, onSelect)
        ├── ProviderModelsPanel (props: provider, models, onEdit)
        └── ProviderEditModal (props: provider, isOpen, onClose)
              └── 提交到 useDashboardStore.saveProviders()
```

---

## 7. 视觉风格

延续现有 Apple-like 设计语言：
- `glass-card`: 背景白色半透明 + backdrop-blur + 细微边框
- 色彩：蓝色 `#007AFF` 为主色调，绿色 `#34C759` 表示在线，红色 `#FF3B30` 表示错误/离线
- 字体：系统字体栈，标题 semibold，标签 uppercase tracking-wider
- 阴影与悬停：微妙的 hover shadow 和 transition

---

## 8. 边界情况

- **无 Provider 数据**: `ProviderSidebar` 展示空状态提示
- **无模型数据**: `ProviderModelsPanel` 展示空状态提示
- **选中 Provider 被删除/改名**: 若当前选中的 Provider 在刷新后不存在，自动回退到第一个 Provider
- **编辑中 Provider 数据刷新**: 编辑弹窗保持打开，内部状态独立，保存时以弹窗内数据为准

---

## 9. 测试策略

- `App.test.tsx`: 更新测试，验证 Tab 切换渲染正确的子组件
- `ModelsExplorer.test.tsx`: 新建测试，验证 Provider 选择、模型过滤、编辑弹窗打开
- `ProviderSidebar.test.tsx`: 新建测试，验证列表渲染、点击选中
- `ProviderModelsPanel.test.tsx`: 新建测试，验证模型表格渲染、空状态
- `ProviderEditModal.test.tsx`: 新建测试，验证表单提交、关闭行为

---

## 10. 相关文件

- `frontend/src/App.tsx`
- `frontend/src/components/DashboardPage.tsx` (新建)
- `frontend/src/components/ModelsExplorer.tsx` (新建)
- `frontend/src/components/ProviderSidebar.tsx` (新建)
- `frontend/src/components/ProviderModelsPanel.tsx` (新建)
- `frontend/src/components/ProviderEditModal.tsx` (新建)
- `frontend/src/store/useDashboardStore.ts` (无变更)
- `frontend/src/types/index.ts` (无变更)
- `frontend/src/api/client.ts` (无变更)
