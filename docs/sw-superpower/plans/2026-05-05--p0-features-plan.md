# Smart Router P0 功能实现计划

> **对应 Spec**: `docs/sw-superpower/specs/2026-05-05--p0-features.md`
> **批次策略**: 数据层 → 交互层 → 监控层
> **预计总任务数**: 39
> **预计总时间**: ~195 分钟

---

## 批次1：高级分析仪表盘（任务 1-16）

### 任务 1: 改造 TokenStats 支持按日聚合

**文件**: `core/smart_router/utils/token_stats.py`

**动作**: 改造 TokenStats 类，新增 `daily_records` 存储，支持 v1→v2 自动升级

**详情**:
- 修改 `TokenStats.__init__`：加载时检测 `version` 字段，v1 自动升级（保留 `records`，新增空的 `daily_records`）
- 修改 `TokenStats.record()`：同时更新 `records[model]` 和 `daily_records[date][model]`
- 新增 `get_daily(date_str)`、`get_daily_range(start, end)`、`get_summary(days)` 方法
- 新增 `DEFAULT_STATS_FILE` 同级备份逻辑：升级前复制到 `.bak`

**验证**:
- [ ] v1 格式文件自动升级到 v2，备份文件存在
- [ ] 调用 `record()` 后 `daily_records[今日日期][model]` 正确累加
- [ ] `get_summary(7)` 返回近7天数据

**依赖**: —

---

### 任务 2: 编写 TokenStats 测试

**文件**: `core/smart_router/utils/tests/test_token_stats.py`

**动作**: 为 TokenStats 改造编写单元测试

**详情**:
- 场景1: v1 格式自动升级，验证 `daily_records` 被创建且 `records` 保留
- 场景2: `record()` 同时写入累计和每日数据
- 场景3: `get_daily_range()` 返回正确日期范围
- 场景4: 文件损坏时优雅降级（保留 `records`，`daily_records` 重建）
- 场景5: 并发 `record()` 不丢数据

**验证**:
- [ ] 所有测试可运行
- [ ] 先失败（RED）→ 实现后通过（GREEN）

**依赖**: 任务 1

---

### 任务 3: 扩展 Config Schema 支持 price 字段

**文件**: `core/smart_router/config/schema.py`

**动作**: 在 `ModelCapabilities` 同级新增可选的 `ModelPrice` Pydantic 模型

**详情**:
```python
class ModelPrice(BaseModel):
    prompt_per_1k: float = Field(..., gt=0)
    completion_per_1k: float = Field(..., gt=0)
    currency: str = Field(default="USD", pattern="^(CNY|USD)$")

class ModelConfig(BaseModel):
    # ... 现有字段
    price: Optional[ModelPrice] = None
```
- `price` 字段为 Optional，不破坏现有配置
- `ConfigLoader.load()` 正常解析含/不含 `price` 的 models.yaml

**验证**:
- [ ] 含 `price` 的 models.yaml 正常加载
- [ ] 不含 `price` 的 models.yaml 正常加载（向后兼容）
- [ ] `price.currency` 非法值时验证报错

**依赖**: —

---

### 任务 4: 编写 Config Schema 测试

**文件**: `core/smart_router/config/tests/test_schema.py`

**动作**: 为 price 字段添加测试

**详情**:
- 场景1: 含完整 `price` 的模型配置正确解析
- 场景2: 不含 `price` 的模型配置正确解析（price=None）
- 场景3: `price.currency` 为 "EUR" 时验证失败
- 场景4: `price.prompt_per_1k` 为负数时验证失败

**验证**:
- [ ] 所有测试可运行，先失败后通过

**依赖**: 任务 3

---

### 任务 5: 新增 Analytics API 后端端点

**文件**: `core/smart_router/gateway/dashboard_api.py`

**动作**: 新增 4 个 analytics 端点及其处理函数

**详情**:
```python
async def analytics_summary(days: int = 7) -> dict
async def analytics_daily(days: int = 7) -> list[dict]
async def analytics_by_model(days: int = 7) -> list[dict]
async def analytics_top_models(limit: int = 10, days: int = 7) -> list[dict]
```
- 从 `TokenStats` 读取 `daily_records`，按日期范围过滤
- 成本计算：`(prompt / 1000 * price.prompt_per_1k) + (completion / 1000 * price.completion_per_1k)`
- 汇总时跳过无单价的模型，返回 `{"total_cost": x, "incomplete": true}`
- 限制 `days` 最大 90，超出时截断
- 在 `build_dashboard_app()` 中注册：
  ```python
  app.get("/api/analytics/summary")(analytics_summary)
  app.get("/api/analytics/daily")(analytics_daily)
  app.get("/api/analytics/by-model")(analytics_by_model)
  app.get("/api/analytics/top-models")(analytics_top_models)
  ```

**验证**:
- [ ] 4 个端点均返回正确 JSON 结构
- [ ] 无单价模型的成本为 `None`
- [ ] `days=90` 正常返回，`days=100` 被截断为 90
- [ ] 空数据时返回空数组/0值，不报错

**依赖**: 任务 1, 3

---

### 任务 6: 编写 Analytics API 测试

