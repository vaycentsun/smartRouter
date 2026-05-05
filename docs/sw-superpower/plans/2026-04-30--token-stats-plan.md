# Token 统计功能实现计划

**日期**: 2026-04-30
**对应 Spec**: `docs/sw-superpower/specs/2026-04-30--token-stats.md`
**任务数**: 16
**预计总时间**: 60-80 分钟

---

## 任务概览

| 编号 | 任务 | 文件 | 依赖 |
|------|------|------|------|
| 1 | 创建 TokenStats 类 | `core/smart_router/utils/token_stats.py` | - |
| 2 | 编写 TokenStats 单元测试 | `core/smart_router/utils/tests/test_token_stats.py` | 1 |
| 3 | 修改 server.py 中间件 | `core/smart_router/gateway/server.py` | 1 |
| 4 | 补充 server.py 中间件测试 | `core/smart_router/gateway/tests/test_server.py` | 3 |
| 5 | 修改 dashboard_api.py | `core/smart_router/gateway/dashboard_api.py` | 1 |
| 6 | 补充 dashboard_api 测试 | `core/smart_router/gateway/tests/test_dashboard_api.py` | 5 |
| 7 | 新增 TokenStats 类型 | `frontend/src/types/index.ts` | - |
| 8 | 新增 getTokenStats API | `frontend/src/api/client.ts` | 7 |
| 9 | 修改 Dashboard Store | `frontend/src/store/useDashboardStore.ts` | 7, 8 |
| 10 | 创建 TokenStatsOverview | `frontend/src/components/TokenStatsOverview.tsx` | 7 |
| 11 | 创建 TokenStatsTable | `frontend/src/components/TokenStatsTable.tsx` | 7 |
| 12 | 编写 TokenStatsTable 测试 | `frontend/src/components/TokenStatsTable.test.tsx` | 11 |
| 13 | 创建 TokenStatsChart | `frontend/src/components/TokenStatsChart.tsx` | 7 |
| 14 | 创建 TokenStatsPage | `frontend/src/components/TokenStatsPage.tsx` | 10, 11, 13 |
| 15 | 修改 App.tsx | `frontend/src/App.tsx` | 14 |
| 16 | 编写 TokenStatsPage 测试 | `frontend/src/components/TokenStatsPage.test.tsx` | 14, 15 |

---

## 后端任务

### 任务 1: 创建 TokenStats 类

**目标**: 创建 `TokenStats` 类，支持 JSON 文件持久化的 token 统计

**文件**: `core/smart_router/utils/token_stats.py`

**内容**:
```python
"""Token 使用量统计 — JSON 文件持久化

数据存储在 ~/.smart-router/token_stats.json，采用原子写入。
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional
import asyncio

DEFAULT_STATS_FILE = Path.home() / ".smart-router" / "token_stats.json"
logger = logging.getLogger(__name__)


class TokenStats:
    def __init__(self, stats_file: Optional[Path] = None):
        self.stats_file = stats_file or DEFAULT_STATS_FILE
        self._data: dict = {}
        self._lock = asyncio.Lock()
        self._load()

    def _load(self):
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        self._data = json.loads(content)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Token stats file corrupted or unreadable: {e}. Starting fresh.")
                self._data = {}
        if "records" not in self._data:
            self._data["records"] = {}
        if "version" not in self._data:
            self._data["version"] = 1

    def _save(self):
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.stats_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.stats_file)

    async def record(
        self, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int
    ):
        async with self._lock:
            records = self._data.setdefault("records", {})
            if model not in records:
                records[model] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "request_count": 0,
                }
            entry = records[model]
            entry["prompt_tokens"] += prompt_tokens
            entry["completion_tokens"] += completion_tokens
            entry["total_tokens"] += total_tokens
            entry["request_count"] += 1
            self._data["_meta"] = {
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            self._save()

    def get_all(self) -> dict:
        return dict(self._data.get("records", {}))

    def reset(self):
        """仅供测试使用：清空所有统计数据"""
        self._data = {"version": 1, "records": {}}
        if self.stats_file.exists():
            self.stats_file.unlink()
```

**验证**:
- [ ] 文件可被 Python 导入
- [ ] `TokenStats()` 实例化成功
- [ ] `record()` 累加数据正确
- [ ] `get_all()` 返回正确格式

---

### 任务 2: 编写 TokenStats 单元测试

**目标**: 为 `TokenStats` 类编写全面的单元测试

**文件**: `core/smart_router/utils/tests/test_token_stats.py`

