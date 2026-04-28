# Smart Router Frontend — AGENTS.md

> Web 管理界面。基于 Vite + TypeScript。供修改 `frontend/` 下代码的 AI 助手阅读。
> AI 对话语言：中文

---

## 技术栈

- **构建工具**: Vite 5+
- **语言**: TypeScript 5+
- **配置**: `vite.config.ts`, `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`
- **Lint**: ESLint (`eslint.config.js`)

---

## 开发命令

```bash
# 安装依赖
npm ci

# 开发服务器（默认端口 5173）
npm run dev

# 构建（产物输出到 frontend/dist/）
npm run build

# 预览生产构建
npm run preview
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
├── src/                    # 源码目录
│   └── (待补充组件结构)
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

## 待补充

- 组件库 / UI 框架选择
- 状态管理方案
- API 调用规范（与后端网关的接口约定）
- 前端测试策略
- 代码风格与目录组织约定
