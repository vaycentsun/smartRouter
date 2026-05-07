# Fallback 链可视化与最近请求路由记录 - 技术规格

## 1. 架构概述

本功能在现有 Smart Router 网关层增强请求/响应拦截能力，在内存中维护一个固定容量的请求路由历史缓冲区，并通过 Dashboard API 暴露给前端。前端在数据分析页面新增时间线面板展示模型链路与 fallback 状态。

```
┌─────────────────┐     ┌──────────────────────────┐     ┌──────────────────┐
│   客户端请求     │────▶│  SmartRouterMiddleware   │────▶│  LiteLLM Proxy   │
└─────────────────┘     └──────────────────────────┘     └──────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  RequestRoutingHistory │ (内存环形缓冲区, maxlen=50)
                    │  + TokenStats (现有)    │
                    └────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  GET /api/analytics/   │
                    │      recent-requests   │
                    └────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   RecentRequestsPanel  │
                    │     (前端时间线)        │
                    └────────────────────────┘
```

## 2. 组件设计

### 2.1 RequestRoutingHistory（新增）

**文件**: `core/smart_router/utils/request_routing_history.py`

**职责**: 协程安全的内存环形缓冲区，存储最近 50 条请求路由记录。

**数据结构**:

```python
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class RequestRoutingEntry:
    request_id: str
    timestamp: str  # ISO 8601 format
    original_model: str
    selected_model: str
    actual_model: Optional[str]
    task_type: Optional[str]
    difficulty: Optional[str]
    strategy: Optional[str]
    fallback_chain: list[str] = field(default_factory=list)
    attempted_fallbacks: Optional[int] = None
    did_fallback: bool = False
    status_code: int = 200
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error_info: Optional[str] = None
```

**类接口**:

```python
from collections import deque
import asyncio

class RequestRoutingHistory:
    def __init__(self, max_size: int = 50):
        self._buffer: deque[RequestRoutingEntry] = deque(maxlen=max_size)
        self._lock: Optional[asyncio.Lock] = None

    async def record(self, entry: RequestRoutingEntry) -> None:
        """异步写入一条记录（线程/协程安全）"""
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            self._buffer.append(entry)

    def get_recent(self, limit: int = 50) -> list[dict]:
        """获取最近 N 条记录（字典列表，按时间倒序）"""
        entries = list(self._buffer)
        entries.reverse()
        return [self._entry_to_dict(e) for e in entries[:limit]]

    def _entry_to_dict(self, entry: RequestRoutingEntry) -> dict:
        return {
            "request_id": entry.request_id,
            "timestamp": entry.timestamp,
            "original_model": entry.original_model,
            "selected_model": entry.selected_model,
            "actual_model": entry.actual_model,
            "task_type": entry.task_type,
            "difficulty": entry.difficulty,
            "strategy": entry.strategy,
            "fallback_chain": entry.fallback_chain,
            "attempted_fallbacks": entry.attempted_fallbacks,
            "did_fallback": entry.did_fallback,
            "status_code": entry.status_code,
            "prompt_tokens": entry.prompt_tokens,
            "completion_tokens": entry.completion_tokens,
            "total_tokens": entry.total_tokens,
            "error_info": entry.error_info,
        }
```

### 2.2 SmartRouterMiddleware 增强

**文件**: `core/smart_router/gateway/server.py`

**修改点**:

#### 请求阶段（在模型选择逻辑之后）

在为 `request.state` 设置 `smart_router_selected` 等属性后，新增以下逻辑：

```python
import uuid

# 生成 request_id
request_id = str(uuid.uuid4())[:8]  # 短 ID 即可
request.state.smart_router_request_id = request_id

# 获取 fallback 链
fallback_chain = []
if hasattr(self.router, 'get_fallback_chain') and request.state.smart_router_selected:
    try:
        fallback_chain = self.router.get_fallback_chain(request.state.smart_router_selected)
    except Exception:
        pass

# 将路由决策信息存入 request.state
request.state.smart_router_routing_info = {
    "request_id": request_id,
    "original_model": original_model,
    "selected_model": getattr(request.state, 'smart_router_selected', None),
    "task_type": getattr(request.state, 'smart_router_task', None),
    "difficulty": getattr(request.state, 'smart_router_difficulty', None),
    "strategy": getattr(request.state, 'smart_router_strategy', None),
    "fallback_chain": fallback_chain,
}
```

> **注**: `smart_router_difficulty` 和 `smart_router_strategy` 当前未在 request.state 中设置，需要同步在 `select_model` 调用后补充。

#### 响应阶段（在 TokenStats 逻辑中复用 body_bytes）

