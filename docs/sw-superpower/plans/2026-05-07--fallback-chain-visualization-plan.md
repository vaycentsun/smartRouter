# Fallback 链可视化与最近请求路由记录 - 实现计划

## 计划概览

- **任务总数**: 12
- **预计总时间**: 50-60 分钟
- **后端任务**: 7（含 4 个测试任务）
- **前端任务**: 5（含 1 个测试任务）

---

## 任务列表

### 任务 1: 创建 RequestRoutingHistory 类

**文件**: `core/smart_router/utils/request_routing_history.py`

**动作**: 创建 RequestRoutingEntry dataclass 和 RequestRoutingHistory 类

**详情**:
```python
from dataclasses import dataclass, field
from typing import Optional
from collections import deque
import asyncio

@dataclass
class RequestRoutingEntry:
    request_id: str
    timestamp: str
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

class RequestRoutingHistory:
    def __init__(self, max_size: int = 50):
        self._buffer: deque[RequestRoutingEntry] = deque(maxlen=max_size)
        self._lock: Optional[asyncio.Lock] = None

    async def record(self, entry: RequestRoutingEntry) -> None:
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            self._buffer.append(entry)

    def get_recent(self, limit: int = 50) -> list[dict]:
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

**验证**:
- [ ] 文件可导入：`python -c "from smart_router.utils.request_routing_history import RequestRoutingHistory, RequestRoutingEntry"`
- [ ] 语法正确

**依赖**: 无

---

### 任务 2: 编写 RequestRoutingHistory 单元测试

**文件**: `core/smart_router/utils/tests/test_request_routing_history.py`

**动作**: 为 RequestRoutingHistory 编写单元测试

**详情**:
- 场景 1: `test_record_and_get_recent` — 记录单条记录后正确读取
- 场景 2: `test_max_size_limit` — 写入 60 条，验证只保留后 50 条（最旧的被丢弃）
- 场景 3: `test_concurrent_writes` — 使用 asyncio.gather 并发写入 100 条，验证无数据丢失、无异常
- 场景 4: `test_entry_to_dict` — 验证字典转换包含所有字段

**验证**:
- [ ] 测试可运行：`pytest core/smart_router/utils/tests/test_request_routing_history.py -v`
- [ ] 先失败（RED）：先运行测试确认失败（因文件尚未创建）→ 任务 1 完成后重新运行
- [ ] 实现后通过（GREEN）：任务 1 完成后运行测试通过

**依赖**: 任务 1

---

### 任务 3: SmartRouterMiddleware 请求阶段增强 + start_server 初始化

**文件**: `core/smart_router/gateway/server.py`

**动作**: 在中间件请求处理逻辑中补充 routing_info，在 start_server 中初始化 RequestRoutingHistory

**详情**:

在中间件请求阶段（select_model 后），现有代码已设置 `smart_router_selected` 等属性。需补充：

```python
# 在请求处理逻辑的 select_model 调用后
result = self.router.select_model(model_hint=original_model, messages=messages)
selected = result.model_name

# 补充 difficulty 和 strategy
request.state.smart_router_selected = selected
request.state.smart_router_original = original_model
request.state.smart_router_task = result.task_type
request.state.smart_router_difficulty = result.difficulty  # 新增
request.state.smart_router_strategy = result.strategy       # 新增

# 生成 request_id 和 routing_info
import uuid
request_id = str(uuid.uuid4())[:8]
request.state.smart_router_request_id = request_id

fallback_chain = []
if hasattr(self.router, 'get_fallback_chain') and selected:
    try:
        fallback_chain = self.router.get_fallback_chain(selected)
    except Exception:
        pass