**测试用例**:
```python
import pytest
import asyncio
import json
from pathlib import Path
from smart_router.utils.token_stats import TokenStats


class TestTokenStats:
    def test_load_empty_file(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        stats_file.write_text("")
        ts = TokenStats(stats_file=stats_file)
        assert ts.get_all() == {}

    def test_load_nonexistent_file(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        assert ts.get_all() == {}
        assert ts._data["version"] == 1

    def test_record_single_model(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        asyncio.run(ts.record("gpt-4o", 100, 50, 150))
        
        all_stats = ts.get_all()
        assert all_stats["gpt-4o"]["prompt_tokens"] == 100
        assert all_stats["gpt-4o"]["completion_tokens"] == 50
        assert all_stats["gpt-4o"]["total_tokens"] == 150
        assert all_stats["gpt-4o"]["request_count"] == 1

    def test_record_multiple_models(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        asyncio.run(ts.record("gpt-4o", 100, 50, 150))
        asyncio.run(ts.record("claude-3-sonnet", 200, 100, 300))
        asyncio.run(ts.record("gpt-4o", 50, 25, 75))
        
        all_stats = ts.get_all()
        assert all_stats["gpt-4o"]["prompt_tokens"] == 150
        assert all_stats["gpt-4o"]["request_count"] == 2
        assert all_stats["claude-3-sonnet"]["request_count"] == 1

    def test_persistence(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts1 = TokenStats(stats_file=stats_file)
        asyncio.run(ts1.record("gpt-4o", 100, 50, 150))
        
        # 重新实例化，验证数据恢复
        ts2 = TokenStats(stats_file=stats_file)
        all_stats = ts2.get_all()
        assert all_stats["gpt-4o"]["prompt_tokens"] == 100
        assert all_stats["gpt-4o"]["request_count"] == 1

    def test_file_schema(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        asyncio.run(ts.record("gpt-4o", 100, 50, 150))
        
        content = json.loads(stats_file.read_text())
        assert content["version"] == 1
        assert "records" in content
        assert "_meta" in content
        assert "last_updated" in content["_meta"]

    def test_concurrent_record(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        
        async def worker():
            for _ in range(10):
                await ts.record("gpt-4o", 1, 1, 2)
        
        async def run():
            await asyncio.gather(*[worker() for _ in range(5)])
        
        asyncio.run(run())
        all_stats = ts.get_all()
        assert all_stats["gpt-4o"]["request_count"] == 50
        assert all_stats["gpt-4o"]["total_tokens"] == 100

    def test_reset(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        asyncio.run(ts.record("gpt-4o", 100, 50, 150))
        ts.reset()
        assert ts.get_all() == {}
        assert not stats_file.exists()

    def test_corrupted_file(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        stats_file.write_text("not valid json")
        ts = TokenStats(stats_file=stats_file)
        assert ts.get_all() == {}
```

**验证**:
- [ ] `pytest core/smart_router/utils/tests/test_token_stats.py -v` 全部通过
- [ ] 测试先失败（RED）→ 任务1完成后通过（GREEN）

---

### 任务 3: 修改 server.py 中间件

**目标**: 在 `SmartRouterMiddleware` 中增加 token 统计数据采集，在 `start_server()` 中初始化 `TokenStats`

**文件**: `core/smart_router/gateway/server.py`

**修改 3a - 在 `start_server()` 中初始化 TokenStats**：

找到代码块 `app.state.smart_router = router`，在其后插入：
```python
        app.state.smart_router = router
        
        # 初始化 Token 统计
        from ..utils.token_stats import TokenStats
        app.state.token_stats = TokenStats()
```

**修改 3b - 在 `SmartRouterMiddleware.dispatch()` 响应阶段增加 usage 拦截**：

找到 `SmartRouterMiddleware.dispatch` 方法的末尾，在 `return response` 之前插入以下代码块：