当前中间件在响应后已消费 `body_bytes` 做 TokenStats。我们在同一位置扩展逻辑：

```python
# 在解析 usage 的同时，提取 actual_model
actual_model = None

if is_sse:
    # SSE 格式：从 data: 行中提取 model 字段
    text = body_bytes.decode("utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                continue
            try:
                chunk = json.loads(data)
                if chunk.get("model"):
                    actual_model = chunk["model"]
                    break  # 取第一个出现的 model 即可
            except json.JSONDecodeError:
                continue
else:
    # 非流式：从 JSON 中提取 model
    try:
        resp_data = json.loads(body_bytes)
        actual_model = resp_data.get("model")
    except json.JSONDecodeError:
        pass

# 获取 routing_info
routing_info = getattr(request.state, 'smart_router_routing_info', None)
selected_model = getattr(request.state, 'smart_router_selected', None)

if routing_info and selected_model:
    # 判断是否 fallback
    did_fallback = actual_model is not None and actual_model != selected_model
    
    # 读取 LiteLLM fallback header（如果 Proxy 层传递）
    attempted_fallbacks = None
    fallback_header = response.headers.get("x-litellm-attempted-fallbacks")
    if fallback_header is not None:
        try:
            attempted_fallbacks = int(fallback_header)
        except ValueError:
            pass
    
    # 组装记录
    from datetime import datetime, timezone
    entry = RequestRoutingEntry(
        request_id=routing_info["request_id"],
        timestamp=datetime.now(timezone.utc).isoformat(),
        original_model=routing_info["original_model"],
        selected_model=selected_model,
        actual_model=actual_model,
        task_type=routing_info.get("task_type"),
        difficulty=routing_info.get("difficulty"),
        strategy=routing_info.get("strategy"),
        fallback_chain=routing_info.get("fallback_chain", []),
        attempted_fallbacks=attempted_fallbacks,
        did_fallback=did_fallback,
        status_code=response.status_code,
        prompt_tokens=usage.get("prompt_tokens", 0) if usage else 0,
        completion_tokens=usage.get("completion_tokens", 0) if usage else 0,
        total_tokens=usage.get("total_tokens", 0) if usage else 0,
    )
    
    # 写入历史
    history = getattr(request.app.state, 'request_routing_history', None)
    if history:
        await history.record(entry)
```

**关键约束**: 必须在消费 `body_bytes` 后、重建 Response 之前完成记录。当前代码结构已经满足这一点（先读取 body，再重建 StreamingResponse/Response）。

### 2.3 Dashboard API 增强

**文件**: `core/smart_router/gateway/dashboard_api.py`

**新增 API**:

```python
async def analytics_recent_requests(request: Request, limit: int = 50):
    """获取最近 N 条请求路由记录"""
    history = getattr(request.app.state, 'request_routing_history', None)
    if not history:
        return {"requests": []}
    return {"requests": history.get_recent(limit)}
```

**路由注册**（在 `build_dashboard_app` 中）:

```python
app.get("/api/analytics/recent-requests")(analytics_recent_requests)
```

### 2.4 服务启动初始化

**文件**: `core/smart_router/gateway/server.py` 的 `start_server` 函数

在初始化 `app.state.token_stats` 之后，新增：

```python
from ..utils.request_routing_history import RequestRoutingHistory
app.state.request_routing_history = RequestRoutingHistory(max_size=50)
```

### 2.5 Router 插件补充 state 信息

**文件**: `core/smart_router/router/plugin.py`

在 `select_model` 方法中，除了设置 `self.last_selected_model`，还需要在调用处（中间件）补充 `difficulty` 和 `strategy` 到 `request.state`。

当前中间件调用 `self.router.select_model(model_hint=original_model, messages=messages)` 后，获取到 `result`（SelectionResult）。`SelectionResult` 已包含 `task_type`, `difficulty`, `strategy` 等字段。中间件可以直接读取这些字段存入 `request.state`。

```python
# 在中间件的请求处理逻辑中
result = self.router.select_model(model_hint=original_model, messages=messages)
selected = result.model_name

request.state.smart_router_selected = selected
request.state.smart_router_original = original_model
request.state.smart_router_task = result.task_type
request.state.smart_router_difficulty = result.difficulty  # 新增
request.state.smart_router_strategy = result.strategy       # 新增
```

### 2.6 前端类型定义

**文件**: `frontend/src/types.ts`

新增类型：

