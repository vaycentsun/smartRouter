# Provider 一键开关 - 业务需求

## 概述
在 Provider 详情面板（ProviderModelsPanel）顶部增加一个总开关，允许用户一键启用/禁用整个 Provider。禁用 Provider 后，其下所有模型被视为不可用，但各模型自身的 enabled 状态保持不变。

## 背景与动机
当前系统支持在 Provider 详情面板中对单个模型进行启用/禁用（ENABLED 开关）。当某个 Provider 下模型数量较多时，用户需要逐个点击开关来暂停该 Provider 的所有模型，操作繁琐。用户需要一个类似"总闸"的功能，一键控制整个 Provider 的可用性。

## 用户与角色
- **主要用户**: 使用 Web 管理界面配置模型路由的管理员
- **使用场景**: 
  - 临时停用某个 Provider（如余额不足、服务维护）
  - 快速切换 Provider 的可用状态进行测试

## 关键约束
- 必须使用现有技术栈（React + Zustand + Python FastAPI）
- 不能破坏现有的模型级 enabled 语义
- 默认 Provider 为 enabled（向后兼容，不影响现有配置）
- 配置持久化到 providers.yaml
- 路由选择器必须感知 Provider 禁用状态

## 目标
- Provider 详情面板顶部增加总开关 UI
- 一键切换 Provider 的启用/禁用状态
- Provider 禁用时，其下所有模型显示为不可用（但模型自身 enabled 状态不变）
- Provider 恢复启用后，各模型按自身原有 enabled 状态恢复
- 配置持久化并支持热重载

## 非目标
- 不在 ProvidersTable（Provider 配置表格）中增加此开关（保持配置页面专注基础配置）
- 不在 ModelsTable（模型总表）中增加 Provider 级操作
- 不引入 Provider 级别的路由权重调整
- 不修改模型级 enabled 的持久化文件（models/{provider}.yaml）

## 方案决策
**选定方案**: 方案C — Provider 级别增加 enabled 字段
**原因**: 
- 语义最清晰：Provider 是一个独立的配置实体，理应有自己的可用状态
- 数据一致性最好：禁用 Provider 是"暂停"行为，不污染模型自身的配置
- 对路由引擎影响直接：选择器在过滤模型时天然可以检查 Provider 状态

**替代方案**: 
- 方案A（前端批量调用）：放弃原因是会触发 N 次 API 请求和热重载，体验和一致性差
- 方案B（后端批量 toggle 模型）：放弃原因是仍然修改的是模型级 enabled，会丢失用户原有的模型开关配置

## 关键组件（草案）
- **前端 UI (`ProviderModelsPanel`)**: 在 Provider 名称旁增加总开关，显示当前 Provider 状态；禁用时下方模型列表的 ENABLED 开关置灰并提示 Provider 已禁用
- **前端 Store (`useDashboardStore`)**: 增加 `toggleProvider(provider, enabled)` action，调用 API 并更新本地 providers 状态
- **前端 API (`api/client`)**: 增加 `toggleProvider(provider, enabled)` 调用 `PUT /api/providers/{provider}/toggle`
- **前端类型 (`types`)**: `ProviderInfo` 增加 `enabled: boolean`
- **后端 API (`dashboard_api.py`)**: 新增 `PUT /api/providers/{provider_name}/toggle` 接口，校验、保存、触发热重载
- **后端配置加载器 (`ConfigLoader`)**: 增加 `save_provider_enabled` 方法，读写 providers.yaml
- **后端配置模型 (`schema.py`)**: `ProviderConfig` 增加 `enabled: bool = True`
- **后端路由引擎 (`plugin.py` / `V3ModelSelector`)**: 模型过滤时检查模型所属 Provider 的 enabled 状态

## 验收标准（初稿）
- [ ] ProviderModelsPanel 顶部显示 Provider 总开关，样式与现有模型开关一致
- [ ] 点击总开关可禁用/启用 Provider，操作有 loading 和 toast 反馈
- [ ] Provider 禁用时，其下所有模型在面板中显示为 DISABLED（状态标签和点变为灰色）
- [ ] Provider 禁用时，其下模型的 ENABLED 单独开关被禁用（不可点击），并显示提示
- [ ] Provider 重新启用后，各模型恢复为自身的 enabled 状态（在线/离线/未配置）
- [ ] 禁用 Provider 后，路由选择器不再选择该 Provider 下的任何模型（可通过 dry-run 验证）
- [ ] 配置持久化到 providers.yaml，页面刷新后状态保持
- [ ] 不影响现有单个模型开关功能（在 Provider 启用状态下可正常切换）

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Provider enabled 字段与现有模型 enabled 语义冲突 | 高 | 明确区分：Provider enabled 是"总闸"，模型 enabled 是"分闸"；过滤时先检查 Provider 再检查模型 |
| 向后兼容性：旧配置没有 enabled 字段 | 中 | ProviderConfig 中 enabled 默认值为 True；加载旧配置时视为启用 |
| 前端状态同步：Provider 禁用后模型状态显示不一致 | 中 | `getModelHealthDisplay` 函数优先检查 Provider enabled 状态 |
| 配置热重载时 ruamel.yaml 可能不保留新增字段的注释格式 | 低 | 使用 ruamel.yaml 保留注释；如失败回退到普通写入 |
