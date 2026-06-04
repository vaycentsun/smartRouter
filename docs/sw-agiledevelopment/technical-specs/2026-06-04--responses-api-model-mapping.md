---
name: responses-api-model-mapping
description: "Use when implementing model mapping support for /v1/responses endpoint in Smart Router"
---

# Responses API 模型映射 - 技术规范

## 概述
在 `SmartRouterMiddleware` 中扩展路径匹配，使 `/v1/responses` POST 请求与 `/v1/chat/completions` 一样支持模型映射（`model_mappings.yaml`）和 Model Override（请求头 + 全局覆盖）。智能路由（任务分类、模型选择）和 Token 统计保持仅在 `chat/completions` 上生效。

## 架构概述

```
┌─────────────────────────────────────────────────────────────┐
│                    SmartRouterMiddleware                     │
│                                                              │
│  POST /v1/chat/completions    POST /v1/responses            │
│           │                            │                     │
│           ▼                            ▼                     │
│  ┌─────────────────┐          ┌─────────────────┐           │
│  │ 1. 解析请求体    │          │ 1. 解析请求体    │           │
│  │ 2. 模型映射      │          │ 2. 模型映射      │           │
│  │ 3. Model Override│          │ 3. Model Override│           │
│  │ 4. 智能路由      │          │ 4. 直接透传      │           │
│  │ 5. Token 统计    │          │ 5. 直接透传      │           │
│  └─────────────────┘          └─────────────────┘           │
│           │                            │                     │
│           ▼                            ▼                     │
│       LiteLLM Router  (统一转发到目标服务商)                   │
└─────────────────────────────────────────────────────────────┘
```

**核心变更点**：中间件的入口条件从单一路径扩展到两个路径，但内部处理逻辑根据端点类型做差异化处理。

## 组件设计

### 组件 1: SmartRouterMiddleware.dispatch

**位置**: `core/smart_router/gateway/server.py`

**职责**: 拦截 HTTP 请求，根据端点类型决定启用哪些处理阶段。

**接口变更**:

```python
class SmartRouterMiddleware(BaseHTTPMiddleware):
    # _apply_model_mapping 保持完全不变
    
    async def dispatch(self, request: Request, call_next):
        if request.scope.get("_smart_router_internal_retry"):
            return await call_next(request)
        
        routed = False
        
        # ===== 变更点 1: 扩展路径匹配 =====
        # 原: if request.url.path == "/v1/chat/completions" and request.method == "POST":
        # 新: 同时支持 /v1/responses
        is_chat_completions = (
            request.url.path == "/v1/chat/completions" and request.method == "POST"
        )
        is_responses = (
            request.url.path == "/v1/responses" and request.method == "POST"
        )
        
        if is_chat_completions or is_responses:
            try:
                body = await request.body()
                if body:
                    data = json.loads(body)
                    original_model = data.get("model", "")
                    
                    # ===== 模型映射（chat 和 responses 都支持）=====
                    mapped_model = self._apply_model_mapping(original_model)
                    if mapped_model:
                        data["model"] = mapped_model
                        modified_body = json.dumps(data).encode("utf-8")
                        request._body = modified_body
                        
                        # 标记 request.state（与现有逻辑完全一致）
                        request.state.smart_router_mapped = True
                        request.state.smart_router_mapped_from = original_model
                        request.state.smart_router_mapped_to = mapped_model
                        
                        request_id = str(uuid.uuid4())[:8]
                        request.state.smart_router_request_id = request_id
                        request.state.smart_router_routing_info = {
                            "request_id": request_id,
                            "original_model": original_model,
                            "selected_model": mapped_model,
                            "task_type": "mapping",
                            "difficulty": None,
                            "strategy": "mapping",
                            "fallback_chain": [],
                        }
                        
                        console.print(f"[cyan]模型映射: {original_model} -> {mapped_model}[/cyan]")
                        
                        response = await call_next(request)
                        
                        # 添加映射响应头
                        response.headers["X-Smart-Router-Mapped"] = "true"
                        response.headers["X-Smart-Router-Mapped-From"] = original_model
                        response.headers["X-Smart-Router-Mapped-To"] = mapped_model
                        
                        return response
                    
                    # ===== Model Override（chat 和 responses 都支持）=====
                    # 请求头覆盖 + 全局覆盖逻辑复用现有代码
                    # ...（与现有逻辑完全一致）...
                    
                    # ===== 变更点 2: 智能路由仅在 chat/completions 上生效 =====
                    if is_chat_completions:
                        # 原有智能路由逻辑保持不变
                        should_route = (
                            original_model in ("auto", "smart-router", "default") or
                            original_model.startswith("stage:") or
                            original_model.startswith("strategy-")
                        )
                        
                        if should_route:
                            response = await self._route_with_retry(
                                request, call_next, data, original_model
                            )
                            routed = True
                            
            except Exception as e:
                console.print(f"[yellow]请求处理失败: {e}[/yellow]")
                import traceback
                console.print(traceback.format_exc())
        
        if not routed:
            response = await call_next(request)
        
        # 响应头添加（与现有逻辑完全一致，不区分端点）
        # ...
        
        # ===== 变更点 3: Token 统计仅在 chat/completions 上生效 =====
        if is_chat_completions:
            # 原有 Token 统计逻辑保持不变
            ...
        
        return response
```

