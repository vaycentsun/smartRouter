import { useDashboardStore } from '../store/useDashboardStore'
import type { ModelInfo } from '../types'

const SORTABLE_KEYS = ['name', 'provider', 'available', 'quality', 'cost', 'context']

function SortIcon({ active, asc }: { active: boolean; asc: boolean }) {
  if (!active) return <span className="text-[rgba(0,0,0,0.12)] ml-1 text-xs">↕</span>
  return <span className="text-[#007AFF] ml-1 text-xs">{asc ? '↑' : '↓'}</span>
}

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
        <span
          key={i}
          className={`text-xs ${i < filled ? colorClass : 'text-[rgba(0,0,0,0.08)]'}`}
        >
          ★
        </span>
      ))}
    </div>
  )
}

export function ModelsTable() {
  const { models, modelsFilter, modelsSort, setModelsFilter, setModelsSort } =
    useDashboardStore()

  const filtered = models.filter((m) =>
    m.name.toLowerCase().includes(modelsFilter.toLowerCase()) ||
    m.provider.toLowerCase().includes(modelsFilter.toLowerCase())
  )

  const sorted = [...filtered].sort((a, b) => {
    const key = modelsSort.key as keyof ModelInfo
    const aVal = a[key]
    const bVal = b[key]
    const mult = modelsSort.asc ? 1 : -1

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return aVal.localeCompare(bVal) * mult
    }
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return (aVal - bVal) * mult
    }
    if (typeof aVal === 'boolean' && typeof bVal === 'boolean') {
      return (aVal === bVal ? 0 : aVal ? -1 : 1) * mult
    }
    return 0
  })

  const keyLabels: Record<string, string> = {
    name: '模型名称',
    provider: 'Provider',
    available: '状态',
    quality: 'Quality',
    cost: 'Cost',
    context: 'Context',
  }

  return (
    <div className="glass-card rounded-2xl">
      <div className="p-4 border-b border-[rgba(0,0,0,0.06)] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-1 h-5 bg-[#007AFF] rounded-full" />
          <h2 className="text-base font-semibold text-[#1d1d1f] tracking-wide">模型列表</h2>
        </div>
        <input
          type="text"
          placeholder="搜索模型或 Provider..."
          value={modelsFilter}
          onChange={(e) => setModelsFilter(e.target.value)}
          className="px-3 py-1.5 rounded-xl text-sm input-glow w-64"
        />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-[rgba(0,0,0,0.02)] text-[#86868b]">
            <tr>
              {SORTABLE_KEYS.map((key) => (
                <th
                  key={key}
                  onClick={() => setModelsSort(key)}
                  className="px-4 py-3 font-mono text-xs uppercase tracking-wider cursor-pointer hover:text-[#007AFF] select-none transition-colors"
                >
                  {keyLabels[key]}
                  <SortIcon active={modelsSort.key === key} asc={modelsSort.asc} />
                </th>
              ))}
              <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">支持任务</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[rgba(0,0,0,0.04)]">
            {sorted.map((model) => (
              <tr key={model.name} className="table-row-hover">
                <td className="px-4 py-3 font-medium text-[#1d1d1f]">
                  {model.name}
                </td>
                <td className="px-4 py-3 text-[#86868b]">{model.provider}</td>
                <td className="px-4 py-3">
                  {model.available ? (
                    <span className="inline-flex items-center gap-1.5 text-[#34C759] text-sm">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#34C759] pulse-glow" />
                      在线
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-[#FF3B30] text-sm">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#FF3B30] pulse-glow-red" />
                      离线
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <StarRating value={model.quality} colorClass="text-[#FF9500]" />
                </td>
                <td className="px-4 py-3">
                  <StarRating value={model.cost} colorClass="text-[#FF9500]" />
                </td>
                <td className="px-4 py-3 text-[#86868b] font-mono text-xs">
                  {model.context >= 1000
                    ? `${Math.floor(model.context / 1000)}k`
                    : model.context}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {model.supported_tasks.slice(0, 3).map((task) => (
                      <TaskBadge key={task} task={task} />
                    ))}
                    {model.supported_tasks.length > 3 && (
                      <span className="text-xs text-[#a1a1a6]">
                        +{model.supported_tasks.length - 3}
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="px-4 py-8 text-center text-[#a1a1a6]"
                >
                  {modelsFilter
                    ? '没有匹配的模型'
                    : '暂无模型数据，请检查配置'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