```python
        # Token 统计：拦截 chat/completions 响应
        if request.url.path == "/v1/chat/completions" and request.method == "POST":
            content_type = response.headers.get("content-type", "")
            if "text/event-stream" not in content_type:
                try:
                    # 确定统计模型名（按优先级）
                    model_name = getattr(request.state, 'smart_router_selected', None)
                    if not model_name:
                        model_name = getattr(request.state, 'smart_router_override_model', None)
                    if not model_name:
                        # 回退：从请求体解析原始 model 字段
                        try:
                            req_body = await request.body()
                            if req_body:
                                req_data = json.loads(req_body)
                                model_name = req_data.get("model", None)
                        except Exception:
                            pass
                    
                    if model_name:
                        # 消费响应 body
                        body_bytes = b""
                        async for chunk in response.body_iterator:
                            body_bytes += chunk
                        
                        # 解析 usage
                        resp_data = json.loads(body_bytes)
                        usage = resp_data.get("usage", {})
                        if usage:
                            prompt_tokens = usage.get("prompt_tokens", 0)
                            completion_tokens = usage.get("completion_tokens", 0)
                            total_tokens = usage.get("total_tokens", 0)
                            
                            token_stats = request.app.state.token_stats
                            await token_stats.record(
                                model_name, prompt_tokens, completion_tokens, total_tokens
                            )
                        
                        # 重建 Response，确保下游正常消费
                        from starlette.responses import Response
                        response = Response(
                            content=body_bytes,
                            status_code=response.status_code,
                            headers=dict(response.headers),
                            media_type=response.media_type,
                        )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Token stats recording failed: {e}")
        
        return response
```

**验证**:
- [ ] `python -c "from smart_router.gateway.server import SmartRouterMiddleware, start_server; print('OK')"` 可导入
- [ ] 启动服务不报错

---

### 任务 4: 补充 server.py 中间件测试

**目标**: 测试中间件对 usage 的正确拦截和记录

**文件**: `core/smart_router/gateway/tests/test_server.py`

**测试用例**:
```python
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.requests import Request
from starlette.responses import Response


class TestTokenStatsMiddleware:
    @pytest.fixture
    def mock_router(self):
        router = MagicMock()
        router.sr_config = MagicMock()
        return router

    @pytest.mark.asyncio
    async def test_middleware_records_usage(self, mock_router, tmp_path):
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.token_stats import TokenStats
        
        # 创建临时 TokenStats
        stats_file = tmp_path / "token_stats.json"
        token_stats = TokenStats(stats_file=stats_file)
        
        # 构建 call_next mock（返回 Response 对象）
        async def mock_call_next(request):
            return Response(
                content=json.dumps({
                    "id": "test",
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
                }).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )
        
        app = MagicMock()
        app.state = MagicMock()
        app.state.token_stats = token_stats
        
        middleware = SmartRouterMiddleware(app, router=mock_router)
        
        # 构建请求
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }
        
        async def receive():
            return {"type": "http.request", "body": b'{}', "more_body": False}
        
        async def send(message):
            pass
        
        request = Request(scope, receive, send)
        request.state.smart_router_selected = "gpt-4o"
        
        response = await middleware.dispatch(request, mock_call_next)
        
        # 验证统计已记录
        all_stats = token_stats.get_all()
        assert "gpt-4o" in all_stats
        assert all_stats["gpt-4o"]["prompt_tokens"] == 100
        assert all_stats["gpt-4o"]["request_count"] == 1

    @pytest.mark.asyncio
    async def test_middleware_uses_override_model(self, mock_router, tmp_path):
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.token_stats import TokenStats
        
        stats_file = tmp_path / "token_stats.json"
        token_stats = TokenStats(stats_file=stats_file)
        
        async def mock_call_next(request):
            return Response(
                content=json.dumps({
                    "usage": {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300}
                }).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )
        
        app = MagicMock()
        app.state = MagicMock()
        app.state.token_stats = token_stats
        
        middleware = SmartRouterMiddleware(app, router=mock_router)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }
        
        async def receive():
            return {"type": "http.request", "body": b'{}', "more_body": False}
        
        async def send(message):
            pass
        
        request = Request(scope, receive, send)
        request.state.smart_router_override_model = "claude-3-sonnet"
        
        response = await middleware.dispatch(request, mock_call_next)
        
        all_stats = token_stats.get_all()
        assert "claude-3-sonnet" in all_stats
        assert all_stats["claude-3-sonnet"]["request_count"] == 1

    @pytest.mark.asyncio
    async def test_middleware_uses_request_body_model(self, mock_router, tmp_path):
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.token_stats import TokenStats
        
        stats_file = tmp_path / "token_stats.json"
        token_stats = TokenStats(stats_file=stats_file)
        
        async def mock_call_next(request):
            return Response(
                content=json.dumps({
                    "usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75}
                }).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )
        
        app = MagicMock()
        app.state = MagicMock()
        app.state.token_stats = token_stats
        
        middleware = SmartRouterMiddleware(app, router=mock_router)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }
        
        async def receive():
            return {"type": "http.request", "body": b'{"model": "gpt-3.5-turbo"}', "more_body": False}
        
        async def send(message):
            pass
        
        request = Request(scope, receive, send)
        # 不设置 smart_router_selected 或 override_model
        
        response = await middleware.dispatch(request, mock_call_next)
        
        all_stats = token_stats.get_all()
        assert "gpt-3.5-turbo" in all_stats
        assert all_stats["gpt-3.5-turbo"]["request_count"] == 1

    @pytest.mark.asyncio
    async def test_middleware_skips_streaming(self, mock_router):
        from smart_router.gateway.server import SmartRouterMiddleware
        
        async def mock_call_next(request):
            return Response(content=b"", status_code=200, headers={"content-type": "text/event-stream"})
        
        app = MagicMock()
        app.state = MagicMock()
        app.state.token_stats = MagicMock()
        
        middleware = SmartRouterMiddleware(app, router=mock_router)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }
        
        async def receive():
            return {"type": "http.request", "body": b'{}', "more_body": False}
        
        async def send(message):
            pass
        
        request = Request(scope, receive, send)
        request.state.smart_router_selected = "gpt-4o"
        
        response = await middleware.dispatch(request, mock_call_next)
        
        # 验证没有调用 record
        app.state.token_stats.record.assert_not_called()
```