**文件**: `core/smart_router/gateway/tests/test_dashboard_api.py`（或新建 `test_analytics_api.py`）

**动作**: 为 4 个 analytics 端点编写单元测试

**详情**:
- 场景1: `/api/analytics/summary` 返回正确汇总（含成本）
- 场景2: `/api/analytics/daily` 返回每日趋势数组
- 场景3: `/api/analytics/by-model` 返回按模型聚合
- 场景4: `/api/analytics/top-models` 返回 TOP N
- 场景5: 部分模型无单价时 `incomplete=true`
- 场景6: 空数据时返回空数组

**验证**:
- [ ] 所有测试可运行，先失败后通过

**依赖**: 任务 5

---

### 任务 7: 新建 ErrorCounter 内存滑动窗口计数器

**文件**: `core/smart_router/gateway/error_counter.py`（新建）

**动作**: 创建基于内存的 5 分钟滑动窗口错误计数器

**详情**:
```python
import time
from collections import deque

class ErrorCounter:
    WINDOW_SECONDS = 300  # 5分钟
    
    def __init__(self):
        self._errors: deque[float] = deque()
        self._total: deque[float] = deque()
    
    def record(self, is_error: bool):
        now = time.time()
        self._total.append(now)
        if is_error:
            self._errors.append(now)
        self._expire_old(now)
    
    def get_error_rate(self) -> float:
        now = time.time()
        self._expire_old(now)
        total = len(self._total)
        if total == 0:
            return 0.0
        return len(self._errors) / total
    
    def _expire_old(self, now: float):
        cutoff = now - self.WINDOW_SECONDS
        while self._errors and self._errors[0] < cutoff:
            self._errors.popleft()
        while self._total and self._total[0] < cutoff:
            self._total.popleft()
```

**验证**:
- [ ] 文件可导入
- [ ] `get_error_rate()` 初始返回 0.0
- [ ] 记录错误后返回正确错误率
- [ ] 5 分钟后旧数据自动过期

**依赖**: —

---

### 任务 8: 集成 ErrorCounter 到 SmartRouterMiddleware

**文件**: `core/smart_router/gateway/server.py`

**动作**: 在 SmartRouterMiddleware 中集成 ErrorCounter，并在 app.state 中初始化

**详情**:
- 导入 `ErrorCounter`
- 在 `start_server()` 中初始化：`app.state.error_counter = ErrorCounter()`
- 在 `SmartRouterMiddleware.dispatch()` 的响应处理中：
  ```python
  if request.url.path == "/v1/chat/completions":
      is_error = response.status_code >= 400
      request.app.state.error_counter.record(is_error)
  ```

**验证**:
- [ ] 服务正常启动
- [ ] 发送失败请求后 `error_counter.get_error_rate()` > 0
- [ ] 发送成功请求后错误率计算正确

**依赖**: 任务 7

---

### 任务 9: 编写 ErrorCounter 及中间件集成测试

**文件**: `core/smart_router/gateway/tests/test_server.py`（扩展）

**动作**: 为 ErrorCounter 和中间件集成编写测试

**详情**:
- 场景1: ErrorCounter 5 分钟内正确统计错误率
- 场景2: 5 分钟后旧错误自动过期
- 场景3: 中间件在 4xx/5xx 响应时记录错误
- 场景4: 中间件在 2xx 响应时不记录错误

**验证**:
- [ ] 所有测试可运行，先失败后通过

**依赖**: 任务 8

---

### 任务 10: 扩展前端 types + api client + store

**文件**:
- `frontend/src/types/index.ts`
- `frontend/src/api/client.ts`
- `frontend/src/store/useDashboardStore.ts`

**动作**: 新增 Analytics 相关类型、API 方法和 Store 状态

**详情**:
```typescript
// types/index.ts 新增
export interface AnalyticsSummary {
  total_cost: number | null
  total_requests: number
  total_tokens: number
  avg_daily_cost: number | null
  incomplete: boolean
}

export interface DailyTrend {
  date: string
  cost: number | null
  requests: number
  tokens: number
}

export interface ModelUsage {
  model: string
  prompt_tokens: number
  completion_tokens: number
  cost: number | null
  request_count: number
}

export interface TopModel {
  model: string
  total_tokens: number
  cost: number | null
  request_count: number
}
```

```typescript
// api/client.ts 新增
export const api = {
  // ... 现有方法
  getAnalyticsSummary: (days?: number) => client.get<AnalyticsSummary>('/api/analytics/summary', { params: { days } }).then(r => r.data),
  getAnalyticsDaily: (days?: number) => client.get<DailyTrend[]>('/api/analytics/daily', { params: { days } }).then(r => r.data),
  getAnalyticsByModel: (days?: number) => client.get<ModelUsage[]>('/api/analytics/by-model', { params: { days } }).then(r => r.data),
  getAnalyticsTopModels: (limit?: number, days?: number) => client.get<TopModel[]>('/api/analytics/top-models', { params: { limit, days } }).then(r => r.data),
}
```