request.state.smart_router_routing_info = {
    "request_id": request_id,
    "original_model": original_model,
    "selected_model": selected,
    "task_type": result.task_type,
    "difficulty": result.difficulty,
    "strategy": result.strategy,
    "fallback_chain": fallback_chain,
}
```

在 `start_server` 函数中，初始化 token_stats 之后：
```python
from ..utils.request_routing_history import RequestRoutingHistory
app.state.request_routing_history = RequestRoutingHistory(max_size=50)
```

**验证**:
- [ ] 修改不破坏现有测试：`pytest core/smart_router/gateway/tests/test_server.py -v`
- [ ] 语法正确

**依赖**: 任务 1

---

### 任务 4: SmartRouterMiddleware 响应阶段增强

**文件**: `core/smart_router/gateway/server.py`

**动作**: 在 TokenStats 逻辑区域（消费 body_bytes 后、重建 Response 前）集成 RequestRoutingHistory 记录

**详情**:

在现有 TokenStats 代码中（`if request.url.path == "/v1/chat/completions"` 块内），在解析 `usage` 的同时，增加 `actual_model` 解析：

```python
# 在解析 usage 后，增加 actual_model 解析
actual_model = None
if is_sse:
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
                    break
            except json.JSONDecodeError:
                continue
else:
    try:
        resp_data = json.loads(body_bytes)
        actual_model = resp_data.get("model")
    except json.JSONDecodeError:
        pass

# 组装并写入 RequestRoutingHistory
routing_info = getattr(request.state, 'smart_router_routing_info', None)
selected_model = getattr(request.state, 'smart_router_selected', None)

if routing_info and selected_model:
    did_fallback = actual_model is not None and actual_model != selected_model
    attempted_fallbacks = None
    fallback_header = response.headers.get("x-litellm-attempted-fallbacks")
    if fallback_header is not None:
        try:
            attempted_fallbacks = int(fallback_header)
        except ValueError:
            pass

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

    history = getattr(request.app.state, 'request_routing_history', None)
    if history:
        await history.record(entry)
```

**验证**:
- [ ] 修改不破坏现有测试：`pytest core/smart_router/gateway/tests/test_server.py -v`
- [ ] 新增逻辑不阻断主流程（异常被捕获）

**依赖**: 任务 3

---

### 任务 5: 编写中间件集成测试

**文件**: `core/smart_router/gateway/tests/test_server.py`

**动作**: 新增测试验证中间件是否正确记录路由历史

**详情**:
- 场景 1: `test_middleware_records_routing_info` — 构造 mock 请求（非流式），响应体包含 model 字段，验证 `app.state.request_routing_history` 中有 1 条记录，且记录字段正确
- 场景 2: `test_middleware_detects_fallback` — 构造请求，selected_model="gpt-4o"，响应体 model="claude-3-opus"，验证 did_fallback=True
- 场景 3: `test_middleware_no_fallback` — 构造请求，selected_model="gpt-4o"，响应体 model="gpt-4o"，验证 did_fallback=False

参考现有 `test_middleware_records_usage` 的 mock 模式（mock_router, mock_call_next, 构造 Request 对象）。

**验证**:
- [ ] 测试可运行：`pytest core/smart_router/gateway/tests/test_server.py::TestSmartRouterMiddleware::<新测试名> -v`
- [ ] 先失败（RED）：任务 3/4 完成前运行应失败
- [ ] 实现后通过（GREEN）：任务 3/4 完成后运行通过

**依赖**: 任务 3, 任务 4

---

### 任务 6: 新增 analytics_recent_requests API 及路由注册

**文件**: `core/smart_router/gateway/dashboard_api.py`

**动作**: 新增 API handler 并在 build_dashboard_app 中注册路由

**详情**:

在 dashboard_api.py 中新增 handler：
```python
async def analytics_recent_requests(request: Request, limit: int = 50):
    history = getattr(request.app.state, 'request_routing_history', None)
    if not history:
        return {"requests": []}
    return {"requests": history.get_recent(limit)}