**验证**:
- [ ] `pytest core/smart_router/gateway/tests/test_server.py -v` 新增测试通过
- [ ] 现有测试不被破坏

---

### 任务 5: 修改 dashboard_api.py

**目标**: 新增 `GET /api/token-stats` API handler

**文件**: `core/smart_router/gateway/dashboard_api.py`

**修改 5a - 在 `get_logs` 函数之后、`build_dashboard_app` 之前，新增 handler**:
```python
async def token_stats():
    from ..utils.token_stats import TokenStats
    stats = TokenStats()
    data = stats.get_all()

    result = []
    total_prompt = 0
    total_completion = 0
    total_requests = 0

    for model, entry in data.items():
        result.append({
            "model": model,
            "prompt_tokens": entry.get("prompt_tokens", 0),
            "completion_tokens": entry.get("completion_tokens", 0),
            "total_tokens": entry.get("total_tokens", 0),
            "request_count": entry.get("request_count", 0),
        })
        total_prompt += entry.get("prompt_tokens", 0)
        total_completion += entry.get("completion_tokens", 0)
        total_requests += entry.get("request_count", 0)

    return {
        "stats": result,
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_requests": total_requests,
    }
```

**修改 5b - 在 `build_dashboard_app()` 中注册路由**（在 `app.get("/api/logs")(get_logs)` 之后插入）:
```python
    app.get("/api/token-stats")(token_stats)
```

**验证**:
- [ ] `python -c "from smart_router.gateway.dashboard_api import build_dashboard_app; app = build_dashboard_app(); print('OK')"` 可导入
- [ ] 路由注册成功

---

### 任务 6: 补充 dashboard_api 测试

**目标**: 测试 `GET /api/token-stats` API

**文件**: `core/smart_router/gateway/tests/test_dashboard_api.py`

**测试用例**:
```python
import json
import pytest
from unittest.mock import patch
from smart_router.utils.token_stats import TokenStats as RealTokenStats


class TestTokenStatsAPI:
    def test_token_stats_empty(self, client):
        response = client.get("/api/token-stats")
        assert response.status_code == 200
        data = response.json()
        assert data["stats"] == []
        assert data["total_prompt_tokens"] == 0
        assert data["total_completion_tokens"] == 0
        assert data["total_requests"] == 0

    def test_token_stats_with_data(self, client, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        stats_data = {
            "version": 1,
            "records": {
                "gpt-4o": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 500,
                    "total_tokens": 1500,
                    "request_count": 10,
                },
                "claude-3-sonnet": {
                    "prompt_tokens": 2000,
                    "completion_tokens": 1000,
                    "total_tokens": 3000,
                    "request_count": 5,
                },
            },
        }
        stats_file.write_text(json.dumps(stats_data))

        with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
            mock_instance = RealTokenStats(stats_file=stats_file)
            MockStats.return_value = mock_instance

            response = client.get("/api/token-stats")
            assert response.status_code == 200
            data = response.json()
            assert len(data["stats"]) == 2
            assert data["total_prompt_tokens"] == 3000
            assert data["total_completion_tokens"] == 1500
            assert data["total_requests"] == 15
```

**验证**:
- [ ] `pytest core/smart_router/gateway/tests/test_dashboard_api.py -v` 新增测试通过
- [ ] 现有测试不被破坏

---

## 前端任务

### 任务 7: 新增 TokenStats 类型

**目标**: 在 types/index.ts 中新增 TokenStatsItem 和 TokenStatsResponse

