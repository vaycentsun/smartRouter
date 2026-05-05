# Dashboard Tab 导航与模型清单页实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Dashboard 前端引入 Tab 导航（仪表盘 / 模型清单），将现有页面拆分为两个视图，并新建模型清单 Master-Detail 页面。

**Architecture:** App 内使用 `useState` 管理 `activeTab`；新建 `DashboardPage` 和 `ModelsExplorer` 两个页面容器；`ModelsExplorer` 内部管理 `selectedProvider` 状态，左右分栏展示 Provider 列表与模型详情；配置编辑通过 Modal 弹窗实现。

**Tech Stack:** React 18 + TypeScript + Tailwind CSS + Zustand

---

## 文件结构

| 文件 | 状态 | 职责 |
|------|------|------|
| `frontend/src/App.tsx` | 修改 | 新增 Tab 导航栏，条件渲染 `DashboardPage` / `ModelsExplorer` |
| `frontend/src/components/DashboardPage.tsx` | 新建 | 仪表盘页面容器 |
| `frontend/src/components/ModelsExplorer.tsx` | 新建 | 模型清单页面容器（左右分栏 + selectedProvider 状态） |
| `frontend/src/components/ProviderSidebar.tsx` | 新建 | 左侧 Provider 列表边栏 |
| `frontend/src/components/ProviderModelsPanel.tsx` | 新建 | 右侧模型列表面板 |
| `frontend/src/components/ProviderEditModal.tsx` | 新建 | Provider 配置编辑弹窗 |
| `frontend/src/App.test.tsx` | 修改 | 更新测试以匹配新 Tab 结构 |
| `frontend/src/components/ModelsExplorer.test.tsx` | 新建 | 模型清单页面集成测试 |
| `frontend/src/components/ProviderSidebar.test.tsx` | 新建 | Provider 边栏单元测试 |
| `frontend/src/components/ProviderModelsPanel.test.tsx` | 新建 | 模型面板单元测试 |
| `frontend/src/components/ProviderEditModal.test.tsx` | 新建 | 编辑弹窗单元测试 |

---

### Task 1: 新建 DashboardPage 组件

**Files:**
- Create: `frontend/src/components/DashboardPage.tsx`
- Test: `frontend/src/components/DashboardPage.test.tsx`

**说明:** 将现有 `App.tsx` 中仪表盘相关内容提取为独立页面组件。

- [ ] **Step 1: 编写组件代码**

```tsx
import { StatsOverview } from './StatsOverview'
import { StatusCard } from './StatusCard'
import { DryRunPanel } from './DryRunPanel'

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <StatsOverview />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <StatusCard />
        </div>
        <div className="lg:col-span-2">
          <DryRunPanel />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 编写测试**

```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { DashboardPage } from './DashboardPage'

vi.mock('../store/useDashboardStore', () => ({
  useDashboardStore: vi.fn((selector) => {
    const state = {
      status: { running: true, pid: 1234, uptime_seconds: 3600, service_url: 'http://localhost:4000', version: '1.0.0' },
      models: [],
      providers: [],
      dryRunResult: null,
      isLoading: false,
      error: null,
    }
    return selector ? selector(state) : state
  }),
}))

