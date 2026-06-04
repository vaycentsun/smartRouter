# Responses API 模型映射 - 业务需求

## 概述
为 Smart Router 的 `/v1/responses` 端点启用模型映射和 Model Override 功能，使客户端通过 OpenAI Responses API 发送的请求也能享受网关层的模型透明转发能力。

## 背景与动机
当前 Smart Router 的中间件仅拦截 `/v1/chat/completions` 请求，在 `/v1/responses` 端点上：
- 模型映射（`model_mappings.yaml`）不生效
- Model Override（`X-Smart-Router-Override-*` 请求头）不生效
- 请求完全透传，无法做网关层的模型转发

用户希望客户端使用 Responses API 时，仍能通过 Smart Router 将模型映射到目标服务商的对应模型，实现请求的透明代理。

## 用户与角色
- **主要用户**: 使用 OpenAI Responses API 客户端的 Smart Router 用户
- **使用场景**: 客户端发送 `/v1/responses` 请求，网关根据 `model_mappings.yaml` 将模型名替换为目标模型，转发到支持 Responses API 的服务商

## 关键约束
- 目标服务商支持 Responses API 格式，Smart Router **不做**请求/响应格式转换
- 智能路由（任务分类、模型选择）暂不扩展到 `/v1/responses`（Responses API 的 `input` 格式与 chat messages 不同）
- Token 统计暂不扩展到 `/v1/responses`（usage 字段结构不同）
- `/v1/chat/completions` 的现有行为必须完全不受影响

## 目标
- [ ] `/v1/responses` POST 请求支持 `model_mappings.yaml` 模型映射
- [ ] `/v1/responses` POST 请求支持 Model Override 请求头
- [ ] 映射/覆盖后的响应包含相应的 `X-Smart-Router-*` 头
- [ ] `/v1/chat/completions` 现有行为不受影响

## 非目标
- 不支持基于 Responses API `input` 内容的智能路由（任务分类、模型选择）
- 不支持 `/v1/responses` 的 Token 统计和 Usage 解析
- 不做请求/响应格式转换（Chat Completions ↔ Responses API）
- 不新增 Dashboard API 或配置 Schema 变更

## 方案决策
**选定方案**: 复用现有逻辑，扩展路径匹配

**原因**:
- 改动最小，直接复用 `_apply_model_mapping` 和 Model Override 代码
- 风险低，不触碰智能路由和 Token 统计等复杂逻辑
- 无需配置变更，零新增 API

**替代方案**:
- 重构为通用处理逻辑：放弃，当前需求不需要这么强的扩展性（YAGNI）
- 仅添加模型映射、Model Override 透传：放弃，Model Override 和映射本质类似，应一起支持

## 关键组件（草案）
- **`SmartRouterMiddleware.dispatch`**: 扩展路径匹配，支持 `/v1/responses`；复用映射和覆盖逻辑
- **`SmartRouter`**: 映射目标虚拟模型已全局注册，无需修改
- **`model_mappings.yaml`**: 规则不区分端点，无需 Schema 变更

## 验收标准
- [ ] `/v1/responses` POST 请求匹配 `model_mappings.yaml` 规则时，请求体 `model` 字段被替换为 `to_model`
- [ ] `/v1/responses` POST 请求带 `X-Smart-Router-Override-*` 头时，请求体 `model` 字段被替换为覆盖模型
- [ ] 映射后的 `/v1/responses` 响应包含 `X-Smart-Router-Mapped: true` 和相关头
- [ ] Override 后的 `/v1/responses` 响应包含 `X-Smart-Router-Override-Active: true` 和相关头
- [ ] `/v1/responses` 请求未触发映射/覆盖时，直接透传，不走智能路由
- [ ] `/v1/chat/completions` 的现有行为完全不受影响
- [ ] 热重载机制对 `/v1/responses` 的映射规则同样生效

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 路径匹配扩展影响 chat/completions 稳定性 | 中 | 保持所有现有逻辑不变，仅扩展最外层 `if` 条件；变更后全量回归测试 |
| Responses API 的 `model` 字段层级不同 | 低 | OpenAI Responses API 的 `model` 仍在请求体顶层，解析逻辑无需改动 |
| LiteLLM 对 `/v1/responses` 支持度不确定 | 中 | LiteLLM 已支持 responses 端点；若有问题由 LiteLLM 层处理 |