**文件**: `frontend/src/types/index.ts`

**修改**（在文件末尾追加）:
```typescript
export interface TokenStatsItem {
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  request_count: number
}

export interface TokenStatsResponse {
  stats: TokenStatsItem[]
  total_prompt_tokens: number
  total_completion_tokens: number
  total_requests: number
}
```

**验证**:
- [ ] `npx tsc --noEmit` 类型检查通过

**附加步骤 - 更新 mock 文件**：在 `frontend/src/store/__mocks__/useDashboardStore.ts` 的 `mockStoreState` 中新增 `tokenStats: []`：
```typescript
export const mockStoreState: Record<string, unknown> = {
  modelOverrides: {},
  modelOverride: { provider: null, model: null, enabled: false },
  setModelOverride: vi.fn(),
  clearModelOverride: vi.fn(),
  tokenStats: [],
}
```

---

### 任务 8: 新增 getTokenStats API

**目标**: 在 api/client.ts 中新增 getTokenStats 方法

**文件**: `frontend/src/api/client.ts`

**修改**:
```typescript
import type {
  // ... 现有导入
  TokenStatsResponse,
} from '../types'

export const api = {
  // ... 现有方法
  getTokenStats: () =>
    client.get<TokenStatsResponse>('/api/token-stats').then((r) => r.data),
}
```

**验证**:
- [ ] `npx tsc --noEmit` 类型检查通过

---

### 任务 9: 修改 Dashboard Store

**目标**: 在 store 中新增 tokenStats 状态和 fetchTokenStats action，并在 fetchAll 中集成

**文件**: `frontend/src/store/useDashboardStore.ts`

**修改 9a - 导入新增类型**:
```typescript
import type {
  // ... 现有导入
  TokenStatsItem,
} from '../types'
```

**修改 9b - 在 DashboardState 接口中新增**:
```typescript
  tokenStats: TokenStatsItem[]
  isLoadingTokenStats: boolean
```

**修改 9c - 在 Actions 中新增**:
```typescript
  fetchTokenStats: () => Promise<void>
```

**修改 9d - 在 create 的初始状态中新增**:
```typescript
  tokenStats: [],
  isLoadingTokenStats: false,
```

**修改 9e - 在 fetchAll 中集成 token stats 获取**:
将现有的 `Promise.all` 从4个请求改为5个：
```typescript
  fetchAll: async () => {
    set({ isLoading: true, error: null })
    try {
      const [status, modelsRes, providersRes, overridesRes, tokenStatsRes] = await Promise.all([
        api.getStatus(),
        api.getModels(),
        api.getProviders(),
        api.getModelOverrides(),
        api.getTokenStats(),
      ])
      set({
        status,
        models: modelsRes.models,
        providers: providersRes.providers,
        modelOverrides: overridesRes.overrides,
        tokenStats: tokenStatsRes.stats,
        isLoading: false,
      })
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false })
    }
  },
```

**修改 9f - 新增独立的 fetchTokenStats action**:
```typescript
  fetchTokenStats: async () => {
    set({ isLoadingTokenStats: true })
    try {
      const result = await api.getTokenStats()
      set({ tokenStats: result.stats, isLoadingTokenStats: false })
    } catch (err) {
      set({ error: (err as Error).message, isLoadingTokenStats: false })
    }
  },
```

**验证**:
- [ ] `npx tsc --noEmit` 类型检查通过

---

### 任务 10: 创建 TokenStatsOverview

**目标**: 创建顶部三卡片总览组件

**文件**: `frontend/src/components/TokenStatsOverview.tsx`