**关键决策**:
- 使用 `is_chat_completions` 和 `is_responses` 两个布尔变量替代硬编码路径判断，使后续的条件分支语义清晰
- 模型映射和 Model Override 的处理对两个端点完全一致
- 智能路由（`_route_with_retry`）和 Token 统计仅在 `is_chat_completions` 时执行
- 响应头添加逻辑不区分端点（如果 request.state 有映射/覆盖信息，就添加相应头）

### 组件 2: SmartRouter

**位置**: `core/smart_router/router/plugin.py`

**职责**: 持有模型映射配置，启动时将映射目标注册为 LiteLLM 虚拟模型。

**变更**: 无。`_build_litellm_model_list` 已全局注册映射目标虚拟模型，不区分端点。映射目标在 `chat/completions` 和 `responses` 请求中均可被 LiteLLM 查找。

### 组件 3: model_mappings.yaml

**位置**: `~/.smart-router/model_mappings.yaml`

**变更**: 无 Schema 变更。映射规则本身不区分端点，匹配逻辑基于请求体中的 `model` 字段，与端点无关。

## 数据流

### 场景 1: `/v1/responses` 触发模型映射

```
Client Request
  POST /v1/responses
  Body: {"model": "o1-preview", "input": "Hello", "tools": [...]}

      ↓
SmartRouterMiddleware.dispatch
  is_responses = True
  
  1. 解析 body → model = "o1-preview"
  2. _apply_model_mapping("o1-preview")
     → 匹配规则: from_model="o1-preview" → to_model="qwen-max"
     → 返回 "qwen-max"
  3. 修改 body["model"] = "qwen-max"
  4. request._body = modified_body
  5. 标记 request.state (mapped=True, mapped_from="o1-preview", mapped_to="qwen-max")
  
      ↓
  6. call_next(request) → LiteLLM Router
     
      ↓
LiteLLM Router
  查找 model_name="qwen-max"
  → 找到虚拟模型: {model_name: "qwen-max", litellm_params: {model: "openai/qwen-max", api_base: "...", api_key: "..."}}
  → 转发 HTTP 请求到目标服务商 /v1/responses
  
      ↓
目标服务商
  接收 Responses API 格式请求
  返回 Responses API 格式响应
  
      ↓
LiteLLM → SmartRouterMiddleware
  响应头添加:
    X-Smart-Router-Mapped: true
    X-Smart-Router-Mapped-From: o1-preview
    X-Smart-Router-Mapped-To: qwen-max
  
      ↓
Client Response
```

### 场景 2: `/v1/responses` 触发 Model Override

数据流与模型映射类似，区别在于：
- 模型名来自 `X-Smart-Router-Override-Provider` + `X-Smart-Router-Override-Model` 请求头
- 或来自全局覆盖状态（`load_override_state()`）
- 响应头为 `X-Smart-Router-Override-*` 系列

### 场景 3: `/v1/responses` 未触发映射/覆盖

```
Client Request
  POST /v1/responses
  Body: {"model": "gpt-4o", "input": "Hello"}

      ↓
SmartRouterMiddleware.dispatch
  is_responses = True
  
  1. 解析 body → model = "gpt-4o"
  2. _apply_model_mapping("gpt-4o") → 无匹配 → None
  3. 检查 Override 请求头 → 无
  4. 检查全局覆盖 → 无
  5. is_chat_completions = False → 跳过智能路由
  
      ↓
  6. call_next(request) → LiteLLM Router
     
      ↓
LiteLLM Router
  查找 model_name="gpt-4o"
  → 若 gpt-4o 在 model_list 中，正常转发
  → 若不在，返回 404
```

