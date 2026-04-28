# ProviderSidebar 排序实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在模型清单页面的 ProviderSidebar 中，将已配置 key 的 Provider 排在上方，同组内按名称字母升序排列。

**Architecture:** 在 ProviderSidebar 组件内使用 `useMemo` 对 `providers` 进行本地排序，不影响其他组件或全局状态。

**Tech Stack:** React, TypeScript

---

### Task 1: ProviderSidebar 排序逻辑

**Files:**
- Modify: `frontend/src/components/ProviderSidebar.tsx`

- [ ] **Step 1: 添加 `useMemo` 导入**

在文件顶部添加：
```tsx
import { useMemo } from 'react'
```

- [ ] **Step 2: 实现排序逻辑**

在组件内部、`return` 之前添加：
```tsx
const sortedProviders = useMemo(() => {
  return [...providers].sort((a, b) => {
    if (a.has_key !== b.has_key) {
      return a.has_key ? -1 : 1
    }
    return a.name.localeCompare(b.name)
  })
}, [providers])
```

- [ ] **Step 3: 替换渲染用的数组**

将 `providers.map((provider) => {` 改为 `sortedProviders.map((provider) => {`

- [ ] **Step 4: 本地验证**

运行：
```bash
cd frontend && npm run build
```
确保无 TypeScript 编译错误。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/ProviderSidebar.tsx
git commit -m "feat: 模型清单 Provider 侧边栏按 key 配置状态排序"
```
