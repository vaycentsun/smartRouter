# 映射规则按端点过滤 - 业务需求

## 概述
为模型映射规则（ModelMappingRule）新增 `endpoints` 字段，允许每条规则独立配置适用于哪些 API 端点（`/v1/chat/completions` 和/或 `/v1/responses`），实现更细粒度的请求转发控制。

## 背景与动机
当前模型映射规则在两个端点（chat/completions 和 responses）上全局生效。用户希望：
1. 某些规则只在 chat/completions 上映射（如 `gpt-4 → qwen-max`）
2. 某些规则只在 responses 上映射（如 `o1-preview → deepseek-r1`）
3. 某些规则在两个端点上映射（默认行为，向后兼容）

## 用户与角色
- **主要用户**: Dashboard 管理员
- **使用场景**: 在模型映射 Tab 中配置规则时，指定每条规则的适用端点

## 关键约束
- 向后兼容：现有规则（无 endpoints 字段）默认同时适用于两个端点
- 空列表不允许：每条规则至少适用于一个端点
- 前端 UI 直观：两个复选框（Chat Completions / Responses）
- 配置热重载：变更后 1 秒内生效

## 目标
- [ ] `ModelMappingRule` Schema 新增 `endpoints: List[str]` 字段
- [ ] 中间件 `_apply_model_mapping` 根据请求端点过滤规则
- [ ] 前端表单增加端点多选控件
- [ ] 前端表格显示每条规则的适用端点
- [ ] 向后兼容：无 endpoints 字段的规则默认同时适用两个端点

## 非目标
- 不支持通配符或正则匹配端点
- 不支持除 chat/responses 外的其他端点（如 embeddings）
- 不修改智能路由或 Model Override 的端点行为

## 方案决策
**选定方案**: 在 ModelMappingRule 中新增 `endpoints` 字段

**原因**:
- 改动最小，符合现有三文件架构
- 向后兼容，不影响现有配置
- 前端改动直观

## 验收标准
- [ ] 规则配置 `endpoints: ["chat"]` 时，只在 `/v1/chat/completions` 上生效
- [ ] 规则配置 `endpoints: ["responses"]` 时，只在 `/v1/responses` 上生效
- [ ] 规则配置 `endpoints: ["chat", "responses"]` 时，两个端点都生效
- [ ] 规则无 `endpoints` 字段时，默认两个端点都生效（向后兼容）
- [ ] 前端表单可以勾选/取消勾选 Chat Completions 和 Responses
- [ ] 前端表格显示每条规则的适用端点
- [ ] 验证失败时（空列表）Dashboard 显示错误
- [ ] 热重载后新规则立即生效