```typescript
// useDashboardStore.ts 新增状态
interface DashboardState {
  // ... 现有状态
  analyticsSummary: AnalyticsSummary | null
  analyticsDaily: DailyTrend[]
  analyticsByModel: ModelUsage[]
  analyticsTopModels: TopModel[]
  // ... 新增 fetchAnalytics 方法
}
```

**验证**:
- [ ] TypeScript 编译无错误
- [ ] `npm run build` 通过

**依赖**: —

---

### 任务 11: 新建 SummaryCards 组件

**文件**: `frontend/src/components/SummaryCards.tsx`

**动作**: 创建 4 张指标卡片组件

**详情**:
- 展示：总成本、总请求、总 token、日均成本
- 成本显示格式：`¥12.50` 或 `$12.50`（根据 currency）
- `incomplete=true` 时成本旁显示 `*` 提示
- 使用现有 glass-card 样式

**验证**:
- [ ] 组件可渲染
- [ ] 空数据时显示 "--"
- [ ] incomplete 时显示提示

**依赖**: 任务 10

---

### 任务 12: 新建 CostTrendChart + RequestTrendChart 组件

**文件**:
- `frontend/src/components/CostTrendChart.tsx`
- `frontend/src/components/RequestTrendChart.tsx`

**动作**: 创建 Recharts AreaChart 趋势组件

**详情**:
```tsx
// CostTrendChart.tsx
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
// 数据: DailyTrend[]
// 双轴: cost (左轴) + requests (右轴，可选)
// 支持日/周/月切换（通过 days 参数控制）
```

```tsx
// RequestTrendChart.tsx
// 类似结构，展示请求数和 token 数趋势
```

**验证**:
- [ ] 空数据时显示 "暂无数据"
- [ ] 有数据时正确渲染面积图
- [ ] 响应式适配容器宽度

**依赖**: 任务 10

---

### 任务 13: 新建 ModelUsageChart + TopModelsTable 组件

**文件**:
- `frontend/src/components/ModelUsageChart.tsx`
- `frontend/src/components/TopModelsTable.tsx`

**动作**: 创建模型使用量对比图和 TOP10 表格

**详情**:
```tsx
// ModelUsageChart.tsx
// Recharts PieChart + 切换按钮（饼图/柱状图）
// 数据: ModelUsage[]
// 按 total_tokens 或 cost 排序
```

```tsx
// TopModelsTable.tsx
// 表格展示 TopModel[]
// 列: 排名、模型名、Token 数、成本、请求数
// 支持按列排序
```

**验证**:
- [ ] 饼图/柱状图切换正常
- [ ] 表格排序正常
- [ ] 空数据时显示占位符

**依赖**: 任务 10

---

### 任务 14: 新建 AnalyticsPage + 修改 App.tsx 导航

**文件**:
- `frontend/src/components/AnalyticsPage.tsx`（新建）
- `frontend/src/App.tsx`（修改）

**动作**: 组装 Analytics 页面，替换 TokenStats 标签页

**详情**:
```tsx
// AnalyticsPage.tsx
export function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <SummaryCards />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CostTrendChart />
        <RequestTrendChart />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ModelUsageChart />
        <TopModelsTable />
      </div>
    </div>
  )
}
```

```tsx
// App.tsx 修改
// 将 'token-stats' 标签改为 'analytics'
// 标签名改为"数据分析"
// 路由对应 <AnalyticsPage />
```

**验证**:
- [ ] 页面正常渲染
- [ ] 导航切换正常
- [ ] `npm run build` 通过

**依赖**: 任务 11, 12, 13

---

### 任务 15: 编写 Analytics 前端组件测试

**文件**:
- `frontend/src/components/SummaryCards.test.tsx`
- `frontend/src/components/CostTrendChart.test.tsx`
- `frontend/src/components/ModelUsageChart.test.tsx`
- `frontend/src/components/TopModelsTable.test.tsx`
- `frontend/src/components/AnalyticsPage.test.tsx`

**动作**: 为 Analytics 组件编写测试

**详情**:
- SummaryCards: 正常数据渲染、incomplete 提示、空数据显示 "--"
- CostTrendChart: 空数据占位符、有数据渲染
- ModelUsageChart: 图表切换交互
- TopModelsTable: 排序交互
- AnalyticsPage: 整体渲染

**验证**:
- [ ] `npm test` 通过
- [ ] 测试覆盖率合理

**依赖**: 任务 14

---

### 任务 16: 端到端验证批次1

**文件**: —

**动作**: 完整验证批次1功能

**详情**:
1. 启动服务：`SMART_ROUTER_MASTER_KEY=xxx smr start --foreground`
2. 发送若干 chat/completions 请求
3. 检查 `token_stats.json`：确认 `daily_records` 有数据
4. 访问 Dashboard → "数据分析" 页面
5. 验证：
   - SummaryCards 显示正确的总成本/请求/token
   - CostTrendChart 展示成本趋势
   - ModelUsageChart 展示模型占比
   - TopModelsTable 展示排名
6. 检查无单价模型的成本显示为 `--`

**验证**:
- [ ] 所有图表正常渲染
- [ ] 数据与请求一致
- [ ] `make test` 通过
- [ ] `make build-web` 通过

**依赖**: 任务 2, 4, 6, 9, 15

---