```typescript
export interface RequestRoutingRecord {
  request_id: string
  timestamp: string
  original_model: string
  selected_model: string
  actual_model: string | null
  task_type: string | null
  difficulty: string | null
  strategy: string | null
  fallback_chain: string[]
  attempted_fallbacks: number | null
  did_fallback: boolean
  status_code: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  error_info: string | null
}
```

### 2.7 API Client 增强

**文件**: `frontend/src/api/client.ts`

新增方法：

```typescript
async getRecentRequests(limit = 50): Promise<{ requests: RequestRoutingRecord[] }> {
  const res = await fetch(`/api/analytics/recent-requests?limit=${limit}`)
  if (!res.ok) throw new Error(`Failed to fetch recent requests: ${res.status}`)
  return res.json()
}
```

### 2.8 Store 增强

**文件**: `frontend/src/store/useDashboardStore.ts`

新增状态和 action：

```typescript
// State
recentRequests: RequestRoutingRecord[]
isLoadingRecentRequests: boolean
recentRequestsError: string | null

// Actions
fetchRecentRequests: () => Promise<void>
```

在 `fetchAnalytics` 中同步调用 `fetchRecentRequests`，或单独提供调用入口。建议单独提供，用户切换到数据分析页面时一并加载。

修改 `fetchAnalytics`：

```typescript
fetchAnalytics: async (days = 7) => {
  set({ isLoadingAnalytics: true, analyticsError: null })
  try {
    const [summary, daily, byModel, topModels, recentRequests] = await Promise.all([
      api.getAnalyticsSummary(days),
      api.getAnalyticsDaily(days),
      api.getAnalyticsByModel(days),
      api.getAnalyticsTopModels(10, days),
      api.getRecentRequests(50),
    ])
    set({
      analyticsSummary: summary,
      analyticsDaily: daily,
      analyticsByModel: byModel,
      analyticsTopModels: topModels,
      recentRequests: recentRequests.requests,
      isLoadingAnalytics: false,
    })
  } catch (err) {
    set({ analyticsError: (err as Error).message, isLoadingAnalytics: false })
  }
},
```

### 2.9 RecentRequestsPanel 组件

**文件**: `frontend/src/components/RecentRequestsPanel.tsx`

**Props**:

```typescript
interface RecentRequestsPanelProps {
  requests: RequestRoutingRecord[]
}
```

**视觉设计**:

- 面板标题："最近请求路由记录"
- 列表布局：每条请求一行，三列布局
  - 左列：时间戳（格式化，如 "14:32:05"）
  - 中列：模型链路
    - 未 fallback: `original → selected ✓`（绿色）
    - fallback: `original → selected → actual`（selected → actual 用橙色箭头）
  - 右列：状态码 + token 数
- fallback 请求：左侧加橙色竖条标识
- 交互：点击整行展开详情卡片
  - 任务类型、难度、策略
  - 配置的 fallback 链（列表展示）
  - attempted_fallbacks 次数
  - request_id

**空状态**: "暂无请求记录"

### 2.10 AnalyticsPage 集成

**文件**: `frontend/src/components/AnalyticsPage.tsx`

在 `<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">` 下方新增全宽面板：

```tsx
<div className="w-full">
  <RecentRequestsPanel requests={recentRequests} />
</div>
```

## 3. 数据流

### 3.1 请求记录阶段

```
1. 客户端 POST /v1/chat/completions
2. SmartRouterMiddleware.dispatch()
   a. 生成 request_id → request.state.smart_router_request_id
   b. 调用 router.select_model() → result
   c. 读取 result.difficulty, result.strategy
   d. 获取 fallback_chain = router.get_fallback_chain(result.model_name)
   e. 将所有信息存入 request.state.smart_router_routing_info
   f. 修改请求体，继续传递到 LiteLLM Proxy
3. LiteLLM Proxy 处理请求（可能内部 fallback）
4. 响应返回 SmartRouterMiddleware
   a. 消费 response.body_bytes（与现有 TokenStats 逻辑复用）
   b. 从 body 解析 actual_model（SSE/非流式）
   c. 对比 selected_model vs actual_model → did_fallback
   d. 读取 response header x-litellm-attempted-fallbacks
   e. 组装 RequestRoutingEntry
   f. 写入 app.state.request_routing_history
   g. 重建 Response（现有逻辑）
```

### 3.2 数据查询阶段

```
1. 前端加载 AnalyticsPage
2. 调用 fetchAnalytics()
3. 请求 GET /api/analytics/recent-requests
4. dashboard_api.analytics_recent_requests()
5. RequestRoutingHistory.get_recent()
6. 返回 JSON → 前端渲染 RecentRequestsPanel
```

## 4. 错误处理

### 4.1 响应体解析失败