```

在 `build_dashboard_app` 的 Analytics API 区域注册：
```python
app.get("/api/analytics/recent-requests")(analytics_recent_requests)
```

**验证**:
- [ ] 修改不破坏现有测试：`pytest core/smart_router/gateway/tests/test_dashboard_api.py -v`
- [ ] API 可访问（通过 TestClient）

**依赖**: 任务 1

---

### 任务 7: 编写 API 测试

**文件**: `core/smart_router/gateway/tests/test_analytics_api.py`

**动作**: 新增测试验证 `/api/analytics/recent-requests` API

**详情**:
- 场景 1: `test_recent_requests_empty` — 无历史记录时返回空列表
- 场景 2: `test_recent_requests_with_data` — 向 `app.state.request_routing_history` 预置记录，验证 API 返回正确格式和字段
- 场景 3: `test_recent_requests_limit` — 预置 60 条记录，limit=50 时返回 50 条

**验证**:
- [ ] 测试可运行：`pytest core/smart_router/gateway/tests/test_analytics_api.py::TestRecentRequests -v`
- [ ] 先失败（RED）→ 实现后通过（GREEN）

**依赖**: 任务 6

---

### 任务 8: 前端类型和 API client 增强

**文件**: `frontend/src/types.ts`, `frontend/src/api/client.ts`

**动作**: 新增 RequestRoutingRecord 类型和 getRecentRequests 方法

**详情**:

`frontend/src/types.ts` 中新增：
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

`frontend/src/api/client.ts` 中新增：
```typescript
async getRecentRequests(limit = 50): Promise<{ requests: RequestRoutingRecord[] }> {
  const res = await fetch(`/api/analytics/recent-requests?limit=${limit}`)
  if (!res.ok) throw new Error(`Failed to fetch recent requests: ${res.status}`)
  return res.json()
}
```

**验证**:
- [ ] TypeScript 编译通过：`cd frontend && npx tsc --noEmit`
- [ ] 无类型错误

**依赖**: 无

---

### 任务 9: Store 增强

**文件**: `frontend/src/store/useDashboardStore.ts`

**动作**: 在 DashboardState 中新增 recentRequests 状态，修改 fetchAnalytics 同步获取 recent requests

**详情**:

在 State 接口中新增：
```typescript
recentRequests: RequestRoutingRecord[]
```

在初始状态中新增：
```typescript
recentRequests: [],
```

修改 `fetchAnalytics`：
```typescript
fetchAnalytics: async (days = 7) => {
  set({ isLoadingAnalytics: true, analyticsError: null })
  try {
    const [summary, daily, byModel, topModels, recentReqs] = await Promise.all([
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
      recentRequests: recentReqs.requests,
      isLoadingAnalytics: false,
    })
  } catch (err) {
    set({ analyticsError: (err as Error).message, isLoadingAnalytics: false })
  }
},
```

**验证**:
- [ ] TypeScript 编译通过：`cd frontend && npx tsc --noEmit`
- [ ] 无类型错误

**依赖**: 任务 8

---

### 任务 10: 创建 RecentRequestsPanel 组件

**文件**: `frontend/src/components/RecentRequestsPanel.tsx`

**动作**: 实现时间线面板组件，展示模型链路与 fallback 状态

**详情**:

组件结构：
- 接收 `requests: RequestRoutingRecord[]` props
- 面板标题："最近请求路由记录"
- 列表渲染：
  - 空状态：显示 "暂无请求记录"
  - 每条请求一行，使用 flex/grid 布局
  - 左列：时间戳（格式化为本地时间，如 "14:32:05"）
  - 中列：模型链路
    - 未 fallback：`{original} → {selected} ✓`（绿色文字/图标）
    - fallback：`{original} → {selected} → {actual}`（selected → actual 用橙色箭头和背景高亮）
  - 右列：状态码 + total_tokens
  - fallback 请求：左侧加 3px 橙色竖条（`border-l-3 border-orange-400`）
- 交互：点击整行展开/折叠详情卡片
  - 详情内容：任务类型、难度、策略、fallback 链列表、attempted_fallbacks、request_id
- 使用 Tailwind CSS 现有样式类（参考项目中其他组件的 glass-card 等样式）

**验证**:
- [ ] 组件可编译通过
- [ ] 手动验证：在浏览器中查看渲染效果（fallback/非 fallback/空状态）

**依赖**: 任务 8

---

### 任务 11: 编写 RecentRequestsPanel 组件测试

**文件**: `frontend/src/components/RecentRequestsPanel.test.tsx`

**动作**: 为 RecentRequestsPanel 编写 Vitest + React Testing Library 测试

**详情**:
- 场景 1: `renders empty state` — 传入空数组，验证显示 "暂无请求记录"
- 场景 2: `renders non-fallback request` — 传入 did_fallback=false 的记录，验证绿色对勾/无橙色高亮
- 场景 3: `renders fallback request` — 传入 did_fallback=true 的记录，验证橙色箭头和左侧竖条
- 场景 4: `toggles details on click` — 点击请求行，验证详情卡片展开/折叠
- 场景 5: `renders model chain correctly` — 验证原始/选中/实际模型名称正确显示

**验证**:
- [ ] 测试可运行：`cd frontend && npm test -- RecentRequestsPanel.test.tsx`
- [ ] 先失败（RED）→ 实现后通过（GREEN）

**依赖**: 任务 10

---

### 任务 12: AnalyticsPage 集成 RecentRequestsPanel

**文件**: `frontend/src/components/AnalyticsPage.tsx`

**动作**: 在 AnalyticsPage 中引入并渲染 RecentRequestsPanel

**详情**:

修改 AnalyticsPage：
```typescript
import { RecentRequestsPanel } from './RecentRequestsPanel'