## 批次2：Playground 交互界面（任务 17-25）

### 任务 17: 新建 Playground API

**文件**: `core/smart_router/gateway/playground_api.py`（新建）

**动作**: 创建 Playground 后端 API

**详情**:
```python
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Literal

playground_router = APIRouter()

class PlaygroundRequest(BaseModel):
    mode: Literal["single", "compare"]
    prompt: str = Field(..., max_length=10000)
    models: list[str] = Field(..., min_length=1, max_length=3)
    stream: bool = False

class PlaygroundResult(BaseModel):
    model: str
    provider: str
    response: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    estimated_cost: float | None
    error: str | None
    routing_info: dict | None

@playground_router.post("/completions")
async def playground_completions(request: PlaygroundRequest) -> list[PlaygroundResult]:
    # 使用 asyncio.gather() 并发请求
    # 每个模型通过 litellm.acompletion() 调用
    # 超时 30 秒
    # stagger: 第 n 个模型等待 (n-1)*0.5s
    # 计算预估成本
    pass

@playground_router.get("/history")
async def playground_history() -> list[dict]:
    pass

@playground_router.delete("/history/{record_id}")
async def playground_delete_history(record_id: str) -> dict:
    pass
```

- 历史记录存储：`~/.smart-router/playground_history.json`（最多50条，FIFO）

**验证**:
- [ ] 路由可注册到 FastAPI app
- [ ] 单模型请求返回正确结果
- [ ] compare 模式返回多个结果
- [ ] 超时的模型返回 error

**依赖**: 任务 3（price 配置）

---

### 任务 18: 编写 Playground API 测试

**文件**: `core/smart_router/gateway/tests/test_playground_api.py`（新建）

**动作**: 为 Playground API 编写单元测试

**详情**:
- 场景1: single 模式返回单个结果
- 场景2: compare 模式并发请求 2 个模型
- 场景3: 超时的模型返回 error
- 场景4: 模型返回 4xx 时返回 error
- 场景5: 超过3个模型时验证失败
- 场景6: history CRUD 正常

**验证**:
- [ ] 所有测试可运行，先失败后通过

**依赖**: 任务 17

---

### 任务 19: 注册 Playground Router 到 Dashboard App

**文件**: `core/smart_router/gateway/dashboard_api.py`

**动作**: 在 `build_dashboard_app()` 中注册 Playground router

**详情**:
```python
from .playground_api import playground_router

def build_dashboard_app(...):
    # ... 现有路由
    app.include_router(playground_router, prefix="/api/playground")
    return app
```

**验证**:
- [ ] `/api/playground/completions` 可访问
- [ ] 不影响现有 API

**依赖**: 任务 17

---

### 任务 20: 扩展前端 types + api client + store（Playground）

**文件**:
- `frontend/src/types/index.ts`
- `frontend/src/api/client.ts`
- `frontend/src/store/useDashboardStore.ts`

**动作**: 新增 Playground 相关类型、API 和 Store 状态

**详情**:
```typescript
// types
export interface PlaygroundRequest {
  mode: 'single' | 'compare'
  prompt: string
  models: string[]
}

export interface PlaygroundResult {
  model: string
  provider: string
  response: string
  latency_ms: number
  prompt_tokens: number
  completion_tokens: number
  estimated_cost: number | null
  error: string | null
  routing_info: DryRunResult | null
}

export interface PlaygroundRecord {
  id: string
  timestamp: string
  mode: 'single' | 'compare'
  prompt: string
  results: PlaygroundResult[]
}
```

```typescript
// api/client.ts
playgroundCompletions: (data: PlaygroundRequest) => ...
playgroundHistory: () => ...
playgroundDeleteHistory: (id: string) => ...
```

```typescript
// store
playgroundResults: PlaygroundResult[]
playgroundHistory: PlaygroundRecord[]
playgroundMode: 'single' | 'compare'
runPlayground: (...) => Promise<void>
```

**验证**:
- [ ] TypeScript 编译无错误
- [ ] `npm run build` 通过

**依赖**: —

---

### 任务 21: 新建 PlaygroundInput + PlaygroundResult 组件

**文件**:
- `frontend/src/components/PlaygroundInput.tsx`
- `frontend/src/components/PlaygroundResult.tsx`

**动作**: 创建输入区和单模型结果展示组件

**详情**:
```tsx
// PlaygroundInput.tsx
// PromptTextarea + ModelSelector（多选复选框，最多3个）+ ModeToggle（单选按钮）+ 提交按钮
// prompt maxLength=10000
```

```tsx
// PlaygroundResult.tsx
// 全宽展示：响应文本 + MetaBar（延迟、token、预估成本）+ RoutingInfo（复用 DryRunPanel 样式）
```

**验证**:
- [ ] 模型多选限制最多3个
- [ ] 提交后显示加载状态
- [ ] 响应正常渲染

**依赖**: 任务 20

---

### 任务 22: 新建 PlaygroundCompare + PlaygroundModelCard 组件

**文件**:
- `frontend/src/components/PlaygroundCompare.tsx`
- `frontend/src/components/PlaygroundModelCard.tsx`

**动作**: 创建多模型对比组件

