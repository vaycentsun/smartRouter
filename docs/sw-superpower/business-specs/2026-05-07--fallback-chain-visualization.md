# Fallback 链可视化与最近请求路由记录 - 业务需求

## 概述

在数据分析页面为每个请求可视化展示实际的路由决策与 fallback 降级链路，并持续记录最近 50 次请求的路由历史，帮助运维人员直观了解 Smart Router 的实时路由行为和降级情况。

## 背景与动机

当前数据分析页面仅展示聚合统计（总成本、请求数、模型分布等），但缺少**请求级别的路由洞察**。当某个请求发生 fallback 降级时，用户无法从看板中感知：
- 请求原本应该路由到哪个模型？
- 实际使用了哪个模型？
- 是否发生了 fallback？fallback 深度是多少？

这导致排查路由异常时需要查看日志，效率低下。

## 目标

- 每次 `/v1/chat/completions` 请求记录完整的路由决策与 fallback 结果
- 内存中滚动保存最近 50 条请求路由记录
- 在数据分析页面以时间线形式可视化展示模型链路（原始 → 选中 → 实际）
- fallback 事件有明确的视觉高亮

## 非目标

- 不持久化到磁盘（50 条实时看板数据，服务重启后清空可接受）
- 不追踪 LiteLLM 内部中间失败的尝试模型（超出当前实现范围）
- 不影响现有 TokenStats、Analytics 统计逻辑
- 不修改 LiteLLM Proxy 的 fallback 配置机制

## 方案决策

**选定方案**: 请求-响应对比 + 响应头增强（方案 B）

**原因**:
- 实现简单可靠，不侵入 LiteLLM 内部回调机制
- 足以满足核心诉求：判断 fallback 是否发生，以及从哪个模型 fallback 到了哪个模型
- 中间尝试失败的具体模型在运维中价值有限，且 LiteLLM 已自动处理
- 测试和维护成本低

**替代方案及放弃原因**:
- **方案 A（LiteLLM CustomLogger 深度集成）**: 能精确追踪每次尝试，但深度耦合 LiteLLM 内部实现，回调上下文关联复杂，实现和测试难度大，ROI 低
- **方案 C（混合方案）**: 兼顾准确性和可靠性，但实现最复杂，维护成本高，当前需求不值得

## 关键组件（草案）

### 后端

1. **`RequestRoutingHistory`**（新增，`core/smart_router/utils/request_routing_history.py`）
   - 职责：内存环形缓冲区，协程安全地存储最近 50 条请求路由记录
   - 关键字段：request_id, timestamp, original_model, selected_model, actual_model, task_type, strategy, fallback_chain, attempted_fallbacks, did_fallback, status_code, tokens

2. **`SmartRouterMiddleware` 增强（`core/smart_router/gateway/server.py`）**
   - 请求阶段：生成 request_id，将路由决策信息存入 request.state
   - 响应阶段：解析 actual_model，对比判断是否 fallback，读取 fallback headers，写入 RequestRoutingHistory

3. **新增 API（`core/smart_router/gateway/dashboard_api.py`）**
   - `GET /api/analytics/recent-requests` — 返回最近 50 条记录

### 前端

4. **`RecentRequestsPanel` 组件（新增，`frontend/src/components/RecentRequestsPanel.tsx`）**
   - 职责：时间线列表，展示模型链路与 fallback 状态
   - 视觉：原始模型 → 选中模型 → 实际模型；fallback 用橙色箭头高亮；未 fallback 用绿色对勾
   - 交互：点击展开查看任务类型、策略、配置的 fallback 链等详情

5. **`AnalyticsPage` 集成（`frontend/src/components/AnalyticsPage.tsx`）**
   - 在现有图表下方新增 RecentRequestsPanel

6. **状态管理增强（`frontend/src/store/useDashboardStore.ts`）**
   - 新增 `recentRequests` 状态与 `fetchRecentRequests` action
   - 新增 API client 方法 `getRecentRequests`

## 验收标准

- [ ] 每次 `/v1/chat/completions` 请求的路由决策被正确记录
- [ ] 能准确识别 fallback 是否发生（actual_model ≠ selected_model）
- [ ] 内存中只保留最近 50 条记录，自动滚动
- [ ] 数据分析页面新增「最近请求路由记录」面板
- [ ] 每个请求展示时间、原始模型、选中模型、实际模型
- [ ] fallback 事件有明确的视觉高亮（橙色箭头 + 徽章）
- [ ] 可展开查看任务类型、策略、配置的 fallback 链等详情
- [ ] 新增 API 能被前端正常调用
- [ ] 不影响现有 TokenStats 和 Analytics 统计功能
- [ ] 服务重启后历史记录清空（符合内存缓冲设计）

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LiteLLM Proxy 不传递 `x-litellm-attempted-fallbacks` header | 中 | 降级处理：如果读取不到 header，仅依赖 actual_model ≠ selected_model 判断 fallback，attempted_fallbacks 显示为 null |
| 响应体解析失败（流式/非流式格式差异） | 中 | 已有 TokenStats 的解析逻辑可参考复用；解析失败时不阻断请求，仅跳过记录 |
| 高频请求导致内存增长 | 低 | 严格限制 50 条环形缓冲区，旧记录自动丢弃 |
| 多并发写入冲突 | 低 | 使用 asyncio.Lock 保证协程安全 |