**内容**:
```tsx
import { useDashboardStore } from '../store/useDashboardStore'

export function TokenStatsOverview() {
  const { tokenStats } = useDashboardStore()

  const totalRequests = tokenStats.reduce((sum, s) => sum + s.request_count, 0)
  const totalPrompt = tokenStats.reduce((sum, s) => sum + s.prompt_tokens, 0)
  const totalCompletion = tokenStats.reduce((sum, s) => sum + s.completion_tokens, 0)

  const stats = [
    {
      label: '总请求数',
      value: totalRequests,
      sub: '次 API 调用',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      ),
      accent: 'blue',
    },
    {
      label: '总输入 Token',
      value: totalPrompt,
      sub: 'Prompt 消耗',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
        </svg>
      ),
      accent: 'purple',
    },
    {
      label: '总输出 Token',
      value: totalCompletion,
      sub: 'Completion 消耗',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      accent: 'green',
    },
  ]

  const accentMap: Record<string, { border: string; text: string; glow: string; bg: string }> = {
    blue: {
      border: 'border-[rgba(0,122,255,0.12)]',
      text: 'text-[#007AFF]',
      glow: 'shadow-[rgba(0,122,255,0.06)]',
      bg: 'bg-[rgba(0,122,255,0.05)]',
    },
    purple: {
      border: 'border-[rgba(175,82,222,0.12)]',
      text: 'text-[#AF52DE]',
      glow: 'shadow-[rgba(175,82,222,0.06)]',
      bg: 'bg-[rgba(175,82,222,0.05)]',
    },
    green: {
      border: 'border-[rgba(52,199,89,0.12)]',
      text: 'text-[#34C759]',
      glow: 'shadow-[rgba(52,199,89,0.06)]',
      bg: 'bg-[rgba(52,199,89,0.05)]',
    },
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {stats.map((stat) => {
        const style = accentMap[stat.accent]
        return (
          <div
            key={stat.label}
            className={`glass-card rounded-2xl p-5 ${style.border} hover:shadow-lg ${style.glow}`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-[#86868b] font-mono uppercase tracking-wider">
                {stat.label}
              </span>
              <span className={`${style.text} ${style.bg} p-1.5 rounded-lg`}>
                {stat.icon}
              </span>
            </div>
            <p className={`text-3xl font-bold ${style.text} tracking-tight`}>
              {typeof stat.value === 'number' ? stat.value.toLocaleString() : stat.value}
            </p>
            <p className="text-xs text-[#a1a1a6] mt-1 font-mono">{stat.sub}</p>
          </div>
        )
      })}
    </div>
  )
}
```

**验证**:
- [ ] `npx tsc --noEmit` 类型检查通过
- [ ] 组件可在测试中被渲染

---

### 任务 11: 创建 TokenStatsTable

**目标**: 创建模型明细表格组件，支持点击表头排序

**文件**: `frontend/src/components/TokenStatsTable.tsx`

**内容**:
```tsx
import { useState } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import type { TokenStatsItem } from '../types'

type SortKey = keyof Omit<TokenStatsItem, 'model'> | 'model'

export function TokenStatsTable() {
  const { tokenStats } = useDashboardStore()
  const [sortKey, setSortKey] = useState<SortKey>('total_tokens')
  const [sortAsc, setSortAsc] = useState(false)

  const sorted = [...tokenStats].sort((a, b) => {
    const aVal = a[sortKey]
    const bVal = b[sortKey]
    if (typeof aVal === 'string') {
      return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
    }
    return sortAsc ? aVal - bVal : bVal - aVal
  })

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(false)
    }
  }

  const SortIcon = ({ column }: { column: SortKey }) => {
    if (sortKey !== column) return <span className="text-[#c7c7cc] ml-1">↕</span>
    return <span className="text-[#007AFF] ml-1">{sortAsc ? '▲' : '▼'}</span>
  }

  if (tokenStats.length === 0) {
    return (
      <div className="text-center py-8 text-[#a1a1a6] text-sm">
        暂无数据，发送请求后将自动统计
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[rgba(0,0,0,0.06)]">
            <th
              className="text-left py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
              onClick={() => handleSort('model')}
            >
              模型 <SortIcon column="model" />
            </th>
            <th
              className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
              onClick={() => handleSort('request_count')}
            >
              请求次数 <SortIcon column="request_count" />
            </th>
            <th
              className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
              onClick={() => handleSort('prompt_tokens')}
            >
              输入 Token <SortIcon column="prompt_tokens" />
            </th>
            <th
              className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
              onClick={() => handleSort('completion_tokens')}
            >
              输出 Token <SortIcon column="completion_tokens" />
            </th>
            <th
              className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
              onClick={() => handleSort('total_tokens')}
            >
              总计 Token <SortIcon column="total_tokens" />
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((item) => (
            <tr
              key={item.model}
              className="border-b border-[rgba(0,0,0,0.04)] hover:bg-[rgba(0,0,0,0.02)] transition-colors"
            >
              <td className="py-3 px-2 font-medium text-[#1d1d1f]">{item.model}</td>
              <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono">
                {item.request_count.toLocaleString()}
              </td>
              <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono">
                {item.prompt_tokens.toLocaleString()}
              </td>
              <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono">
                {item.completion_tokens.toLocaleString()}
              </td>
              <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono font-medium">
                {item.total_tokens.toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

**验证**:
- [ ] `npx tsc --noEmit` 类型检查通过

---

### 任务 12: 编写 TokenStatsTable 测试

**目标**: 为 TokenStatsTable 编写单元测试

**文件**: `frontend/src/components/TokenStatsTable.test.tsx`

**内容**:
```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TokenStatsTable } from './TokenStatsTable'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

