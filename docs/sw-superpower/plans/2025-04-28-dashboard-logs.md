# Dashboard 日志 Tab 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Dashboard 新增"日志" Tab，通过轮询 API 实时展示 Smart Router 服务日志和 Dashboard 自身日志。

**Architecture:** 后端新增 `GET /api/logs` 接口读取白名单日志文件；前端新增 LogsPanel 组件和日志轮询状态管理；App.tsx 扩展 Tab 导航。

**Tech Stack:** Python 3.9+, FastAPI, TypeScript, React, Zustand, Tailwind CSS

---

### Task 1: 后端新增日志读取 API

**Files:**
- Modify: `core/smart_router/gateway/dashboard_api.py`

- [ ] **Step 1: 新增日志读取函数和 Pydantic 模型**

在 `dashboard_api.py` 的 Pydantic 模型区域后新增：

```python
class LogsResponse(BaseModel):
    lines: list[str]
    offset: int
    total_size: int


LOG_FILE_MAP = {
    "service": DEFAULT_PID_DIR / "smart-router.log",
    "dashboard": DEFAULT_PID_DIR / "dashboard.log",
}


def read_log_lines(source: str, offset: int, limit: int = 500) -> LogsResponse:
    """读取日志文件指定偏移之后的新行

    Args:
        source: 日志源，"service" 或 "dashboard"
        offset: 已读取的字节数
        limit: 最大返回行数

    Returns:
        LogsResponse: 包含新行列表、新的 offset 和文件总大小
    """
    if source not in LOG_FILE_MAP:
        raise ValueError(f"Invalid log source: {source}")

    log_path = LOG_FILE_MAP[source]

    if not log_path.exists():
        return LogsResponse(lines=[], offset=0, total_size=0)

    content = log_path.read_bytes()
    total_size = len(content)

    # 文件被清空或轮转：offset 超出范围，从头开始
    if offset > total_size:
        offset = 0

    new_content = content[offset:]
    text = new_content.decode("utf-8", errors="replace")
    lines = text.splitlines()

    if len(lines) > limit:
        lines = lines[-limit:]

    return LogsResponse(lines=lines, offset=total_size, total_size=total_size)
```

- [ ] **Step 2: 新增 API handler 并注册到 build_dashboard_app**

在 `dry_run` handler 附近新增：

```python
async def get_logs(source: str = "service", offset: int = 0, limit: int = 500):
    try:
        result = read_log_lines(source, offset, limit)
        return {
            "lines": result.lines,
            "offset": result.offset,
            "total_size": result.total_size,
        }
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {e}")
```

在 `build_dashboard_app` 函数中新增路由注册：

```python
app.get("/api/logs")(get_logs)
```

- [ ] **Step 3: 运行后端测试确保未破坏现有功能**

Run: `pytest core/smart_router/gateway/tests/test_dashboard_api.py -v`
Expected: 所有现有测试通过

- [ ] **Step 4: Commit**

```bash
git add core/smart_router/gateway/dashboard_api.py
git commit -m "feat(gateway): 新增 /api/logs 接口用于读取服务日志和 Dashboard 日志"
```

---

### Task 2: 后端编写日志 API 测试

**Files:**
- Create: `core/smart_router/gateway/tests/test_logs_api.py`

- [ ] **Step 1: 编写测试文件**

```python
"""日志 API 单元测试"""

import pytest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from smart_router.gateway.dashboard_api import build_dashboard_app


@pytest.fixture
def client():
    app = build_dashboard_app(static_dir=None)
    return TestClient(app)


class TestLogs:
    def test_logs_service_source(self, client, tmp_path):
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("line1\nline2\nline3\n")

        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            response = client.get("/api/logs?source=service&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert data["lines"] == ["line1", "line2", "line3"]
            assert data["offset"] == 18
            assert data["total_size"] == 18

    def test_logs_with_offset(self, client, tmp_path):
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("line1\nline2\nline3\n")

        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            # offset 在 line2 之后
            response = client.get("/api/logs?source=service&offset=12")
            assert response.status_code == 200
            data = response.json()
            assert data["lines"] == ["line3"]
            assert data["offset"] == 18

    def test_logs_file_not_exist(self, client, tmp_path):
        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": tmp_path / "nonexistent.log",
            "dashboard": tmp_path / "dashboard.log",
        }):
            response = client.get("/api/logs?source=service&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert data["lines"] == []
            assert data["offset"] == 0
            assert data["total_size"] == 0

    def test_logs_invalid_source(self, client):
        response = client.get("/api/logs?source=invalid&offset=0")
        assert response.status_code == 400

    def test_logs_offset_overflow(self, client, tmp_path):
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("newcontent\n")

        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            # offset 大于文件大小，应该从头开始
            response = client.get("/api/logs?source=service&offset=9999")
            assert response.status_code == 200
            data = response.json()
            assert data["lines"] == ["newcontent"]
            assert data["offset"] == 11
```

