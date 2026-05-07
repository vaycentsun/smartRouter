# ProviderSidebar 排序设计文档

## 目标
在 Dashboard 「模型清单」页面的 Provider 侧边栏中，将已配置 API Key 的 Provider 排在列表上方，同组内按名称字母升序排列。

## 方案
采用**方案 A**：在 `ProviderSidebar` 组件内部使用 `useMemo` 对 `providers` prop 进行排序。

## 排序规则
1. `has_key === true` 的 Provider 排在 `has_key === false` 之前；
2. 同组内按 `name` 字母升序排列（使用 `localeCompare`）。

## 变更范围
- **文件**：`frontend/src/components/ProviderSidebar.tsx`
- **新增**：一个 `useMemo` 钩子用于生成排序后的 provider 列表。
- **修改**：将渲染逻辑中使用的 `providers` 替换为排序后的数组。

## 影响面
- 仅影响「模型清单」页面的左侧 Provider 列表展示顺序；
- `selectedProvider` 与 `onSelectProvider` 逻辑不受影响；
- 不改动 Dashboard 页面的 `ProvidersTable`，也不改动后端 API 或数据获取逻辑。

## 不在本次范围
- Dashboard 页面的 Provider 表格排序；
- 后端 API 返回顺序的调整；
- 全局状态管理层的排序逻辑。