describe('DashboardPage', () => {
  it('renders stats overview, status card and dry run panel', () => {
    render(<DashboardPage />)
    expect(screen.getByText('模型总数')).toBeInTheDocument()
    expect(screen.getByText('服务状态')).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: 运行测试确保通过**

Run: `cd frontend && npm test -- DashboardPage.test.tsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/DashboardPage.tsx frontend/src/components/DashboardPage.test.tsx
git commit -m "feat: add DashboardPage component"
```

---

### Task 2: 新建 ProviderSidebar 组件

**Files:**
- Create: `frontend/src/components/ProviderSidebar.tsx`
- Test: `frontend/src/components/ProviderSidebar.test.tsx`

**说明:** 左侧边栏，展示 Provider 卡片列表，点击选中。

- [ ] **Step 1: 编写组件代码**

```tsx
import type { ProviderInfo } from '../types'

interface ProviderSidebarProps {
  providers: ProviderInfo[]
  selectedProvider: string | null
  modelsCount: Record<string, number>
  onSelect: (name: string) => void
}

function StatusDot({ hasKey }: { hasKey: boolean }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${
        hasKey ? 'bg-emerald-400' : 'bg-red-400'
      }`}
      title={hasKey ? 'Key 已配置' : 'Key 缺失'}
    />
  )
}

export function ProviderSidebar({ providers, selectedProvider, modelsCount, onSelect }: ProviderSidebarProps) {
  if (providers.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-6">
        <p className="text-[#a1a1a6] text-sm">暂无 Provider 数据</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {providers.map((provider) => {
        const isSelected = selectedProvider === provider.name
        const count = modelsCount[provider.name] || 0
        return (
          <button
            key={provider.name}
            onClick={() => onSelect(provider.name)}
            className={`w-full text-left p-4 rounded-2xl border transition-all duration-200 ${
              isSelected
                ? 'bg-[rgba(0,122,255,0.06)] border-[rgba(0,122,255,0.2)] shadow-sm'
                : 'bg-white/60 border-transparent hover:bg-white/80 hover:border-[rgba(0,0,0,0.06)]'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <StatusDot hasKey={provider.has_key} />
                <span className="font-semibold text-[#1d1d1f] text-sm">{provider.name}</span>
              </div>
              <span className="text-xs bg-[rgba(0,0,0,0.04)] text-[#86868b] px-2 py-0.5 rounded-full font-mono">
                {count} 模型
              </span>
            </div>
            <p className="text-xs text-[#a1a1a6] truncate font-mono">{provider.api_base}</p>
            <div className="mt-2 flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded-full border ${
                provider.has_key
                  ? 'bg-[rgba(52,199,89,0.06)] text-[#34C759] border-[rgba(52,199,89,0.12)]'
                  : 'bg-[rgba(255,59,48,0.06)] text-[#FF3B30] border-[rgba(255,59,48,0.12)]'
              }`}>
                {provider.has_key ? 'Key 已配置' : 'Key 缺失'}
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: 编写测试**

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ProviderSidebar } from './ProviderSidebar'
import type { ProviderInfo } from '../types'

const mockProviders: ProviderInfo[] = [
  { name: 'openai', api_base: 'https://api.openai.com', timeout: 30, key_type: 'env:OPENAI_API_KEY', has_key: true, masked_key: 'sk-****' },
  { name: 'anthropic', api_base: 'https://api.anthropic.com', timeout: 30, key_type: 'env:ANTHROPIC_API_KEY', has_key: false },
]

describe('ProviderSidebar', () => {
  it('renders provider list', () => {
    render(<ProviderSidebar providers={mockProviders} selectedProvider={null} modelsCount={{}} onSelect={vi.fn()} />)
    expect(screen.getByText('openai')).toBeInTheDocument()
    expect(screen.getByText('anthropic')).toBeInTheDocument()
  })

  it('calls onSelect when provider is clicked', () => {
    const onSelect = vi.fn()
    render(<ProviderSidebar providers={mockProviders} selectedProvider={null} modelsCount={{}} onSelect={onSelect} />)
    fireEvent.click(screen.getByText('openai'))
    expect(onSelect).toHaveBeenCalledWith('openai')
  })

  it('shows empty state when no providers', () => {
    render(<ProviderSidebar providers={[]} selectedProvider={null} modelsCount={{}} onSelect={vi.fn()} />)
    expect(screen.getByText('暂无 Provider 数据')).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: 运行测试**

Run: `cd frontend && npm test -- ProviderSidebar.test.tsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ProviderSidebar.tsx frontend/src/components/ProviderSidebar.test.tsx
git commit -m "feat: add ProviderSidebar component"
```

---

### Task 3: 新建 ProviderModelsPanel 组件

**Files:**
- Create: `frontend/src/components/ProviderModelsPanel.tsx`
- Test: `frontend/src/components/ProviderModelsPanel.test.tsx`

**说明:** 右侧面板，展示选中 Provider 的模型列表。

- [ ] **Step 1: 编写组件代码**

```tsx
import type { ModelInfo, ProviderInfo } from '../types'

function TaskBadge({ task }: { task: string }) {
  return (
    <span className="inline-block px-2 py-0.5 bg-[rgba(0,122,255,0.06)] text-[#007AFF]/80 text-xs rounded border border-[rgba(0,122,255,0.12)] mr-1">
      {task}
    </span>
  )
}

function StarRating({ value, colorClass }: { value: number; colorClass: string }) {
  const filled = Math.floor(value / 2)
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={`text-xs ${i < filled ? colorClass : 'text-[rgba(0,0,0,0.08)]'}`}>★</span>
      ))}
    </div>
  )
}

interface ProviderModelsPanelProps {
  provider: ProviderInfo | null
  models: ModelInfo[]
  onEdit: () => void
}

export function ProviderModelsPanel({ provider, models, onEdit }: ProviderModelsPanelProps) {
  if (!provider) {
    return (
      <div className="glass-card rounded-2xl p-8 flex items-center justify-center min-h-[300px]">
        <p className="text-[#a1a1a6]">请选择一个 Provider</p>
      </div>
    )
  }

  const providerModels = models.filter((m) => m.provider === provider.name)

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <div className="p-4 border-b border-[rgba(0,0,0,0.06)] flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#1d1d1f]">{provider.name}</h2>
          <p className="text-xs text-[#a1a1a6] font-mono mt-0.5">{providerModels.length} 个模型</p>
        </div>
        <button
          onClick={onEdit}
          className="px-4 py-2 bg-[rgba(0,122,255,0.08)] text-[#007AFF] border border-[rgba(0,122,255,0.15)] rounded-xl hover:bg-[rgba(0,122,255,0.12)] text-sm font-medium transition-all"
        >
          编辑配置
        </button>
      </div>

      {providerModels.length === 0 ? (
        <div className="p-8 text-center text-[#a1a1a6]">
          该 Provider 暂无模型数据
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-[rgba(0,0,0,0.02)] text-[#86868b]">
              <tr>
                <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">模型名称</th>
                <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">状态</th>
                <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">Quality</th>
                <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">Cost</th>
                <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">Context</th>
                <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">支持任务</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(0,0,0,0.04)]">
              {providerModels.map((model) => (
                <tr key={model.name} className="table-row-hover">
                  <td className="px-4 py-3 font-medium text-[#1d1d1f]">{model.name}</td>
                  <td className="px-4 py-3">
                    {model.available ? (
                      <span className="inline-flex items-center gap-1.5 text-[#34C759] text-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#34C759] pulse-glow" />在线
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-[#FF3B30] text-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#FF3B30] pulse-glow-red" />离线
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3"><StarRating value={model.quality} colorClass="text-[#FF9500]" /></td>
                  <td className="px-4 py-3"><StarRating value={model.cost} colorClass="text-[#FF9500]" /></td>
                  <td className="px-4 py-3 text-[#86868b] font-mono text-xs">
                    {model.context >= 1000 ? `${Math.floor(model.context / 1000)}k` : model.context}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {model.supported_tasks.slice(0, 3).map((task) => (
                        <TaskBadge key={task} task={task} />
                      ))}
                      {model.supported_tasks.length > 3 && (
                        <span className="text-xs text-[#a1a1a6]">+{model.supported_tasks.length - 3}</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 编写测试**

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ProviderModelsPanel } from './ProviderModelsPanel'
import type { ModelInfo, ProviderInfo } from '../types'

const mockProvider: ProviderInfo = {
  name: 'openai', api_base: 'https://api.openai.com', timeout: 30, key_type: 'env:OPENAI_API_KEY', has_key: true,
}

const mockModels: ModelInfo[] = [
  { name: 'gpt-4', provider: 'openai', available: true, quality: 10, cost: 4, context: 8192, supported_tasks: ['chat', 'completion'] },
  { name: 'gpt-3.5', provider: 'openai', available: true, quality: 8, cost: 6, context: 4096, supported_tasks: ['chat'] },
  { name: 'claude-3', provider: 'anthropic', available: true, quality: 10, cost: 4, context: 200000, supported_tasks: ['chat'] },
]

describe('ProviderModelsPanel', () => {
  it('shows placeholder when no provider selected', () => {
    render(<ProviderModelsPanel provider={null} models={[]} onEdit={vi.fn()} />)
    expect(screen.getByText('请选择一个 Provider')).toBeInTheDocument()
  })

  it('renders models for selected provider', () => {
    render(<ProviderModelsPanel provider={mockProvider} models={mockModels} onEdit={vi.fn()} />)
    expect(screen.getByText('gpt-4')).toBeInTheDocument()
    expect(screen.getByText('gpt-3.5')).toBeInTheDocument()
    expect(screen.queryByText('claude-3')).not.toBeInTheDocument()
  })

  it('calls onEdit when edit button clicked', () => {
    const onEdit = vi.fn()
    render(<ProviderModelsPanel provider={mockProvider} models={mockModels} onEdit={onEdit} />)
    fireEvent.click(screen.getByText('编辑配置'))
    expect(onEdit).toHaveBeenCalled()
  })
})
```

- [ ] **Step 3: 运行测试**

Run: `cd frontend && npm test -- ProviderModelsPanel.test.tsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ProviderModelsPanel.tsx frontend/src/components/ProviderModelsPanel.test.tsx
git commit -m "feat: add ProviderModelsPanel component"
```

---

### Task 4: 新建 ProviderEditModal 组件

**Files:**
- Create: `frontend/src/components/ProviderEditModal.tsx`
- Test: `frontend/src/components/ProviderEditModal.test.tsx`

**说明:** 弹窗编辑 Provider 配置。

- [ ] **Step 1: 编写组件代码**

```tsx
import { useState, useEffect } from 'react'
import type { ProviderInfo, ProviderUpdate } from '../types'

interface ProviderEditModalProps {
  provider: ProviderInfo | null
  isOpen: boolean
  onClose: () => void
  onSave: (name: string, update: ProviderUpdate) => void
  isSaving: boolean
}

export function ProviderEditModal({ provider, isOpen, onClose, onSave, isSaving }: ProviderEditModalProps) {
  const [apiBase, setApiBase] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [timeout, setTimeout] = useState(30)
  const [showKey, setShowKey] = useState(false)

  useEffect(() => {
    if (provider) {
      setApiBase(provider.api_base)
      setApiKey(provider.key_type.startsWith('env:') ? `os.environ/${provider.key_type.replace('env:', '')}` : '')
      setTimeout(provider.timeout)
      setShowKey(false)
    }
  }, [provider])

  if (!isOpen || !provider) return null

  const handleSave = () => {
    const update: ProviderUpdate = { api_base: apiBase, timeout }
    if (apiKey.trim()) {
      update.api_key = apiKey
    }
    onSave(provider.name, update)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 overflow-hidden">
        <div className="p-4 border-b border-[rgba(0,0,0,0.06)] flex items-center justify-between">
          <h3 className="text-base font-semibold text-[#1d1d1f]">编辑 Provider: {provider.name}</h3>
          <button onClick={onClose} className="text-[#a1a1a6] hover:text-[#1d1d1f] transition-colors text-xl">&times;</button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-mono text-[#86868b] uppercase tracking-wider mb-1.5">API Base</label>
            <input
              type="text"
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
              className="w-full px-3 py-2 rounded-xl text-sm text-[#1d1d1f] input-glow"
            />
          </div>
          <div>
            <label className="block text-xs font-mono text-[#86868b] uppercase tracking-wider mb-1.5">API Key</label>
            <div className="flex items-center gap-2">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                placeholder={provider.masked_key || '未配置 API Key'}
                onChange={(e) => setApiKey(e.target.value)}
                className="flex-1 px-3 py-2 rounded-xl text-sm text-[#1d1d1f] input-glow placeholder-[#a1a1a6]"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="text-[#a1a1a6] hover:text-[#007AFF] text-xs px-2 transition-colors"
                title={showKey ? '隐藏' : '显示'}
              >
                {showKey ? '🙈' : '👁'}
              </button>
            </div>
            <p className="text-xs text-[#a1a1a6] mt-1">留空则保持现有配置</p>
          </div>
          <div>
            <label className="block text-xs font-mono text-[#86868b] uppercase tracking-wider mb-1.5">Timeout</label>
            <input
              type="number"
              value={timeout}
              onChange={(e) => setTimeout(parseInt(e.target.value) || 30)}
              className="w-32 px-3 py-2 rounded-xl text-sm text-[#1d1d1f] input-glow"
            />
          </div>
        </div>
        <div className="p-4 border-t border-[rgba(0,0,0,0.06)] flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-sm text-[#86868b] hover:bg-[rgba(0,0,0,0.03)] transition-all"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 bg-[#007AFF] text-white rounded-xl text-sm font-medium hover:bg-[#0051D5] disabled:opacity-50 transition-all"
          >
            {isSaving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 编写测试**

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ProviderEditModal } from './ProviderEditModal'
import type { ProviderInfo } from '../types'

const mockProvider: ProviderInfo = {
  name: 'openai', api_base: 'https://api.openai.com', timeout: 30, key_type: 'env:OPENAI_API_KEY', has_key: true, masked_key: 'sk-****',
}

describe('ProviderEditModal', () => {
  it('does not render when closed', () => {
    render(<ProviderEditModal provider={mockProvider} isOpen={false} onClose={vi.fn()} onSave={vi.fn()} isSaving={false} />)
    expect(screen.queryByText('编辑 Provider: openai')).not.toBeInTheDocument()
  })

  it('renders form when open', () => {
    render(<ProviderEditModal provider={mockProvider} isOpen={true} onClose={vi.fn()} onSave={vi.fn()} isSaving={false} />)
    expect(screen.getByText('编辑 Provider: openai')).toBeInTheDocument()
    expect(screen.getByDisplayValue('https://api.openai.com')).toBeInTheDocument()
  })

  it('calls onSave with correct data', () => {
    const onSave = vi.fn()
    render(<ProviderEditModal provider={mockProvider} isOpen={true} onClose={vi.fn()} onSave={onSave} isSaving={false} />)
    fireEvent.change(screen.getByDisplayValue('https://api.openai.com'), { target: { value: 'https://new.api.com' } })
    fireEvent.click(screen.getByText('保存'))
    expect(onSave).toHaveBeenCalledWith('openai', { api_base: 'https://new.api.com', timeout: 30 })
  })

  it('calls onClose when cancel clicked', () => {
    const onClose = vi.fn()
    render(<ProviderEditModal provider={mockProvider} isOpen={true} onClose={onClose} onSave={vi.fn()} isSaving={false} />)
    fireEvent.click(screen.getByText('取消'))
    expect(onClose).toHaveBeenCalled()
  })
})
```

- [ ] **Step 3: 运行测试**

Run: `cd frontend && npm test -- ProviderEditModal.test.tsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ProviderEditModal.tsx frontend/src/components/ProviderEditModal.test.tsx
git commit -m "feat: add ProviderEditModal component"
```

---

### Task 5: 新建 ModelsExplorer 组件

**Files:**
- Create: `frontend/src/components/ModelsExplorer.tsx`
- Test: `frontend/src/components/ModelsExplorer.test.tsx`

**说明:** 模型清单页面容器，组合 ProviderSidebar + ProviderModelsPanel + ProviderEditModal，管理 selectedProvider 状态。

- [ ] **Step 1: 编写组件代码**

```tsx
import { useState, useMemo, useEffect } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import { ProviderSidebar } from './ProviderSidebar'
import { ProviderModelsPanel } from './ProviderModelsPanel'
import { ProviderEditModal } from './ProviderEditModal'

export function ModelsExplorer() {
  const { providers, models, saveProviders, isSavingProviders, toast, clearToast } = useDashboardStore()
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null)
  const [editModalOpen, setEditModalOpen] = useState(false)

  // 默认选中第一个 provider
  useEffect(() => {
    if (providers.length > 0 && !selectedProvider) {
      setSelectedProvider(providers[0].name)
    }
  }, [providers, selectedProvider])

  // 若当前选中的 provider 已不存在，回退到第一个
  useEffect(() => {
    if (selectedProvider && providers.length > 0 && !providers.find((p) => p.name === selectedProvider)) {
      setSelectedProvider(providers[0].name)
    }
  }, [providers, selectedProvider])

  const modelsCount = useMemo(() => {
    const count: Record<string, number> = {}
    providers.forEach((p) => {
      count[p.name] = models.filter((m) => m.provider === p.name).length
    })
    return count
  }, [providers, models])

  const currentProvider = providers.find((p) => p.name === selectedProvider) || null

  const handleSave = async (name: string, update: { api_base: string; api_key?: string; timeout: number }) => {
    await saveProviders({ [name]: update })
    setEditModalOpen(false)
  }

  // Toast auto dismiss
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => clearToast(), 3000)
      return () => clearTimeout(timer)
    }
  }, [toast, clearToast])

  return (
    <div className="space-y-4">
      {/* Toast */}
      {toast && (
        <div className={`glass-card rounded-xl p-3 flex items-center justify-between border ${
          toast.type === 'success' ? 'border-[rgba(52,199,89,0.2)]' : 'border-[rgba(255,59,48,0.2)]'
        }`}>
          <p className={`text-sm ${toast.type === 'success' ? 'text-[#34C759]' : 'text-[#FF3B30]'}`}>{toast.message}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <ProviderSidebar
            providers={providers}
            selectedProvider={selectedProvider}
            modelsCount={modelsCount}
            onSelect={setSelectedProvider}
          />
        </div>
        <div className="lg:col-span-2">
          <ProviderModelsPanel
            provider={currentProvider}
            models={models}
            onEdit={() => setEditModalOpen(true)}
          />
        </div>
      </div>

      <ProviderEditModal
        provider={currentProvider}
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        onSave={handleSave}
        isSaving={isSavingProviders}
      />
    </div>
  )
}
```

- [ ] **Step 2: 编写测试**

```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ModelsExplorer } from './ModelsExplorer'

vi.mock('../store/useDashboardStore', () => ({
  useDashboardStore: vi.fn((selector) => {
    const state = {
      providers: [
        { name: 'openai', api_base: 'https://api.openai.com', timeout: 30, key_type: 'env:OPENAI_API_KEY', has_key: true },
      ],
      models: [
        { name: 'gpt-4', provider: 'openai', available: true, quality: 10, cost: 4, context: 8192, supported_tasks: ['chat'] },
      ],
      saveProviders: vi.fn(),
      isSavingProviders: false,
      toast: null,
      clearToast: vi.fn(),
    }
    return selector ? selector(state) : state
  }),
}))

describe('ModelsExplorer', () => {
  it('renders sidebar and models panel', () => {
    render(<ModelsExplorer />)
    expect(screen.getByText('openai')).toBeInTheDocument()
    expect(screen.getByText('gpt-4')).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: 运行测试**

Run: `cd frontend && npm test -- ModelsExplorer.test.tsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ModelsExplorer.tsx frontend/src/components/ModelsExplorer.test.tsx
git commit -m "feat: add ModelsExplorer component"
```

---

### Task 6: 重构 App.tsx 并更新测试

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

**说明:** 引入 Tab 导航，条件渲染两个页面。

- [ ] **Step 1: 修改 App.tsx**

完整替换为：

```tsx
import { useEffect, useState } from 'react'
import { useDashboardStore } from './store/useDashboardStore'
import { Header } from './components/Header'
import { DashboardPage } from './components/DashboardPage'
import { ModelsExplorer } from './components/ModelsExplorer'

function App() {
  const { fetchAll, error, clearError } = useDashboardStore()
  const [activeTab, setActiveTab] = useState<'dashboard' | 'models'>('dashboard')

  // Auto refresh every 5 seconds
  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 5000)
    return () => clearInterval(interval)
  }, [fetchAll])

  return (
    <div className="min-h-screen bg-[#f5f5f7] bg-tech-grid bg-tech-gradient relative">
      <div className="fixed top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-black/5 to-transparent pointer-events-none" />

      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 relative z-10">
        {/* Error Alert */}
        {error && (
          <div className="glass-card rounded-2xl p-4 flex items-center justify-between border border-red-400/20">
            <p className="text-sm text-[#FF3B30]">{error}</p>
            <button
              onClick={clearError}
              className="text-sm text-[#FF3B30] hover:text-[#FF3B30]/70 transition-colors"
            >
              关闭
            </button>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="glass-card rounded-2xl p-1.5 inline-flex gap-1">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-5 py-2 rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
              activeTab === 'dashboard'
                ? 'bg-[rgba(0,122,255,0.08)] text-[#007AFF] shadow-sm'
                : 'text-[#86868b] hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
            仪表盘
          </button>
          <button
            onClick={() => setActiveTab('models')}
            className={`px-5 py-2 rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
              activeTab === 'models'
                ? 'bg-[rgba(0,122,255,0.08)] text-[#007AFF] shadow-sm'
                : 'text-[#86868b] hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
            </svg>
            模型清单
          </button>
        </div>

        {/* Page Content */}
        {activeTab === 'dashboard' ? <DashboardPage /> : <ModelsExplorer />}
      </main>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 text-center text-sm text-[#a1a1a6] relative z-10">
        Smart Router Dashboard
      </footer>
    </div>
  )
}

export default App
```

- [ ] **Step 2: 更新 App.test.tsx**

完整替换为：

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import App from './App'

vi.mock('./store/useDashboardStore', () => ({
  useDashboardStore: vi.fn((selector) => {
    const state = {
      status: { running: true, pid: 1234, uptime_seconds: 3600, service_url: 'http://localhost:4000', version: '1.0.0' },
      models: [],
      providers: [],
      dryRunResult: null,
      isLoading: false,
      error: null,
      toast: null,
      fetchAll: vi.fn(),
      clearError: vi.fn(),
      runDryRun: vi.fn(),
      stopService: vi.fn(),
      saveProviders: vi.fn(),
      setModelsFilter: vi.fn(),
      setModelsSort: vi.fn(),
      clearToast: vi.fn(),
    }
    return selector ? selector(state) : state
  }),
}))

describe('App', () => {
  it('renders dashboard tab by default', () => {
    render(<App />)
    expect(screen.getByText('仪表盘')).toBeInTheDocument()
    expect(screen.getByText('模型清单')).toBeInTheDocument()
  })

  it('switches to models tab when clicked', () => {
    render(<App />)
    fireEvent.click(screen.getByText('模型清单'))
    // ModelsExplorer 会展示 ProviderSidebar 的空状态
    expect(screen.getByText('暂无 Provider 数据')).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: 运行测试**

Run: `cd frontend && npm test -- App.test.tsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: add Tab navigation to App, wire DashboardPage and ModelsExplorer"
```

---

### Task 7: 清理旧组件引用（可选但推荐）

**Files:**
- Modify: `frontend/src/App.tsx`（已在 Task 6 中完成移除引用）

**说明:** 现有 `ProvidersTable.tsx` 和 `ModelsTable.tsx` 不再被 `App.tsx` 引用，但仍保留在仓库中供后续清理或作为独立页面使用。本次不做删除操作。

---

### Task 8: 运行全部测试

- [ ] **Step 1: 运行全部前端测试**

Run: `cd frontend && npm test`
Expected: 全部测试通过

- [ ] **Step 2: 构建验证**

Run: `cd frontend && npm run build`
Expected: 构建成功，无 TypeScript 错误

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "test: verify all tests pass after tab navigation refactor"
```

---

## Spec 覆盖检查

| Spec 需求 | 对应 Task |
|-----------|-----------|
| App 内状态管理 activeTab | Task 6 |
| Tab 导航栏样式 | Task 6 |
| 仪表盘页精简版 | Task 1 |
| 模型清单页左右分栏 | Task 5 |
| ProviderSidebar 含配置摘要 | Task 2 |
| ProviderModelsPanel 含模型列表 | Task 3 |
| ProviderEditModal 编辑配置 | Task 4 |
| 默认选中第一个 Provider | Task 5 |
| 选中 Provider 失效回退 | Task 5 |
| 自动刷新保留 | Task 6 |
| 测试覆盖 | 每个 Task 含测试 |

---

## 自检清单

- [x] 无 TBD / TODO / placeholder
- [x] 每个步骤包含完整代码
- [x] 类型名称一致（ProviderUpdate, ProviderInfo, ModelInfo）
- [x] 文件路径使用绝对 frontend/src/ 前缀
- [x] 测试代码与实现代码同时提供
- [x] 提交命令包含正确文件