- [ ] **Step 2: 运行测试**

Run: `pytest core/smart_router/gateway/tests/test_logs_api.py -v`
Expected: 全部 5 个测试通过

- [ ] **Step 3: Commit**

```bash
git add core/smart_router/gateway/tests/test_logs_api.py
git commit -m "test(gateway): 新增日志 API 单元测试"
```

---

### Task 3: 前端扩展类型定义和 API Client

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 新增日志相关类型**

在 `frontend/src/types/index.ts` 末尾追加：

```typescript
export interface LogsResponse {
  lines: string[]
  offset: number
  total_size: number
}

export type LogSource = 'service' | 'dashboard'

export interface LogState {
  lines: string[]
  offset: number
  total_size: number
  source: LogSource
}
```

- [ ] **Step 2: 扩展 API Client**

在 `frontend/src/api/client.ts` 中：
1. 导入列表新增 `LogsResponse, LogSource`
2. `api` 对象新增：

```typescript
getLogs: (source: LogSource, offset: number, limit?: number) =>
  client.get<LogsResponse>('/api/logs', { params: { source, offset, limit } }).then((r) => r.data),
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat(frontend): 新增日志相关类型和 API 方法"
```

---

### Task 4: 前端扩展 Dashboard Store 支持日志轮询

**Files:**
- Modify: `frontend/src/store/useDashboardStore.ts`

- [ ] **Step 1: 扩展 State 和 Actions**

在 interface 中新增字段：

```typescript
// Logs
logs: LogState
isLoadingLogs: boolean
logError: string | null
```

在 Actions 中新增：

```typescript
fetchLogs: (source?: LogSource) => Promise<void>
setLogSource: (source: LogSource) => void
clearLogError: () => void
```

- [ ] **Step 2: 扩展 create 实现**

在初始 state 中新增：

```typescript
logs: { lines: [], offset: 0, total_size: 0, source: 'service' as LogSource },
isLoadingLogs: false,
logError: null,
```

新增 actions：

```typescript
fetchLogs: async (source?: LogSource) => {
  const currentSource = source || get().logs.source
  const currentOffset = source ? 0 : get().logs.offset

  set({ isLoadingLogs: true, logError: null })
  try {
    const result = await api.getLogs(currentSource, currentOffset, 500)
    const existingLines = source ? [] : get().logs.lines
    set({
      logs: {
        lines: [...existingLines, ...result.lines],
        offset: result.offset,
        total_size: result.total_size,
        source: currentSource,
      },
      isLoadingLogs: false,
    })
  } catch (err) {
    set({ logError: (err as Error).message, isLoadingLogs: false })
  }
},

setLogSource: (source: LogSource) => {
  set({
    logs: { lines: [], offset: 0, total_size: 0, source },
    logError: null,
  })
},

clearLogError: () => set({ logError: null }),
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/store/useDashboardStore.ts
git commit -m "feat(frontend): Dashboard Store 新增日志状态管理和轮询支持"
```

---

### Task 5: 前端新增 LogsPanel 组件

**Files:**
- Create: `frontend/src/components/LogsPanel.tsx`
- Create: `frontend/src/components/LogsPanel.test.tsx`

- [ ] **Step 1: 编写 LogsPanel 组件**

