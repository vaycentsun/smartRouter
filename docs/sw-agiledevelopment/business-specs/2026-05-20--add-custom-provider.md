# 添加自定义 Provider 与 Model - 业务需求

## 概述

在 Dashboard Web 管理界面的模型清单页面（`/models`）增加"添加自定义 Provider"功能，支持用户通过 UI 创建新 Provider 并手动为其添加 Models。

## 背景与动机

目前 Smart Router 的 Provider 和 Model 只能通过手动编辑 YAML 配置文件添加。对于不熟悉 YAML 或希望快速测试新 Provider 的用户来说门槛较高。通过在 Dashboard 提供可视化添加能力，可以显著降低配置难度，提升用户体验。

## 用户与角色

- **主要用户**: 使用 Smart Router Dashboard 管理模型的运维人员或开发者。
- **使用场景**: 
  - 接入一个新的 OpenAI-compatible API Provider（如 Groq、Together AI 等）。
  - 为新 Provider 配置其支持的模型及能力参数。

## 关键约束

- **API Key 安全**：新添加的 API Key 以明文写入 `providers.yaml`，与现有 `update_providers` 行为一致；同时保留 `os.environ/KEY_NAME` 格式支持。
- **配置验证**：任何 YAML 写入后必须调用 `ConfigLoader.validate()` 确保整体配置一致；验证失败时自动回滚到备份。
- **命名唯一性**：Provider name 和 Model name 必须全局唯一。
- **前端样式**：严格遵循现有暗黑科技风（`tech-card`、`tech-btn-primary`、`input-glow` 等）。
- **手动填写**：模型信息由用户手动输入，不支持自动发现。

## 目标

- 用户可以在 `/models` 页面通过表单创建新的 Provider。
- 用户可以为已创建的 Provider 通过表单手动添加 Model。
- 创建/添加后配置立即持久化到 YAML 文件，Dashboard 状态实时刷新。

## 非目标

- 不支持 Provider 删除（避免误删导致配置丢失）。
- 不支持 Model 删除。
- 不支持自动发现模型列表（用户已明确选择手动填写方案）。
- 不涉及 `routing.yaml` 的修改（新 provider/model 默认不加入 routing 任务映射，由用户后续手动配置）。

## 方案决策

**选定方案**: 在 `/models` 页面统一添加（方案 1）

**原因**: 
- 用户明确要求"在 dashboard 的模型清单页面增加"，`/models` 即模型清单页面。
- 现有页面已具备 ProviderSidebar + ProviderModelsPanel 的左右布局，天然适合"选 Provider → 添加 Model"的交互流程。
- 与现有的 `ProviderEditModal` 设计模式一致，学习成本低。

**替代方案及放弃原因**:
- 方案 2（Dashboard 页面添加 Provider）：将 provider 和 model 添加分散在两个页面，体验不连贯。
- 方案 3（Wizard 向导式）：与现有简洁的直接编辑风格不一致，开发成本高。

## 关键组件（草案）

| 组件 | 职责 | 类型 |
|------|------|------|
| `AddProviderModal` | 收集 Provider 基本信息并提交 | 新增前端组件 |
| `AddModelModal` | 收集 Model 能力参数并提交 | 新增前端组件 |
| `ProviderSidebar` | 在列表顶部渲染 "+ Add Provider" 按钮 | 修改现有组件 |
| `ProviderModelsPanel` | 在模型列表上方渲染 "+ Add Model" 按钮 | 修改现有组件 |
| `ModelsExplorer` | 管理 Modal 开关状态，对接 Store action | 修改现有组件 |
| `useDashboardStore` | 新增 `createProvider`、`addModel` action | 修改现有 store |
| `api/client.ts` | 新增 `createProvider`、`addModel` API 方法 | 修改现有文件 |
| `POST /api/providers` | 接收 Provider 数据，写入 providers.yaml | 新增后端接口 |
| `POST /api/providers/{name}/models` | 接收 Model 数据，写入 models/{name}.yaml | 新增后端接口 |
| `ConfigLoader.create_provider` | 校验并追加 provider 到 providers.yaml | 新增后端方法 |
| `ConfigLoader.add_model` | 校验并追加 model 到对应 YAML | 新增后端方法 |

## 接口草案（前端 ↔ 后端）

```typescript
// POST /api/providers
interface CreateProviderRequest {
  name: string
  api_base: string
  api_key: string
  timeout: number
}

interface CreateProviderResponse {
  success: boolean
  provider: ProviderInfo
  error?: string
}

// POST /api/providers/:name/models
interface AddModelRequest {
  name: string
  litellm_model: string
  quality: number
  cost: number
  context: number
  supported_tasks: string[]
  enabled?: boolean
}

interface AddModelResponse {
  success: boolean
  model: ModelInfo
  error?: string
}
```

## 验收标准（初稿）

- [ ] 在 `/models` 页面点击 "+ Add Provider" 可弹出表单，填写后保存，新 Provider 立即出现在左侧 Sidebar 中。
- [ ] 创建 Provider 时，name 已存在则前端显示明确错误提示。
- [ ] 创建 Provider 后，`providers.yaml` 中新增对应条目，且整体配置通过验证。
- [ ] 选中某个 Provider 后，点击 "+ Add Model" 可弹出表单，填写后保存，新 Model 立即出现在右侧模型列表中。
- [ ] 添加 Model 时，name 全局唯一性校验失败则前端显示明确错误提示。
- [ ] 添加 Model 后，`models/{provider_name}.yaml` 中新增对应条目，且整体配置通过验证。
- [ ] 若写入配置后验证失败，原配置自动回滚，前端收到错误响应。

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 并发写入导致 YAML 损坏 | 中 | 当前为单进程服务，无并发问题；若未来扩展，可引入文件锁 |
| 用户输入无效 YAML 特殊字符（如 `:`、`#`） | 中 | 使用 `yaml.safe_dump` 自动转义；前端做基础输入校验 |
| Model name 与现有 model 冲突 | 低 | 后端在写入前做全局唯一性校验 |
| 写入后验证失败但备份恢复也失败 | 低 | 保持现有 `save_providers` / `save_model` 的备份回滚逻辑 |
