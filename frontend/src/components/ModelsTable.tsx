import { useTranslation } from '../i18n/useTranslation'
import { useDashboardStore } from '../store/useDashboardStore'
import type { ModelInfo } from '../types'

const SORTABLE_KEYS = ['name', 'provider', 'available', 'quality', 'cost', 'context']

function SortIcon({ active, asc }: { active: boolean; asc: boolean }) {
  if (!active) return <span className="text-[#636366] ml-1 text-xs">↕</span>
  return <span className="text-[#00d4aa] ml-1 text-xs">{asc ? '↑' : '↓'}</span>
}

function TaskBadge({ task }: { task: string }) {
  return (
    <span className="tech-tag tech-tag-accent mr-1">
      {task}
    </span>
  )
}

function StarRating({ value }: { value: number }) {
  return (
    <span className="text-xs font-mono text-[#f39c12]">{value}/10</span>
  )
}

export function ModelsTable() {
  const { t } = useTranslation()
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
    name: t('MODEL'),
    provider: t('PROVIDER'),
    available: t('STATUS'),
    quality: t('QUALITY'),
    cost: t('COST'),
    context: t('CONTEXT'),
  }

  return (
    <div className="tech-card rounded-sm">
      <div className="p-4 border-b border-[#1a1a2e] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-1 h-4 bg-[#00d4aa]" />
          <h2 className="text-base font-semibold text-[#e8e8ed] uppercase tracking-wider font-mono">{t('MODELS')}</h2>
        </div>
        <input
          type="text"
          placeholder={t('SEARCH MODELS...')}
          value={modelsFilter}
          onChange={(e) => setModelsFilter(e.target.value)}
          className="px-3 py-1.5 rounded-sm text-sm input-glow w-64"
        />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-[#0a0a0f] text-[#636366]">
            <tr>
              {SORTABLE_KEYS.map((key) => (
                <th
                  key={key}
                  onClick={() => setModelsSort(key)}
                  className="px-4 py-3 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer hover:text-[#00d4aa] select-none transition-colors"
                >
                  {keyLabels[key]}
                  <SortIcon active={modelsSort.key === key} asc={modelsSort.asc} />
                </th>
              ))}
              <th className="px-4 py-3 text-[10px] text-[#636366] font-mono uppercase tracking-widest">{t('TASKS')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1a1a2e]">
            {sorted.map((model) => (
              <tr key={model.name} className="data-row">
                <td className="px-4 py-3 font-medium text-[#e8e8ed] font-mono">
                  {model.name}
                </td>
                <td className="px-4 py-3 text-[#636366] font-mono">{model.provider}</td>
                <td className="px-4 py-3">
                  {!model.enabled ? (
                    <span className="inline-flex items-center gap-1.5 text-[#636366] text-sm">
                      <span className="w-1.5 h-1.5 rounded-sm bg-[#636366]" />
                      {t('DISABLED')}
                    </span>
                  ) : model.available ? (
                    <span className="inline-flex items-center gap-1.5 text-[#00d4aa] text-sm">
                      <span className="w-1.5 h-1.5 rounded-sm bg-[#00d4aa] pulse-glow" />
                      {t('ONLINE')}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-[#e74c3c] text-sm">
                      <span className="w-1.5 h-1.5 rounded-sm bg-[#e74c3c] pulse-glow" />
                      {t('OFFLINE')}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <StarRating value={model.quality} />
                </td>
                <td className="px-4 py-3">
                  <StarRating value={model.cost} />
                </td>
                <td className="px-4 py-3 text-[#636366] font-mono text-xs">
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
                      <span className="text-xs text-[#636366]">
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
                  className="px-4 py-8 text-center text-[#636366]"
                >
                  {modelsFilter
                    ? t('NO MATCHING MODELS')
                    : t('NO MODEL DATA. CHECK CONFIGURATION.')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