```tsx
import { useEffect, useRef, useState, useCallback } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import type { LogSource } from '../types'

const LOG_SOURCES: { key: LogSource; label: string }[] = [
  { key: 'service', label: '服务日志' },
  { key: 'dashboard', label: 'Dashboard 日志' },
]

function getLineColor(line: string): string {
  const upper = line.toUpperCase()
  if (upper.includes('ERROR') || upper.includes('CRITICAL') || upper.includes('FATAL')) {
    return 'text-[#FF3B30]'
  }
  if (upper.includes('WARNING') || upper.includes('WARN')) {
    return 'text-[#FF9500]'
  }
  if (upper.includes('INFO')) {
    return 'text-[#34C759]'
  }
  return 'text-[#e5e5ea]'
}

export function LogsPanel() {
  const { logs, fetchLogs, setLogSource, logError, clearLogError } = useDashboardStore()
  const [activeSource, setActiveSource] = useState<LogSource>('service')
  const [autoScroll, setAutoScroll] = useState(true)
  const containerRef = useRef<HTMLDivElement>(null)
  const prevLinesLength = useRef(0)

  // 初始加载和切换源
  useEffect(() => {
    setLogSource(activeSource)
    fetchLogs(activeSource)
  }, [activeSource])

  // 轮询：每 10 秒获取新日志
  useEffect(() => {
    const interval = setInterval(() => {
      fetchLogs()
    }, 10000)
    return () => clearInterval(interval)
  }, [fetchLogs])

  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll && containerRef.current && logs.lines.length > prevLinesLength.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
    prevLinesLength.current = logs.lines.length
  }, [logs.lines, autoScroll])

  const handleScroll = useCallback(() => {
    if (!containerRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 50
    setAutoScroll(isNearBottom)
  }, [])

  const handleSwitch = (source: LogSource) => {
    if (source === activeSource) return
    setActiveSource(source)
  }

  return (
    <div className="space-y-4">
      {/* Error Alert */}
      {logError && (
        <div className="glass-card rounded-2xl p-4 flex items-center justify-between border border-red-400/20">
          <p className="text-sm text-[#FF3B30]">{logError}</p>
          <button
            onClick={clearLogError}
            className="text-sm text-[#FF3B30] hover:text-[#FF3B30]/70 transition-colors"
          >
            关闭
          </button>
        </div>
      )}

      <div className="glass-card rounded-2xl overflow-hidden">
        {/* Header with source tabs */}
        <div className="p-4 border-b border-[rgba(0,0,0,0.06)] flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-1 h-5 bg-[#007AFF] rounded-full" />
            <h2 className="text-base font-semibold text-[#1d1d1f] tracking-wide">实时日志</h2>
            <div className="flex gap-1 ml-4">
              {LOG_SOURCES.map((s) => (
                <button
                  key={s.key}
                  onClick={() => handleSwitch(s.key)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                    activeSource === s.key
                      ? 'bg-[rgba(0,122,255,0.08)] text-[#007AFF]'
                      : 'text-[#86868b] hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
          <div className="text-xs text-[#86868b] font-mono">
            {logs.lines.length} 行
          </div>
        </div>

        {/* Log content */}
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="bg-[#1c1c1e] p-4 overflow-auto"
          style={{ maxHeight: '60vh', minHeight: '400px' }}
        >
          {logs.lines.length === 0 ? (
            <p className="text-sm text-[#86868b] font-mono text-center py-8">暂无日志</p>
          ) : (
            <div className="space-y-0.5">
              {logs.lines.map((line, index) => (
                <pre
                  key={`${activeSource}-${index}`}
                  className={`text-xs font-mono whitespace-pre-wrap break-all leading-relaxed ${getLineColor(line)}`}
                >
                  {line}
                </pre>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-[rgba(0,0,0,0.06)] flex items-center justify-between">
          <span className="text-xs text-[#86868b]">
            {autoScroll ? '自动滚动中' : '已暂停自动滚动'}
          </span>
          <span className="text-xs text-[#86868b] font-mono">
            offset: {logs.offset} bytes
          </span>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 编写 LogsPanel 测试**

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { LogsPanel } from './LogsPanel'
import * as storeModule from '../store/useDashboardStore'

vi.mock('../store/useDashboardStore')

const createMockStore = (overrides = {}) => ({
  logs: { lines: [], offset: 0, total_size: 0, source: 'service' as const },
  fetchLogs: vi.fn(),
  setLogSource: vi.fn(),
  logError: null,
  clearLogError: vi.fn(),
  ...overrides,
})

describe('LogsPanel', () => {
  it('renders empty state', () => {
    vi.mocked(storeModule.useDashboardStore).mockReturnValue(createMockStore())
    render(<LogsPanel />)
    expect(screen.getByText('暂无日志')).toBeInTheDocument()
  })

  it('renders log lines', () => {
    vi.mocked(storeModule.useDashboardStore).mockReturnValue(
      createMockStore({
        logs: {
          lines: ['INFO: started', 'ERROR: failed'],
          offset: 100,
          total_size: 100,
          source: 'service' as const,
        },
      })
    )
    render(<LogsPanel />)
    expect(screen.getByText('INFO: started')).toBeInTheDocument()
    expect(screen.getByText('ERROR: failed')).toBeInTheDocument()
  })

  it('switches log source on tab click', () => {
    const setLogSource = vi.fn()
    vi.mocked(storeModule.useDashboardStore).mockReturnValue(
      createMockStore({ setLogSource })
    )
    render(<LogsPanel />)
    fireEvent.click(screen.getByText('Dashboard 日志'))
    expect(setLogSource).toHaveBeenCalledWith('dashboard')
  })
})
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/LogsPanel.tsx frontend/src/components/LogsPanel.test.tsx
git commit -m "feat(frontend): 新增 LogsPanel 组件及测试"
```

