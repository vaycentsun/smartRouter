import { useDashboardStore } from '../store/useDashboardStore'
import type { ModelInfo } from '../types'

const SORTABLE_KEYS = ['name', 'provider', 'available', 'quality', 'cost', 'context']

function SortIcon({ active, asc }: { active: boolean; asc: boolean }) {
  if (!active) return <span className="text-slate-600 ml-1 text-xs">↕</span>
  return <span className="text-cyan-400 ml-1 text-xs">{asc ? '↑' : '↓'}</span>
}

function TaskBadge({ task }: { task: string }) {
  return (
    <span className="inline-block px-2 py-0.5 bg-cyan-400/5 text-cyan-300/80 text-xs rounded border border-cyan-400/10 mr-1">
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
          className={`text-xs ${i < filled ? colorClass : 'text-slate-700'}`}
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
    <div className="glass-card rounded-xl">
      <div className="p-4 border-b border-cyan-400/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-1 h-5 bg-cyan-400 rounded-full" />
          <h2 className="text-base font-semibold text-slate-100 tracking-wide">模型列表</h2>
        </div>
        <input
          type="text"
          placeholder="搜索模型或 Provider..."
          value={modelsFilter}
          onChange={(e) => setModelsFilter(e.target.value)}
          className="px-3 py-1.5 rounded-lg text-sm text-slate-200 placeholder-slate-600 input-glow w-64"
        />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-800/40 text-slate-400">
            <tr>
              {SORTABLE_KEYS.map((key) => (
                <th
                  key={key}
                  onClick={() => setModelsSort(key)}
                  className="px-4 py-3 font-mono text-xs uppercase tracking-wider cursor-pointer hover:text-cyan-300 select-none transition-colors"
                >
                  {keyLabels[key]}
                  <SortIcon active={modelsSort.key === key} asc={modelsSort.asc} />
                </th>
              ))}
              <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">支持任务</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/20">
            {sorted.map((model) => (
              <tr key={model.name} className="table-row-hover">
                <td className="px-4 py-3 font-medium text-slate-200">
                  {model.name}
                </td>
                <td className="px-4 py-3 text-slate-400">{model.provider}</td>
                <td className="px-4 py-3">
                  {model.available ? (
                    <span className="inline-flex items-center gap-1.5 text-emerald-400 text-sm">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-glow" />
                      在线
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-red-400 text-sm">
                      <span className="w-1.5 h-1.5 rounded-full bg-red-400 pulse-glow-red" />
                      离线
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <StarRating value={model.quality} colorClass="text-amber-400" />
                </td>
                <td className="px-4 py-3">
                  <StarRating value={model.cost} colorClass="text-emerald-400" />
                </td>
                <td className="px-4 py-3 text-slate-400 font-mono text-xs">
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
                      <span className="text-xs text-slate-500">
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
                  className="px-4 py-8 text-center text-slate-500"
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