## 错误处理

| 错误场景 | 处理策略 | 说明 |
|---------|---------|------|
| 请求体解析失败（非 JSON）| 捕获异常，打印日志，继续透传 | 与现有 chat/completions 行为一致 |
| 映射规则 `to_base_url` 无效 | 启动时验证，运行时 LiteLLM 返回错误 | 与现有行为一致 |
| 映射目标模型不在 LiteLLM model_list | LiteLLM 返回 404 | 与现有行为一致 |
| Model Override 模型无效 | 打印警告日志，继续透传 | 与现有行为一致 |

## 安全考虑
- 无新增安全需求。模型映射的 API Key 存储、环境变量解析、文件权限等机制已存在于 `ModelMappingLoader` 中。
- `/v1/responses` 的映射规则与 `/v1/chat/completions` 共用同一份 `model_mappings.yaml`，不引入新的配置暴露面。

## 测试策略

### 后端测试

**单元测试：中间件路径匹配扩展**（`core/smart_router/gateway/tests/test_mapping_api.py` 扩展）

新增测试用例覆盖 `/v1/responses` 端点：

1. **`test_middleware_maps_model_responses_endpoint`**
   - 请求路径为 `/v1/responses`
   - 请求体 model 匹配映射规则
   - 断言：下游接收到的请求体 model 被替换，响应头包含映射信息

2. **`test_middleware_override_responses_endpoint`**
   - 请求路径为 `/v1/responses`
   - 携带 `X-Smart-Router-Override-*` 请求头
   - 断言：下游请求体 model 被替换为覆盖模型，响应头包含 Override 信息

3. **`test_middleware_no_route_responses_endpoint`**
   - 请求路径为 `/v1/responses`
   - 无映射、无覆盖
   - 断言：直接透传，不走智能路由（`_route_with_retry` 不被调用）

4. **`test_chat_completions_unchanged`**
   - 回归测试：确保 `/v1/chat/completions` 的映射、覆盖、路由、Token 统计行为完全不变

**测试实现细节**:
- 复用现有的 `mock_router_with_mappings`、`mock_app` fixtures
- 使用 `AsyncMock` 模拟 `call_next`
- 构造 `Request` 对象时指定 `url.path = "/v1/responses"`
- 断言 `request._body` 被修改，`request.state` 被正确标记

### 前端测试
- 无需新增前端测试。Dashboard 的模型映射配置不区分端点，前端无需感知变更。

## 验收标准

- [ ] `/v1/responses` POST 请求匹配 `model_mappings.yaml` 规则时，请求体 `model` 字段被替换为 `to_model`
- [ ] `/v1/responses` POST 请求带 `X-Smart-Router-Override-*` 头时，请求体 `model` 字段被替换为覆盖模型
- [ ] 映射后的 `/v1/responses` 响应包含 `X-Smart-Router-Mapped: true`、`X-Smart-Router-Mapped-From`、`X-Smart-Router-Mapped-To`
- [ ] Override 后的 `/v1/responses` 响应包含 `X-Smart-Router-Override-Active: true`、`X-Smart-Router-Override-Provider`、`X-Smart-Router-Override-Model`
- [ ] `/v1/responses` 请求未触发映射/覆盖时，直接透传，`_route_with_retry` 不被调用
- [ ] `/v1/chat/completions` 的映射、覆盖、智能路由、Token 统计行为完全不受影响
- [ ] 热重载机制对 `/v1/responses` 的映射规则同样生效（复用现有机制，无需额外验证）
- [ ] 新增的中间件单元测试全部通过

## 依赖

### 外部依赖
- 无新增外部依赖

### 内部依赖
- `core/smart_router/gateway/server.py` — 主要变更文件
- `core/smart_router/gateway/tests/test_mapping_api.py` — 新增测试用例
- `core/smart_router/router/plugin.py` — 无需变更，但依赖其虚拟模型注册机制

## 实现任务（概览）
1. 修改 `SmartRouterMiddleware.dispatch`，扩展路径匹配支持 `/v1/responses`
2. 使用 `is_chat_completions` / `is_responses` 变量区分端点处理逻辑
3. 确保智能路由和 Token 统计仅在 `is_chat_completions` 时执行
4. 在 `test_mapping_api.py` 中新增 4 个测试用例覆盖 responses 端点
5. 运行全量测试，确保 chat/completions 行为不受影响