**详情**:
```tsx
// PlaygroundCompare.tsx
// 2-3 栏并列布局（grid-cols-2 或 grid-cols-3）
// 每栏一个 PlaygroundModelCard
```

```tsx
// PlaygroundModelCard.tsx
// 模型名标题 + ResponseText + MetaBar + RoutingInfo
// error 状态时显示错误信息（红色）
```

**验证**:
- [ ] 2 个模型时 2 栏布局
- [ ] 3 个模型时 3 栏布局
- [ ] 错误模型显示红色错误信息

**依赖**: 任务 21

---

### 任务 23: 新建 PlaygroundPage + 修改 App.tsx 导航

**文件**:
- `frontend/src/components/PlaygroundPage.tsx`（新建）
- `frontend/src/App.tsx`（修改）

**动作**: 组装 Playground 页面，添加导航标签

**详情**:
```tsx
// PlaygroundPage.tsx
export function PlaygroundPage() {
  const { playgroundMode, playgroundResults } = useDashboardStore()
  return (
    <div className="space-y-6">
      <PlaygroundInput />
      {playgroundMode === 'single' ? (
        playgroundResults.length > 0 && <PlaygroundResult result={playgroundResults[0]} />
      ) : (
        <PlaygroundCompare results={playgroundResults} />
      )}
    </div>
  )
}
```

```tsx
// App.tsx 新增 'playground' 标签
```

**验证**:
- [ ] 页面正常渲染
- [ ] 单模型/对比模式切换正常
- [ ] `npm run build` 通过

**依赖**: 任务 21, 22

---

### 任务 24: 编写 Playground 组件测试

**文件**:
- `frontend/src/components/PlaygroundInput.test.tsx`
- `frontend/src/components/PlaygroundCompare.test.tsx`
- `frontend/src/components/PlaygroundPage.test.tsx`

**动作**: 为 Playground 组件编写测试

**详情**:
- PlaygroundInput: 模型多选限制、提交交互
- PlaygroundCompare: 多栏渲染、错误状态显示
- PlaygroundPage: 模式切换、整体渲染

**验证**:
- [ ] `npm test` 通过

**依赖**: 任务 23

---

### 任务 25: 端到端验证批次2

**文件**: —

**动作**: 完整验证 Playground 功能

**详情**:
1. 访问 Dashboard → "Playground" 页面
2. 单模型测试：输入提示词，选择1个模型，提交，验证响应展示
3. 多模型对比：选择2个模型，提交，验证2栏并列展示
4. 验证延迟、token、预估成本显示正确
5. 验证路由决策详情展示
6. 检查 playground_history.json 有记录

**验证**:
- [ ] 单模型测试正常
- [ ] 多模型对比正常
- [ ] 历史记录持久化
- [ ] `make test` 通过
- [ ] `make build-web` 通过

**依赖**: 任务 18, 24

---

## 批次3：告警系统（任务 26-39）

### 任务 26: 新建 Alert 配置解析模块

**文件**:
- `core/smart_router/alerts/__init__.py`（新建）
- `core/smart_router/alerts/config.py`（新建）

**动作**: 创建 alerts.yaml 解析和验证模块

**详情**:
```python
# alerts/config.py
from pydantic import BaseModel, Field
from typing import Literal
from pathlib import Path
import yaml

class AlertCondition(BaseModel):
    metric: Literal["daily_cost", "daily_requests", "daily_tokens", "error_rate"]
    operator: Literal[">", "<", ">=", "<="]
    threshold: float

class AlertChannel(BaseModel):
    type: Literal["webhook", "log"]
    url: str | None = None

class AlertRule(BaseModel):
    id: str
    name: str
    enabled: bool = True
    condition: AlertCondition
    severity: Literal["info", "warning", "critical"] = "warning"
    time_window: str = "1d"
    channels: list[AlertChannel] = Field(default_factory=list)
    cooldown_minutes: int = 60

class AlertConfig:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.rules: list[AlertRule] = []
        self._load()
    
    def _load(self):
        if self.config_path.exists():
            data = yaml.safe_load(self.config_path.read_text())
            for item in data.get("alerts", []):
                try:
                    self.rules.append(AlertRule(**item))
                except Exception as e:
                    logger.warning(f"Invalid alert rule: {e}")
    
    def save(self):
        data = {"alerts": [r.model_dump() for r in self.rules]}
        self.config_path.write_text(yaml.safe_dump(data, allow_unicode=True))
```

**验证**:
- [ ] 正常 alerts.yaml 正确解析
- [ ] 错误规则被跳过，不阻断
- [ ] save() 后文件可重新加载

**依赖**: —

---

### 任务 27: 编写 Alert 配置测试

**文件**: `core/smart_router/alerts/tests/test_config.py`（新建）

**动作**: 为 AlertConfig 编写测试

**详情**:
- 场景1: 正常 alerts.yaml 解析
- 场景2: 缺少必填字段的规则被跳过
- 场景3: webhook url 为 http:// 时验证失败
- 场景4: save() 后重新加载一致

**验证**:
- [ ] 所有测试可运行，先失败后通过

**依赖**: 任务 26

---

### 任务 28: 新建 AlertChecker

