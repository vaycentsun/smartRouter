# Responses API 模型映射 - 实施计划

## 计划概览

| 项目 | 内容 |
|------|------|
| 变更文件 | `core/smart_router/gateway/server.py`（1 个文件） |
| 测试文件 | `core/smart_router/gateway/tests/test_mapping_api.py`（扩展） |
| 任务数 | 6 个 |
| 预计总时间 | 30–40 分钟 |

---

## 任务列表

### 任务 1: 修改 SmartRouterMiddleware.dispatch 路径匹配

**文件**: `core/smart_router/gateway/server.py`

**动作**: 扩展路径匹配条件，同时支持 `/v1/chat/completions` 和 `/v1/responses`

**详情**:
在 `dispatch` 方法中做以下变更：

1. 将入口条件从：
   ```python
   if request.url.path == "/v1/chat/completions" and request.method == "POST":
   ```
   改为：
   ```python
   is_chat_completions = (
       request.url.path == "/v1/chat/completions" and request.method == "POST"
   )
   is_responses = (
       request.url.path == "/v1/responses" and request.method == "POST"
   )
   
   if is_chat_completions or is_responses:
   ```

2. 将智能路由触发条件从隐含的"在 if 块内"改为显式检查：
   ```python
   if is_chat_completions:
       should_route = (
           original_model in ("auto", "smart-router", "default") or
           original_model.startswith("stage:") or
           original_model.startswith("strategy-")
       )
       if should_route:
           response = await self._route_with_retry(...)
           routed = True
   ```

3. 将 Token 统计条件从：
   ```python
   if request.url.path == "/v1/chat/completions" and request.method == "POST":
   ```
   改为：
   ```python
   if is_chat_completions:
   ```

4. 模型映射和 Model Override 的逻辑**不做任何修改**，自然对两个端点生效。

**验证**:
- [ ] 代码语法正确（Python 可解析）
- [ ] 逻辑与 technical-spec 完全一致
- [ ] `is_chat_completions` 和 `is_responses` 变量命名正确
- [ ] 智能路由和 Token 统计的条件仅依赖 `is_chat_completions`

---

### 任务 2: 编写 responses 模型映射测试

**文件**: `core/smart_router/gateway/tests/test_mapping_api.py`

**动作**: 为 `/v1/responses` 端点的模型映射编写单元测试

**详情**:
新增测试类或方法（参考现有 `TestMiddlewareMappingMatch` 的风格）：

- **测试方法**: `test_middleware_maps_model_responses_endpoint`
- **场景**:
  1. 构造 `Request(scope={...}, receive=...)`，其中 `url.path = "/v1/responses"`
  2. 请求体 JSON: `{"model": "gpt-4", "input": "Hello"}`
  3. 使用 `mock_router_with_mappings` fixture（映射 `gpt-4 -> claude-3-opus`）
  4. `call_next` 使用 `AsyncMock` 返回一个带 `headers` 属性的 `Response`
- **断言**:
  - `call_next` 被调用 1 次
  - 传入 `call_next` 的 `request._body` 解析后，`model` 为 `"claude-3-opus"`
  - `request.state.smart_router_mapped` 为 `True`
  - `request.state.smart_router_mapped_from` 为 `"gpt-4"`
  - `request.state.smart_router_mapped_to` 为 `"claude-3-opus"`
  - 响应头包含 `X-Smart-Router-Mapped: true`
  - 响应头包含 `X-Smart-Router-Mapped-From: gpt-4`
  - 响应头包含 `X-Smart-Router-Mapped-To: claude-3-opus`

**验证**:
- [ ] 测试可运行
- [ ] 在任务 1 完成前，测试预期失败（或 mock 表现与旧代码一致）
- [ ] 任务 1 完成后，测试通过

---

### 任务 3: 编写 responses Model Override 测试

**文件**: `core/smart_router/gateway/tests/test_mapping_api.py`

**动作**: 为 `/v1/responses` 端点的 Model Override 编写单元测试

**详情**:
- **测试方法**: `test_middleware_override_responses_endpoint`
- **场景**:
  1. 构造 `Request(url.path="/v1/responses")`
  2. 请求体 JSON: `{"model": "gpt-4", "input": "Hello"}`
  3. 在请求头中设置 `X-Smart-Router-Override-Provider` 和 `X-Smart-Router-Override-Model`
  4. mock router 的 `sr_config` 使覆盖模型有效
  5. `call_next` 使用 `AsyncMock`