// 在 store 解构中增加 recentRequests
const {
  // ... existing
  recentRequests,
} = useDashboardStore()

// 在 JSX 中，现有 grid 下方新增全宽面板
<div className="w-full">
  <RecentRequestsPanel requests={recentRequests} />
</div>
```

**验证**:
- [ ] TypeScript 编译通过：`cd frontend && npx tsc --noEmit`
- [ ] 页面能正常加载，RecentRequestsPanel 出现在数据分析页面底部
- [ ] 端到端验证：发送一个 chat/completions 请求，刷新数据分析页面，确认新请求出现在面板中

**依赖**: 任务 9, 任务 10

---

## 深度自检清单

| # | 检查项 | 状态 |
|---|--------|------|
| 1 | 完整性 — 无 TODO、无占位符 | ✅ 通过 |
| 2 | Spec 对齐 — 每个 Spec 需求都有对应任务 | ✅ 通过 |
| 3 | 任务分解 — 每个任务能在 2-5 分钟内完成 | ✅ 通过 |
| 4 | 可构建性 — 文件路径明确、详情足够 | ✅ 通过 |
| 5 | 验收标准覆盖 — 10 条验收标准均有对应验证 | ✅ 通过 |
| 6 | 明确性 — 每个任务有确切文件路径、详情、验证步骤 | ✅ 通过 |
| 7 | 可验证性 — 每个任务的验证步骤可执行 | ✅ 通过 |
| 8 | 顺序合理性 — 依赖正确，实现+测试成对相邻，基础优先 | ✅ 通过 |

---

## 验收标准覆盖映射

| 验收标准 | 对应任务 | 验证方式 |
|---------|---------|---------|
| 每次请求的路由决策被正确记录 | 任务 3, 4, 5 | 集成测试：检查 history 缓冲区 |
| 能准确识别 fallback 是否发生 | 任务 4, 5 | 单元测试：对比 actual vs selected |
| 内存中只保留最近 50 条 | 任务 1, 2 | 单元测试：deque maxlen |
| 数据分析页面新增面板 | 任务 10, 12 | 视觉验证/组件测试 |
| 展示时间、原始模型、选中模型、实际模型 | 任务 10, 11 | 组件测试 |
| fallback 事件有视觉高亮 | 任务 10, 11 | 组件测试 |
| 可展开查看详情 | 任务 10, 11 | 组件测试 |
| 新增 API 能被前端正常调用 | 任务 6, 7 | API 测试 + 端到端验证 |
| 不影响现有 TokenStats 和 Analytics | 任务 3, 4, 5 | 回归测试：现有测试全部通过 |
| 服务重启后历史清空 | 任务 1 | 单元测试/设计验证 |
