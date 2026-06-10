# Smart Router Frontend — AGENTS.md

> Web 管理界面。基于 Vite + TypeScript。供修改 `frontend/` 下代码的 AI 助手阅读。
> AI 对话语言：中文
>
> **LSP**: TypeScript (tsserver), ESLint
> **项目类型**: React + TypeScript
> **构建工具**: Vite

## UI 风格参考

本项目 UI 风格遵循项目根目录下的 [`DESIGN.md`](../DESIGN.md) 规范。所有前端界面开发（颜色、排版、布局、组件样式等）均需以该文档为基准，保持与 Smart Router 品牌视觉体系一致。

---

## 技术栈

- **构建工具**: Vite 5+
- **框架**: React 18+ + TypeScript 5+
- **路由**: wouter (轻量级 hooks 路由)
- **状态管理**: Zustand (`src/store/useDashboardStore.ts`)
- **图表**: Recharts
- **样式**: Tailwind CSS
- **配置**: `vite.config.ts`, `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`
- **Lint**: ESLint (`eslint.config.js`)
- **测试**: Vitest + React Testing Library (当前 115 个测试失败，需修复)

---

## 开发命令

```bash
# 安装依赖
npm ci

# 开发服务器（默认端口 5173）
npm run dev

# 类型检查
./node_modules/.bin/tsc --noEmit

# Lint 检查
./node_modules/.bin/eslint .

# 构建（产物输出到 frontend/dist/）
npm run build

# 预览生产构建
npm run preview

# 运行测试
npm test
```

---

## 目录结构

```
frontend/
├── index.html              # 入口 HTML
├── vite.config.ts          # Vite 配置
├── package.json            # 依赖与脚本
├── eslint.config.js        # ESLint 配置
├── tsconfig*.json          # TypeScript 配置
├── src/
│   ├── main.tsx            # React 入口
│   ├── App.tsx             # 根组件（含路由定义）
│   ├── client.ts           # HTTP 客户端封装
│   ├── store/
│   │   └── useDashboardStore.ts  # Zustand 全局状态
│   ├── i18n/
│   │   ├── I18nContext.tsx       # React Context
│   │   └── useTranslation.ts     # useTranslation Hook
│   └── components/         # 页面组件
│       ├── DashboardPage.tsx
│       ├── ModelsExplorer.tsx
│       ├── AnalyticsPage.tsx    # (懒加载，含 Recharts)
│       ├── FormulaBuilder.tsx
│       ├── ModelMappingTab.tsx
│       ├── LogsPanel.tsx
│       ├── AlertsPage.tsx
│       ├── Header.tsx
│       ├── ModelOverrideBar.tsx
│       ├── TopModelsTable.tsx
│       ├── TokenStatsTable.tsx
│       ├── SummaryCards.tsx
│       ├── CostTrendChart.tsx
│       ├── RequestTrendChart.tsx
│       ├── ModelUsageChart.tsx
│       ├── RecentRequestsPanel.tsx
│       ├── ProvidersTable.tsx
│       ├── ProviderEditModal.tsx
│       └── AddProviderModal.tsx
├── public/                 # 静态资源（不经过构建）
└── dist/                   # 构建产物（gitignore）
```

---

## 与 Core 的耦合

- **产物去向**：`npm run build` 生成 `frontend/dist/`，随后由根目录 `make build-web` 复制到 `core/smart_router/web/static/`。
- **不要**在 `core/smart_router/web/static/` 中直接开发；所有前端源码修改应在 `frontend/src/` 进行。
- 若修改了前端路由模式（如从 hash 改为 history），需同步检查后端 `gateway/server.py` 的 SPA fallback 处理。
- 发布 wheel 时，Python 构建系统通过 `tool.hatch.build.targets.wheel.include` 将 `core/smart_router/web/static/` 打包进安装包。

---

## 已知问题

| 问题 | 位置 | 优先级 |
|------|------|--------|
| 115 个测试失败 | `*.test.tsx` | 中 |
| `AnalyticsPage` 已改为 lazy loading | `App.tsx` | 已优化 |
| `I18nContext` + `useTranslation` 分离 | `src/i18n/` | 已优化 |

---

## 代码规范

- **Fast Refresh**: 禁止在组件文件内同时 export 非组件（如 `export const useTranslation`），需分离到独立文件
- **Hooks 规则**: `setState` 不可在 `useEffect` 初始化阶段调用；`useMemo` 优于 `useEffect+setState`
- **类型安全**: `catch (err)` 使用 `unknown` 而非 `any`，配合类型守卫 `if (err instanceof Error)`