- **断言**:
  - 传入 `call_next` 的 `request._body` 解析后，`model` 为覆盖模型
  - `request.state.smart_router_override` 为 `True`
  - 响应头包含 `X-Smart-Router-Override-Active: true`

**验证**:
- [ ] 测试可运行
- [ ] 任务 1 完成后测试通过

---

### 任务 4: 编写 responses 透传测试

**文件**: `core/smart_router/gateway/tests/test_mapping_api.py`

**动作**: 为 `/v1/responses` 端点无映射/覆盖的情况编写单元测试

**详情**:
- **测试方法**: `test_middleware_no_route_responses_endpoint`
- **场景**:
  1. 构造 `Request(url.path="/v1/responses")`
  2. 请求体 JSON: `{"model": "unknown-model", "input": "Hello"}`（不匹配任何映射规则）
  3. 无 Override 请求头
  4. mock router 无映射配置（使用 `mock_router_no_mappings`）
  5. `call_next` 使用 `AsyncMock`
- **断言**:
  - `_route_with_retry` **不被调用**（使用 `unittest.mock.patch` 监控）
  - `call_next` 被调用 1 次
  - 传入 `call_next` 的 `request._body` 未被修改（`model` 仍为 `"unknown-model"`）
  - 响应头**不包含** `X-Smart-Router-Mapped`

**验证**:
- [ ] 测试可运行
- [ ] 任务 1 完成后测试通过

---

### 任务 5: 编写 chat/completions 回归测试

**文件**: `core/smart_router/gateway/tests/test_mapping_api.py`

**动作**: 确保 `/v1/chat/completions` 的智能路由逻辑未被破坏

**详情**:
- **测试方法**: `test_chat_completions_routing_unchanged`
- **场景**:
  1. 构造 `Request(url.path="/v1/chat/completions")`
  2. 请求体 JSON: `{"model": "auto", "messages": [...]}`
  3. mock router 支持智能路由
  4. `call_next` 使用 `AsyncMock`
- **断言**:
  - `_route_with_retry` **被调用** 1 次（因为它是 chat/completions 且 model="auto"）
  - `routed = True`，最终响应由 `_route_with_retry` 返回

**验证**:
- [ ] 测试可运行
- [ ] 任务 1 前后均通过（回归测试）

---

### 任务 6: 运行全量测试并修复

**动作**: 运行 gateway 模块的全部测试，确保无回归

**详情**:
执行以下命令：
```bash
pytest core/smart_router/gateway/tests/test_mapping_api.py -v
pytest core/smart_router/gateway/tests/test_server.py -v
```

**验证**:
- [ ] `test_mapping_api.py` 全部通过（包括新增和现有测试）
- [ ] `test_server.py` 全部通过
- [ ] 无新增警告或弃用提示

---

## 自检清单

| # | 检查项 | 状态 |
|---|--------|------|
| 1 | **完整性** | ✅ 无待办/占位符 |
| 2 | **规范对齐** | ✅ 所有 technical-spec 需求都有对应任务 |
| 3 | **任务分解** | ✅ 每个任务可在 10 分钟内完成 |
| 4 | **可构建性** | ✅ 文件路径明确，详情足够 |
| 5 | **验收标准覆盖** | ✅ 8 条验收标准全部覆盖 |
| 6 | **明确性** | ✅ 每个任务有确切路径、详情、验证 |
| 7 | **可验证性** | ✅ 验证步骤可执行 |
| 8 | **顺序合理性** | ✅ 实现(1) → 测试(2-5) → 集成验证(6) |

## 验收标准对应表

| 验收标准 | 覆盖任务 |
|---------|---------|
| `/v1/responses` POST 匹配映射规则，model 被替换 | 任务 2 |
| `/v1/responses` POST 带 Override 头，model 被替换 | 任务 3 |
| 映射后的 responses 响应包含 `X-Smart-Router-Mapped-*` | 任务 2 |
| Override 后的 responses 响应包含 `X-Smart-Router-Override-*` | 任务 3 |
| `/v1/responses` 未触发映射/覆盖时直接透传 | 任务 4 |
| `/v1/chat/completions` 现有行为不受影响 | 任务 5、6 |
| 热重载机制对 responses 同样生效 | 复用现有，无需验证 |
| 新增中间件单元测试全部通过 | 任务 6 |