**文件**: `core/smart_router/alerts/checker.py`（新建）

**动作**: 创建告警检查器

**详情**:
```python
class AlertChecker:
    def __init__(self, config: AlertConfig, token_stats: TokenStats, error_counter: ErrorCounter):
        self.config = config
        self.token_stats = token_stats
        self.error_counter = error_counter
        self._last_triggered: dict[str, float] = {}  # rule_id -> timestamp
    
    async def check_all(self) -> list[AlertTrigger]:
        triggers = []
        for rule in self.config.rules:
            if not rule.enabled:
                continue
            if self._is_in_cooldown(rule):
                continue
            
            current_value = self._get_metric_value(rule)
            if current_value is None:
                continue
            
            if self._evaluate_condition(current_value, rule.condition):
                trigger = AlertTrigger(
                    rule_id=rule.id,
                    timestamp=datetime.utcnow().isoformat(),
                    metric=rule.condition.metric,
                    current_value=current_value,
                    threshold=rule.condition.threshold,
                )
                triggers.append(trigger)
                self._last_triggered[rule.id] = time.time()
        return triggers
    
    def _get_metric_value(self, rule: AlertRule) -> float | None:
        metric = rule.condition.metric
        if metric == "error_rate":
            return self.error_counter.get_error_rate()
        # daily_cost, daily_requests, daily_tokens: 读取 daily_records 按 time_window 汇总
        days = self._parse_time_window(rule.time_window)
        summary = self.token_stats.get_summary(days)
        return summary.get(metric)
    
    def _is_in_cooldown(self, rule: AlertRule) -> bool:
        last = self._last_triggered.get(rule.id)
        if not last:
            return False
        return (time.time() - last) < (rule.cooldown_minutes * 60)
```

**验证**:
- [ ] 正常规则正确触发
- [ ] 冷却期内不重复触发
- [ ] 禁用规则被跳过
- [ ] error_rate 正确读取

**依赖**: 任务 26

---

### 任务 29: 编写 AlertChecker 测试

**文件**: `core/smart_router/alerts/tests/test_checker.py`（新建）

**动作**: 为 AlertChecker 编写测试

**详情**:
- 场景1: 条件满足时触发告警
- 场景2: 条件不满足时不触发
- 场景3: 冷却期内不重复触发
- 场景4: 禁用规则不触发
- 场景5: error_rate 告警正常

**验证**:
- [ ] 所有测试可运行，先失败后通过

**依赖**: 任务 28

---

### 任务 30: 新建 AlertNotifier

**文件**: `core/smart_router/alerts/notifier.py`（新建）

**动作**: 创建告警通知器

**详情**:
```python
import httpx
import logging

logger = logging.getLogger(__name__)

class AlertNotifier:
    async def send(self, rule: AlertRule, trigger: AlertTrigger, channel: AlertChannel):
        if channel.type == "webhook":
            await self._send_webhook(rule, trigger, channel)
        elif channel.type == "log":
            self._send_log(rule, trigger)
    
    async def _send_webhook(self, rule, trigger, channel):
        payload = {
            "alert_name": rule.name,
            "severity": rule.severity,
            "metric": trigger.metric,
            "current_value": trigger.current_value,
            "threshold": trigger.threshold,
            "timestamp": trigger.timestamp,
            "message": f"Smart Router 告警：{rule.name}，当前值 {trigger.current_value}，阈值 {trigger.threshold}",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(channel.url, json=payload)
                resp.raise_for_status()
                return {"status": "success"}
        except Exception as e:
            logger.error(f"Webhook failed: {e}")
            self._send_log(rule, trigger)  # 回退到日志
            return {"status": "failed", "error": str(e)}
    
    def _send_log(self, rule, trigger):
        logger.warning(
            f"[ALERT] {rule.name}: {trigger.metric}={trigger.current_value} {rule.condition.operator} threshold={trigger.threshold}"
        )
```

**验证**:
- [ ] Webhook 发送成功
- [ ] Webhook 失败时回退到日志
- [ ] 日志输出格式正确

**依赖**: —

---

### 任务 31: 编写 AlertNotifier 测试

**文件**: `core/smart_router/alerts/tests/test_notifier.py`（新建）

**动作**: 为 AlertNotifier 编写测试

**详情**:
- 场景1: Webhook 发送成功（mock httpx）
- 场景2: Webhook 失败时回退到日志
- 场景3: 日志通道正常输出

**验证**:
- [ ] 所有测试可运行，先失败后通过

**依赖**: 任务 30

---

### 任务 32: 新增 Alert API 端点

**文件**: `core/smart_router/gateway/dashboard_api.py`

**动作**: 新增 Alert 相关 API 端点

**详情**:
```python
# 在 dashboard_api.py 中新增
async def list_alert_rules() -> dict
async def create_alert_rule(request: AlertRule) -> dict
async def update_alert_rule(rule_id: str, request: AlertRule) -> dict
async def delete_alert_rule(rule_id: str) -> dict
async def list_alert_history(limit: int = 50) -> dict
async def test_alert_channel(request: dict) -> dict
```