---

### Task 6: 前端修改 App.tsx 添加日志 Tab

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`（如有必要）

- [ ] **Step 1: 修改 App.tsx**

1. 导入 `LogsPanel`
2. 将 `activeTab` state 类型扩展为 `'dashboard' | 'models' | 'logs'`
3. 在 Tab Navigation 区新增"日志"按钮
4. 在 Page Content 条件渲染中新增 `logs` 分支

具体修改：

```tsx
import { LogsPanel } from './components/LogsPanel'
```

```tsx
const [activeTab, setActiveTab] = useState<'dashboard' | 'models' | 'logs'>('dashboard')
```

Tab Navigation 新增按钮（放在"模型清单"之后）：

```tsx
<button
  onClick={() => setActiveTab('logs')}
  className={`px-5 py-2 rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
    activeTab === 'logs'
      ? 'bg-[rgba(0,122,255,0.08)] text-[#007AFF] shadow-sm'
      : 'text-[#86868b] hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
  }`}
>
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
  日志
</button>
```

Page Content 条件渲染：

```tsx
{activeTab === 'dashboard' ? <DashboardPage /> : activeTab === 'models' ? <ModelsExplorer /> : <LogsPanel />}
```

- [ ] **Step 2: 运行前端测试**

Run: `cd frontend && npm test -- --run`
Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): App.tsx 新增日志 Tab 导航"
```

---

### Task 7: 端到端验证

- [ ] **Step 1: 运行后端测试**

Run: `pytest core/smart_router/gateway/tests/ -v`
Expected: 全部通过

- [ ] **Step 2: 运行前端测试**

Run: `cd frontend && npm test -- --run`
Expected: 全部通过

- [ ] **Step 3: 构建前端**

Run: `cd frontend && npm run build`
Expected: 构建成功，无错误

- [ ] **Step 4: 快速手动验证（可选）**

```bash
# 启动 Dashboard（前台模式）
smr dashboard --foreground
```

打开 http://127.0.0.1:8080，切换到"日志" Tab，确认：
1. 默认显示"暂无日志"（如果服务未启动）
2. 切换"服务日志"/"Dashboard 日志"正常
3. 每 10 秒自动刷新（可以在浏览器 DevTools Network 中观察）

- [ ] **Step 5: Commit**

```bash
git commit --allow-empty -m "feat: Dashboard 日志 Tab 功能完成"
```

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `core/smart_router/gateway/dashboard_api.py` | 修改 | 新增 `read_log_lines` 函数、`get_logs` handler、路由注册 |
| `core/smart_router/gateway/tests/test_logs_api.py` | 创建 | 日志 API 单元测试 |
| `frontend/src/types/index.ts` | 修改 | 新增 `LogsResponse`, `LogSource`, `LogState` 类型 |
| `frontend/src/api/client.ts` | 修改 | 新增 `getLogs` API 方法 |
| `frontend/src/store/useDashboardStore.ts` | 修改 | 新增日志状态、actions、轮询逻辑 |
| `frontend/src/components/LogsPanel.tsx` | 创建 | 日志展示组件 |
| `frontend/src/components/LogsPanel.test.tsx` | 创建 | 日志组件测试 |
| `frontend/src/App.tsx` | 修改 | 扩展 Tab 导航，引入 LogsPanel |

## Spec 覆盖检查

- ✅ 轮询 API 方案 — Task 1
- ✅ 10 秒轮询间隔 — Task 5 (useEffect interval)
- ✅ 双日志源（service + dashboard）— Task 1 & 5
- ✅ offset 机制只获取新增行 — Task 1 `read_log_lines`
- ✅ 文件不存在/清空/越界处理 — Task 1 & 2
- ✅ 安全白名单 — Task 1 `LOG_FILE_MAP`
- ✅ 自动滚动 — Task 5 `autoScroll` state
- ✅ 日志着色 — Task 5 `getLineColor`
- ✅ 独立轮询（与 fetchAll 5秒轮询不冲突）— Task 4 & 5