- **场景**: SSE 格式异常、JSON 损坏、body 为空
- **处理**: `actual_model` 设为 `None`，`did_fallback` 设为 `False`（未知状态不标记为 fallback）
- **影响**: 该请求的记录缺少 actual_model，但不阻断其他逻辑

### 4.2 LiteLLM fallback header 缺失

- **场景**: Proxy 层未将 `_hidden_params.additional_headers` 传递到 HTTP 响应头
- **处理**: `attempted_fallbacks` 设为 `None`
- **降级**: 仍可通过 `actual_model != selected_model` 判断 fallback

### 4.3 环形缓冲区写入冲突

- **场景**: 高并发下多个请求同时完成
- **处理**: `asyncio.Lock` 保证写入串行化
- **影响**: 无数据丢失

### 4.4 服务重启

- **场景**: 进程重启后内存清空
- **处理**: 符合设计预期（内存缓冲），前端显示空状态

## 5. 安全考虑

### 5.1 数据隐私

- 请求路由记录**不包含**用户消息内容、API Key、敏感元数据
- 仅包含模型名称、策略、token 数量等无敏感信息的字段

### 5.2 内存限制

- 严格限制 `deque(maxlen=50)`，防止内存泄漏
- 每条记录约 500 字节，50 条约 25KB，可忽略

### 5.3 API 访问

- `GET /api/analytics/recent-requests` 继承现有 Dashboard API 的访问控制
- 当前 Dashboard 未单独做认证，依赖绑定 127.0.0.1 的本地访问控制（符合现有安全模型）

## 6. 测试策略

### 6.1 后端单元测试

- `RequestRoutingHistory` 测试：
  - `test_record_and_get_recent`: 记录后正确读取
  - `test_max_size_limit`: 超过 50 条后自动丢弃旧记录
  - `test_concurrent_writes`: 并发写入不丢数据

### 6.2 后端集成测试

- 在 `test_server.py` 中测试：
  - `test_recent_requests_api`: API 返回正确格式
  - `test_middleware_records_routing_info`: 请求后缓冲区有记录

### 6.3 前端组件测试

- `RecentRequestsPanel.test.tsx`:
  - 渲染 fallback / 非 fallback 两种状态
  - 点击展开详情
  - 空状态展示

## 7. 依赖与兼容性

### 7.1 后端

- 无新增第三方依赖
- 使用 Python 标准库：`collections.deque`, `uuid`, `dataclasses`, `asyncio`

### 7.2 前端

- 无新增第三方依赖
- 复用现有 React + Zustand + Tailwind CSS 技术栈

### 7.3 LiteLLM 兼容性

- 依赖 LiteLLM 响应体中的 `model` 字段（OpenAI 标准格式，兼容性高）
- `x-litellm-attempted-fallbacks` header 为可选增强，缺失不影响核心功能

## 8. 性能影响

- **内存**: 固定 50 条 × ~500 字节 ≈ 25KB，可忽略
- **CPU**: 响应后解析 body 已存在（TokenStats），仅增加少量字段提取和字典组装
- **I/O**: 无磁盘 I/O（内存缓冲），API 为纯内存读取
- **延迟**: 对请求处理延迟无影响（所有操作在响应发送前/后异步/同步执行，不阻塞）

## 9. 验收标准映射

| 验收标准 | 技术实现 | 验证方式 |
|---------|---------|---------|
| 每次请求的路由决策被正确记录 | Middleware 请求阶段生成 request_id 并存入 request.state | 集成测试：发送请求后检查缓冲区内容 |
| 能准确识别 fallback 是否发生 | 对比 actual_model vs selected_model | 单元测试：构造 actual ≠ selected 的场景 |
| 内存中只保留最近 50 条 | deque(maxlen=50) | 单元测试：写入 60 条，验证只保留后 50 条 |
| 数据分析页面新增面板 | AnalyticsPage 集成 RecentRequestsPanel | 视觉测试/手动验证 |
| 展示时间、原始模型、选中模型、实际模型 | RecentRequestsPanel 渲染逻辑 | 组件测试 |
| fallback 事件有视觉高亮 | did_fallback 为 true 时应用橙色样式 | 组件测试 |
| 可展开查看详情 | 点击交互 + 详情卡片渲染 | 组件测试 |
| 新增 API 能被前端正常调用 | dashboard_api 注册路由 + api client | 集成测试 |
| 不影响现有 TokenStats 和 Analytics | Middleware 中新增逻辑独立执行 | 回归测试 |
| 服务重启后历史清空 | 内存缓冲设计 | 手动验证/单元测试 |
