# 模型单独开关（Model Toggle）- 业务需求

## 概述
为 Smart Router 的每个模型增加一个 `enabled` 开关。用户可通过 Web 管理界面手动禁用特定模型；被禁用的模型不再参与路由选择，且开关状态持久化到对应 `models/{provider}.yaml` 文件中。

## 背景与动机
当前所有配置在 `models.yaml` 中的模型默认全部可用。当某个模型临时不可用、成本过高或用户不希望使用时，没有简单的方式在界面上将其剔除，只能手动编辑 YAML 文件并重启服务。这降低了运维效率。

## 用户与角色
- **主要用户**: Smart Router 管理员 / 使用者
- **使用场景**: 
  - 某模型 API Key 额度用完，临时禁用
  - 新模型测试完毕后决定不下线旧模型但不再使用
  - 根据业务策略动态调整可用模型池

## 关键约束
- 必须保持向后兼容：未设置 `enabled` 的模型默认启用
- 开关状态必须持久化到 `models/` 目录下的 YAML，不能仅存于前端状态
- 修改后必须通过配置热重载生效，无需重启服务
- 不能破坏现有健康检查、fallback、analytics 等逻辑

## 目标
- [ ] 在 `ModelConfig` Schema 中增加 `enabled: bool = True`
- [ ] Web 界面 Provider 模型列表中每行显示一个 Toggle Switch
- [ ] 用户点击开关后即时保存到 YAML 并热重载
- [ ] 被禁用的模型不再出现在路由候选池中
- [ ] `GET /api/models` 返回中包含 `enabled` 字段

## 非目标
- 不增加批量开关（一键全选/全不选）
- 不增加开关历史记录或审计日志
- 不增加基于开关的 analytics 筛选（analytics 仍统计所有请求）
- 不修改 CLI 命令（`smr list` 等暂不显示开关状态）

## 方案决策
**选定方案**: 方案 A — 逐模型保存 API（`PUT /api/models/{provider}/{model}`）
**原因**: 
- 接口语义清晰，与现有单资源更新模式一致
- 只写入目标文件，避免全量 models 目录扫描
- 前端操作单个开关即可即时保存，UX 最自然
**替代方案**: 
- 方案 B（批量保存）因实现复杂度高、需处理跨文件合并而放弃
- 方案 C（独立文件）与用户明确要求"在每个 model.yaml 中增加字段"冲突

## 关键组件（草案）
| 组件 | 职责 |
|------|------|
| `config/schema.py::ModelConfig` | 增加 `enabled` 字段，默认 `True` |
| `config/loader.py::ConfigLoader` | 新增 `save_model()` 方法，按 provider 修改单个 YAML |
| `selector/v3_selector.py::_filter_candidates` | 过滤 `enabled=False` 的模型 |
| `gateway/dashboard_api.py` | 新增 `PUT /api/models/{provider}/{model}`，返回 `enabled` |
| `frontend/src/api/client.ts` | 新增 `toggleModel()` API 调用 |
| `frontend/src/store/useDashboardStore.ts` | 新增 `toggleModel` action 和 loading 状态 |
| `frontend/src/components/ProviderModelsPanel.tsx` | 表格增加开关列和交互 |
| `frontend/src/components/ModelsTable.tsx` | 显示模型启用/禁用状态 |

## 验收标准
- [ ] 默认模板 `models/*.yaml` 中所有模型包含 `enabled: true`
- [ ] 未设置 `enabled` 的旧配置加载时默认视为启用
- [ ] 禁用模型后，`smr dry-run` 不再选中该模型
- [ ] 禁用模型后，实际 LLM 请求不再路由到该模型
- [ ] Web 界面开关操作后，500ms 内完成保存并刷新列表
- [ ] 配置热重载生效，无需重启服务
- [ ] 现有 pytest 测试全部通过
- [ ] 新增测试覆盖：Schema 默认值、Selector 过滤、API 保存与验证

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| ruamel.yaml 未安装导致注释丢失 | 中 | 优先使用 ruamel.yaml 保留注释，回退到 yaml.safe_dump |
| 并发写入 models/ 目录导致文件损坏 | 低 | 当前是单进程服务，无并发；未来如需并发可加文件锁 |
| 前端开关快速点击导致重复请求 | 低 | 前端设置 loading 状态禁用按钮，或加防抖 |
| 禁用所有模型导致无可用模型 | 中 | 保持现有 `NoModelAvailableError` 处理逻辑不变 |