端点注册:
```python
app.get("/api/alerts/rules")(list_alert_rules)
app.post("/api/alerts/rules")(create_alert_rule)
app.put("/api/alerts/rules/{rule_id}")(update_alert_rule)
app.delete("/api/alerts/rules/{rule_id}")(delete_alert_rule)
app.get("/api/alerts/history")(list_alert_history)
app.post("/api/alerts/test")(test_alert_channel)
```

**验证**:
- [ ] 所有端点可访问
- [ ] CRUD 操作正常
- [ ] 测试通道发送测试消息

**依赖**: 任务 26, 30

---

### 任务 33: 编写 Alert API 测试

**文件**: `core/smart_router/gateway/tests/test_alerts_api.py`（新建）

**动作**: 为 Alert API 编写测试

**详情**:
- 场景1: 获取规则列表
- 场景2: 创建规则
- 场景3: 修改规则
- 场景4: 删除规则
- 场景5: 获取告警历史
- 场景6: 测试通道发送测试消息

**验证**:
- [ ] 所有测试可运行，先失败后通过

**依赖**: 任务 32

---

### 任务 34: 集成 AlertChecker 到 server.py

**文件**: `core/smart_router/gateway/server.py`

**动作**: 在 server.py 中启动 AlertChecker 后台协程

**详情**:
```python
from ..alerts.config import AlertConfig
from ..alerts.checker import AlertChecker
from ..alerts.notifier import AlertNotifier

async def alert_check_loop(checker: AlertChecker, notifier: AlertNotifier, config: AlertConfig):
    while True:
        try:
            triggers = await checker.check_all()
            for trigger in triggers:
                rule = next(r for r in config.rules if r.id == trigger.rule_id)
                for channel in rule.channels:
                    await notifier.send(rule, trigger, channel)
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Alert check error: {e}")
            await asyncio.sleep(60)

# 在 start_server() 中
alert_config = AlertConfig(config_dir / "alerts.yaml")
alert_checker = AlertChecker(alert_config, app.state.token_stats, app.state.error_counter)
alert_notifier = AlertNotifier()
# 启动后台协程
asyncio.create_task(alert_check_loop(alert_checker, alert_notifier, alert_config))
```

**验证**:
- [ ] 服务启动时 AlertChecker 正常初始化
- [ ] 后台协程每 60 秒执行一次
- [ ] 异常时不阻断主服务

**依赖**: 任务 28, 30

---

### 任务 35: 扩展前端 types + api client + store（Alerts）

**文件**:
- `frontend/src/types/index.ts`
- `frontend/src/api/client.ts`
- `frontend/src/store/useDashboardStore.ts`

**动作**: 新增 Alert 相关类型、API 和 Store 状态

**详情**:
```typescript
// types
export interface AlertRule {
  id: string
  name: string
  enabled: boolean
  condition: { metric: string; operator: string; threshold: number }
  severity: 'info' | 'warning' | 'critical'
  time_window: string
  channels: AlertChannel[]
  cooldown_minutes: number
}

export interface AlertChannel {
  type: 'webhook' | 'log'
  url?: string
}

export interface AlertHistoryItem {
  id: string
  rule_id: string
  rule_name: string
  severity: string
  metric: string
  current_value: number
  threshold: number
  timestamp: string
  status: 'success' | 'failed'
  channel_type: string
}
```

```typescript
// api
getAlertRules: () => ...
createAlertRule: (rule: AlertRule) => ...
updateAlertRule: (id: string, rule: AlertRule) => ...
deleteAlertRule: (id: string) => ...
getAlertHistory: (limit?: number) => ...
testAlertChannel: (channel: AlertChannel) => ...
```

```typescript
// store
alertRules: AlertRule[]
alertHistory: AlertHistoryItem[]
fetchAlertRules: () => Promise<void>
saveAlertRule: (...) => Promise<void>
deleteAlertRule: (...) => Promise<void>
testAlertChannel: (...) => Promise<void>
```

**验证**:
- [ ] TypeScript 编译无错误
- [ ] `npm run build` 通过

**依赖**: —

---

### 任务 36: 新建 Alert 前端组件

**文件**:
- `frontend/src/components/AlertSummaryCard.tsx`
- `frontend/src/components/AlertRulesTable.tsx`
- `frontend/src/components/AlertRuleEditor.tsx`
- `frontend/src/components/AlertHistoryTable.tsx`

**动作**: 创建告警管理前端组件

**详情**:
```tsx
// AlertSummaryCard.tsx
// 2 张卡片：活跃规则数、今日触发数
```

```tsx
// AlertRulesTable.tsx
// 表格：规则名、metric、阈值、状态、启用/禁用开关、编辑/删除按钮
```

```tsx
// AlertRuleEditor.tsx
// 表单：规则名、metric 下拉、operator 下拉、阈值、severity、time_window、channels（动态添加 webhook/log）
// 新增/编辑共用
```

```tsx
// AlertHistoryTable.tsx
// 表格：规则名、severity、metric、当前值、阈值、时间、状态
```

**验证**:
- [ ] 表格渲染正常
- [ ] 启用/禁用开关交互正常
- [ ] 表单验证正常

**依赖**: 任务 35

---