const mockTokenStats = [
  { model: 'gpt-4o', prompt_tokens: 1000, completion_tokens: 500, total_tokens: 1500, request_count: 10 },
  { model: 'claude-3', prompt_tokens: 2000, completion_tokens: 1000, total_tokens: 3000, request_count: 5 },
]

describe('TokenStatsTable', () => {
  beforeEach(() => {
    mockStoreState.tokenStats = mockTokenStats
  })

  it('renders table with data', () => {
    render(<TokenStatsTable />)
    expect(screen.getByText('gpt-4o')).toBeInTheDocument()
    expect(screen.getByText('claude-3')).toBeInTheDocument()
  })

  it('sorts by total_tokens descending by default', () => {
    render(<TokenStatsTable />)
    const rows = screen.getAllByRole('row')
    // claude-3 has more total_tokens, should be first in tbody
    expect(rows[1]).toHaveTextContent('claude-3')
    expect(rows[2]).toHaveTextContent('gpt-4o')
  })

  it('toggles sort order when clicking same column', () => {
    render(<TokenStatsTable />)
    const totalHeader = screen.getByText('总计 Token')
    fireEvent.click(totalHeader)
    // After clicking, should sort ascending
    const rows = screen.getAllByRole('row')
    expect(rows[1]).toHaveTextContent('gpt-4o')
    expect(rows[2]).toHaveTextContent('claude-3')
  })

  it('changes sort column when clicking different column', () => {
    render(<TokenStatsTable />)
    const requestHeader = screen.getByText('请求次数')
    fireEvent.click(requestHeader)
    // gpt-4o has more requests
    const rows = screen.getAllByRole('row')
    expect(rows[1]).toHaveTextContent('gpt-4o')
  })

  it('shows empty state when no data', () => {
    mockStoreState.tokenStats = []
    render(<TokenStatsTable />)
    expect(screen.getByText('暂无数据，发送请求后将自动统计')).toBeInTheDocument()
  })
})
```

**验证**:
- [ ] `cd frontend && npx vitest run src/components/TokenStatsTable.test.tsx` 全部通过

---

### 任务 13: 创建 TokenStatsChart

**目标**: 创建 Recharts 饼图展示各模型 token 占比

**文件**: `frontend/src/components/TokenStatsChart.tsx`

**内容**:
```tsx
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useDashboardStore } from '../store/useDashboardStore'

const COLORS = [
  '#007AFF', '#AF52DE', '#34C759', '#FF9500',
  '#FF3B30', '#5856D6', '#FF2D55', '#5AC8FA',
]

