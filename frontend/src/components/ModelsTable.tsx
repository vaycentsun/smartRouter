import { useDashboardStore } from '../store/useDashboardStore'
import type { ModelInfo } from '../types'

const SORTABLE_KEYS = ['name', 'provider', 'available', 'quality', 'cost', 'context']

function SortIcon({ active, asc }: { active: boolean; asc: boolean }) {
  if (!active) return <span className="text-gray-300 ml-1">↕</span>
  return <span className="text-blue-600 ml-1">{asc ? '↑' : '↓'}</span>
}

function TaskBadge({ task }: { task: string }) {
  return (
    <span className="inline-block px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded mr-1">
      {task}
    </span>
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

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">模型列表</h2>
        <input
          type="text"
          placeholder="搜索模型或 Provider..."
          value={modelsFilter}
          onChange={(e) => setModelsFilter(e.target.value)}
          className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
        />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-50 text-gray-700">
            <tr>
              {SORTABLE_KEYS.map((key) => (
                <th
                  key={key}
                  onClick={() => setModelsSort(key)}
                  className="px-4 py-3 font-medium cursor-pointer hover:bg-gray-100 select-none"
                >
                  {key === 'name'
                    ? '模型名称'
                    : key === 'provider'
                    ? 'Provider'
                    : key === 'available'
                    ? '状态'
                    : key === 'quality'
                    ? 'Quality'
                    : key === 'cost'
                    ? 'Cost'
                    : 'Context'}
                  <SortIcon
                    active={modelsSort.key === key}
                    asc={modelsSort.asc}
                  />
                </th>
              ))}
              <th className="px-4 py-3 font-medium">支持任务</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {sorted.map((model) => (
              <tr key={model.name} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">
                  {model.name}
                </td>
                <td className="px-4 py-3 text-gray-600">{model.provider}</td>
                <td className="px-4 py-3">
                  {model.available ? (
                    <span className="text-green-600 font-medium">✓</span>
                  ) : (
                    <span className="text-red-500 font-medium">✗</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    <span className="text-yellow-500">
                      {'★'.repeat(Math.floor(model.quality / 2))}
                    </span>
                    <span className="text-gray-300">
                      {'★'.repeat(5 - Math.floor(model.quality / 2))}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    <span className="text-green-500">
                      {'★'.repeat(Math.floor(model.cost / 2))}
                    </span>
                    <span className="text-gray-300">
                      {'★'.repeat(5 - Math.floor(model.cost / 2))}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-600">
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
                      <span className="text-xs text-gray-400">
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
                  className="px-4 py-8 text-center text-gray-500"
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