### 任务 37: 新建 AlertsPage + 修改 App.tsx 导航

**文件**:
- `frontend/src/components/AlertsPage.tsx`（新建）
- `frontend/src/App.tsx`（修改）

**动作**: 组装 Alerts 页面，添加导航标签

**详情**:
```tsx
// AlertsPage.tsx
export function AlertsPage() {
  return (
    <div className="space-y-6">
      <AlertSummaryCard />
      <div className="flex justify-end">
        <button onClick={() => setEditingRule(null)}>新增规则</button>
      </div>
      <AlertRulesTable />
      {editingRule !== undefined && <AlertRuleEditor rule={editingRule} />}
      <AlertHistoryTable />
    </div>
  )
}
```

**验证**:
- [ ] 页面正常渲染
- [ ] 新增/编辑/删除规则交互正常
- [ ] `npm run build` 通过

**依赖**: 任务 36

---

### 任务 38: 编写 Alert 前端组件测试

**文件**:
- `frontend/src/components/AlertRulesTable.test.tsx`
- `frontend/src/components/AlertRuleEditor.test.tsx`
- `frontend/src/components/AlertsPage.test.tsx`

**动作**: 为 Alert 组件编写测试

**详情**:
- AlertRulesTable: 规则列表渲染、启用/禁用开关
- AlertRuleEditor: 表单验证、提交
- AlertsPage: 整体渲染、新增规则弹窗

**验证**:
- [ ] `npm test` 通过

**依赖**: 任务 37

---

### 任务 39: 端到端验证批次3 + 更新 ROADMAP

**文件**:
- `docs/ROADMAP.md`（修改）

**动作**: 完整验证告警系统，更新 ROADMAP 标记 P0 完成

**详情**:
1. 访问 Dashboard → "告警" 页面
2. 新增一条规则：`daily_cost > 0.01`
3. 发送 chat/completions 请求产生成本
4. 等待 60 秒或手动触发检查
5. 验证：
   - 告警历史中有触发记录
   - Webhook 收到正确 payload（如配置了测试 webhook）
   - `alerts.log` 中有告警日志
6. 测试冷却期：同一规则短时间内不重复触发
7. 测试禁用：禁用规则后不触发

**更新 ROADMAP**:
```markdown
### 7.2 功能优先级排序
| 优先级 | 功能 | ... |
| **P0** | 高级分析仪表盘 | ... | ✅ 已完成 |
| **P0** | Playground 交互界面 | ... | ✅ 已完成 |
| **P0** | 告警系统 | ... | ✅ 已完成 |
```

**验证**:
- [ ] 告警正常触发
- [ ] Webhook/日志通道正常
- [ ] 冷却期生效
- [ ] ROADMAP 已更新
- [ ] `make test` 通过
- [ ] `make build-web` 通过

**依赖**: 任务 27, 29, 31, 33, 38

---

## 深度自检

### 自检清单

| # | 检查项 | 状态 |
|---|--------|------|
| 1 | **完整性** | ✅ 无 TODO、无占位符 |
| 2 | **Spec 对齐** | ✅ 所有 Spec 需求都有对应任务 |
| 3 | **任务分解** | ✅ 每个任务 2-5 分钟 |
| 4 | **可构建性** | ✅ 文件路径明确、详情足够 |
| 5 | **验收标准覆盖** | ✅ 33 条验收标准全部覆盖 |
| 6 | **明确性** | ✅ 每个任务有文件路径、详情、验证步骤 |
| 7 | **可验证性** | ✅ 验证步骤可执行、可判断 |
| 8 | **顺序合理性** | ✅ 依赖正确、实现+测试成对相邻、基础优先 |

### 验收标准对照

**批次1（12项）**:
- [x] v1→v2 自动升级 → 任务 1, 2
- [x] price 字段支持 → 任务 3, 4
- [x] 4 个 analytics 端点 → 任务 5, 6
- [x] 前端图表 → 任务 11-15
- [x] 测试覆盖 → 任务 2, 4, 6, 9, 15

**批次2（10项）**:
- [x] Playground API → 任务 17, 18
- [x] 单/多模型测试 → 任务 17, 18
- [x] 结果字段完整 → 任务 17
- [x] 超时/错误处理 → 任务 17, 18
- [x] 历史记录 → 任务 17
- [x] 前端页面 → 任务 21-24

**批次3（11项）**:
- [x] 告警规则配置 → 任务 26, 27
- [x] metrics 支持 → 任务 28, 29
- [x] Webhook/日志通道 → 任务 30, 31
- [x] 告警历史 → 任务 32, 33
- [x] 冷却期 → 任务 28, 29
- [x] 前端页面 → 任务 36-38
- [x] ROADMAP 更新 → 任务 39

---

## 分批执行建议

由于任务数 39 > 20，建议分 3 批调用子 Agent 执行：

| 批次 | 任务范围 | 任务数 | 说明 |
|------|---------|--------|------|
| 执行1 | 任务 1-16 | 16 | 高级分析仪表盘（数据层） |
| 执行2 | 任务 17-25 | 9 | Playground 交互界面 |
| 执行3 | 任务 26-39 | 14 | 告警系统 |