export function TokenStatsChart() {
  const { tokenStats } = useDashboardStore()

  if (tokenStats.length === 0) {
    return (
      <div className="text-center py-8 text-[#a1a1a6] text-sm">
        暂无数据，发送请求后将自动统计
      </div>
    )
  }

  const data = tokenStats.map((item) => ({
    name: item.model,
    value: item.total_tokens,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={100}
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
        >
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number) => [value.toLocaleString(), 'Token']}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}
```

**验证**:
- [ ] `npx tsc --noEmit` 类型检查通过

---

### 任务 14: 创建 TokenStatsPage

**目标**: 创建页面容器，组合 Overview、Table、Chart

**文件**: `frontend/src/components/TokenStatsPage.tsx`

**内容**:
```tsx
import { TokenStatsOverview } from './TokenStatsOverview'
import { TokenStatsTable } from './TokenStatsTable'
import { TokenStatsChart } from './TokenStatsChart'

export function TokenStatsPage() {
  return (
    <div className="space-y-6">
      <TokenStatsOverview />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card rounded-2xl p-5">
          <h3 className="text-sm font-medium text-[#86868b] mb-4">
            模型消耗明细
          </h3>
          <TokenStatsTable />
        </div>
        <div className="glass-card rounded-2xl p-5">
          <h3 className="text-sm font-medium text-[#86868b] mb-4">
            Token 分布
          </h3>
          <TokenStatsChart />
        </div>
      </div>
    </div>
  )
}
```

**验证**:
- [ ] `npx tsc --noEmit` 类型检查通过

---

### 任务 15: 修改 App.tsx

**目标**: 在 Tab 导航中新增 "Token 统计" 标签

**文件**: `frontend/src/App.tsx`

**修改 15a - 导入 TokenStatsPage**:
```tsx
import { TokenStatsPage } from './components/TokenStatsPage'
```

**修改 15b - 扩展 activeTab 类型**:
```tsx
const [activeTab, setActiveTab] = useState<'dashboard' | 'models' | 'logs' | 'token-stats'>('dashboard')
```

**修改 15c - 在 Tab Navigation 中新增按钮**（在 logs 按钮之后插入）:
```tsx
          <button
            onClick={() => setActiveTab('token-stats')}
            className={`px-5 py-2 rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
              activeTab === 'token-stats'
                ? 'bg-[rgba(0,122,255,0.08)] text-[#007AFF] shadow-sm'
                : 'text-[#86868b] hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
            </svg>
            Token 统计
          </button>
```

**修改 15d - 在渲染条件中新增**:
```tsx
        {activeTab === 'dashboard' ? <DashboardPage /> : 
         activeTab === 'models' ? <ModelsExplorer /> : 
         activeTab === 'logs' ? <LogsPanel /> : 
         <TokenStatsPage />}
```

**验证**:
- [ ] `npx tsc --noEmit` 类型检查通过
- [ ] `cd frontend && npx vitest run src/App.test.tsx` 通过

---

### 任务 16: 编写 TokenStatsPage 测试

**目标**: 为 TokenStatsPage 编写集成测试

**文件**: `frontend/src/components/TokenStatsPage.test.tsx`

**内容**:
```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TokenStatsPage } from './TokenStatsPage'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

const mockStats = [
  { model: 'gpt-4o', prompt_tokens: 1000, completion_tokens: 500, total_tokens: 1500, request_count: 10 },
]

describe('TokenStatsPage', () => {
  beforeEach(() => {
    mockStoreState.tokenStats = mockStats
  })

  it('renders overview cards', () => {
    render(<TokenStatsPage />)
    expect(screen.getByText('总请求数')).toBeInTheDocument()
    expect(screen.getByText('总输入 Token')).toBeInTheDocument()
    expect(screen.getByText('总输出 Token')).toBeInTheDocument()
  })

  it('renders table section', () => {
    render(<TokenStatsPage />)
    expect(screen.getByText('模型消耗明细')).toBeInTheDocument()
    expect(screen.getByText('gpt-4o')).toBeInTheDocument()
  })

  it('renders chart section', () => {
    render(<TokenStatsPage />)
    expect(screen.getByText('Token 分布')).toBeInTheDocument()
  })

  it('shows zero values when no data', () => {
    mockStoreState.tokenStats = []
    render(<TokenStatsPage />)
    expect(screen.getAllByText('0')).toHaveLength(3) // 三个卡片都是0
  })
})
```

**验证**:
- [ ] `cd frontend && npx vitest run src/components/TokenStatsPage.test.tsx` 全部通过

---

## 验收标准覆盖检查

| 验收标准 | 对应任务 | 验证方式 |
|---------|---------|---------|
| 后端：非流式 chat/completions 请求的 usage 被正确累加 | 3, 4 | pytest 中间件测试 |
| 后端：`GET /api/token-stats` 返回正确格式的 JSON | 5, 6 | pytest API 测试 |
| 后端：服务重启后历史数据不丢失 | 1, 2 | TokenStats 持久化测试 |
| 后端：并发请求不造成数据损坏或丢失 | 2 | 并发 record 测试 |
| 前端：Tab 导航中出现"Token 统计"标签 | 15 | App.tsx 渲染测试 |
| 前端：页面展示三卡片总览、明细表格、饼图 | 14, 16 | TokenStatsPage 测试 |
| 前端：表格支持按各列排序 | 11, 12 | TokenStatsTable 测试 |
| 前端：数据自动刷新（与 Dashboard 相同的 5 秒间隔） | 9 | fetchAll 集成 token stats |
| 测试：后端单元测试全部通过 | 2, 4, 6 | pytest |
| 测试：前端测试全部通过 | 12, 16 | vitest |

---

## 执行建议

**分批策略**:
1. **第一批（任务 1-6）**: 后端全部任务，完成后运行 `pytest core/` 验证
2. **第二批（任务 7-16）**: 前端全部任务，完成后运行 `cd frontend && npx vitest run`

**跨进程注意事项**:
- `server.py`（端口4000）和 `dashboard_api.py`（端口8080）是两个独立进程
- 两者通过 `~/.smart-router/token_stats.json` 共享数据
- 测试时需要确保文件路径正确（使用 `tmp_path` fixture）

**已知限制**:
- 流式响应（SSE）第一期不处理
- 时间维度统计留待后续扩展
