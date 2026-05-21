import { useState } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import type { ModelInfo, ProviderInfo } from '../types'
import { useTranslation } from '../i18n/I18nProvider'

function SortIcon({ active, asc }: { active: boolean; asc: boolean }) {
  if (!active) return <span className="text-[#889397] ml-1 text-xs">↕</span>
  return <span className="text-[#00A34D] ml-1 text-xs">{asc ? '▲' : '▼'}</span>
}

function TaskBadge({ task }: { task: string }) {
  return (
    <span className="inline-block px-2 py-0.5 bg-[#2F87FC]/5 text-[#2F87FC] text-[10px] rounded-full mr-1 font-medium uppercase tracking-wider">
      {task}
    </span>
  )
}

interface ProviderModelsPanelProps {
  provider: ProviderInfo | null
  models: ModelInfo[]
  onEdit: () => void
  onSaveKey: (apiKey: string) => void
  isSaving: boolean
  onCheckHealth?: (providerName: string) => Promise<void>
  isCheckingHealth?: boolean
  onAddModel?: () => void
}

const healthStatusMap: Record<string, { label: string; color: string; dotColor: string; tooltip: string }> = {
  available: { label: 'ONLINE', color: 'text-[#00A34D]', dotColor: 'bg-[#00A34D]', tooltip: 'Model confirmed available' },
  not_found: { label: 'NOT FOUND', color: 'text-[#8B6F18]', dotColor: 'bg-[#F08B1E]', tooltip: 'Model not found in provider list' },
  unconfigured: { label: 'UNCONFIGURED', color: 'text-[#889397]', dotColor: 'bg-[#889397]', tooltip: 'API Key not configured' },
  auth_error: { label: 'AUTH ERROR', color: 'text-[#E65C5C]', dotColor: 'bg-[#E65C5C]', tooltip: 'API Key invalid or insufficient permissions' },
  rate_limited: { label: 'RATE LIMITED', color: 'text-[#8B6F18]', dotColor: 'bg-[#F08B1E]', tooltip: 'Rate limit exceeded' },
  network_error: { label: 'NETWORK ERR', color: 'text-[#E65C5C]', dotColor: 'bg-[#E65C5C]', tooltip: 'Network connection failed' },
  unknown: { label: 'CHECK FAILED', color: 'text-[#E65C5C]', dotColor: 'bg-[#E65C5C]', tooltip: 'Health check failed' },
  checking: { label: 'CHECKING', color: 'text-[#2F87FC]', dotColor: 'bg-[#2F87FC]', tooltip: 'Checking provider connectivity' },
}

function getModelHealthDisplay(model: ModelInfo, provider?: ProviderInfo, providerHealth?: { status: string; error?: string | null }) {
  const providerEnabled = provider ? (provider.enabled ?? true) : true
  if (!providerEnabled) {
    return { label: 'DISABLED', color: 'text-[#889397]', dotColor: 'bg-[#889397]', tooltip: 'Provider disabled by user' }
  }

  if (!model.enabled) {
    return { label: 'DISABLED', color: 'text-[#889397]', dotColor: 'bg-[#889397]', tooltip: 'Model disabled by user' }
  }

  const status = model.health_status

  if (providerHealth?.status === 'checking' || status === 'checking') {
    return healthStatusMap.checking
  }

  if (status && healthStatusMap[status]) {
    const mapping = healthStatusMap[status]
    if (providerHealth?.error && status !== 'available' && status !== 'not_found') {
      return { ...mapping, tooltip: providerHealth.error }
    }
    return mapping
  }

  if (model.available) {
    return { label: 'CONFIGURED', color: 'text-[#00A34D]', dotColor: 'bg-[#00A34D]', tooltip: 'API Key configured (not yet checked)' }
  }
  return { label: 'UNCONFIGURED', color: 'text-[#889397]', dotColor: 'bg-[#889397]', tooltip: 'API Key not configured' }
}

export function ProviderModelsPanel({
  provider,
  models,
  onEdit,
  onSaveKey,
  isSaving,
  onCheckHealth,
  isCheckingHealth = false,
  onAddModel,
}: ProviderModelsPanelProps) {
  const { t } = useTranslation()
  const [keyInput, setKeyInput] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [sortConfig, setSortConfig] = useState<{ key: string; asc: boolean }>({ key: 'name', asc: true })
  const toggleModel = useDashboardStore((state) => state.toggleModel)
  const isTogglingModel = useDashboardStore((state) => state.isTogglingModel)
  const toggleProvider = useDashboardStore((state) => state.toggleProvider)
  const isTogglingProvider = useDashboardStore((state) => state.isTogglingProvider)

  const handleSort = (key: string) => {
    setSortConfig((prev) => ({
      key,
      asc: prev.key === key ? !prev.asc : true,
    }))
  }

  if (!provider) {
    return (
      <div className="card-base p-8 flex items-center justify-center min-h-[300px]">
        <p className="text-[#889397]">{t('SELECT A PROVIDER')}</p>
      </div>
    )
  }

  const providerModels = models.filter((m) => m.provider === provider.name)
  const providerHealth = provider.health
  const providerToggling = isTogglingProvider[provider.name] || false
  const providerEnabled = provider.enabled ?? true

  const sortedModels = [...providerModels].sort((a, b) => {
    let aVal: string | number
    let bVal: string | number
    if (sortConfig.key === 'status') {
      aVal = getModelHealthDisplay(a, provider, providerHealth).label
      bVal = getModelHealthDisplay(b, provider, providerHealth).label
    } else if (sortConfig.key === 'context') {
      aVal = a.context
      bVal = b.context
    } else if (sortConfig.key === 'tasks') {
      aVal = a.supported_tasks.length
      bVal = b.supported_tasks.length
    } else {
      aVal = a.name
      bVal = b.name
    }
    const mult = sortConfig.asc ? 1 : -1
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return aVal.localeCompare(bVal) * mult
    }
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return (aVal - bVal) * mult
    }
    return 0
  })

  return (
    <div className="card-base overflow-hidden">
      <div className="p-4 border-b border-[#E8EDEB] flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#001E2B]">{provider.name}</h2>
          <p className="text-xs text-[#889397] mt-0.5">{providerModels.length} {t('MODELS')}</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="relative inline-flex items-center cursor-pointer mr-2">
            <input
              type="checkbox"
              className="sr-only peer"
              checked={providerEnabled}
              onChange={() => toggleProvider(provider.name, !providerEnabled)}
              disabled={providerToggling}
            />
            <div className={`w-9 h-5 rounded-full peer relative transition-all ${providerEnabled ? 'bg-[#00A34D]' : 'bg-[#C1C7C6]'} ${providerToggling ? 'opacity-50' : ''}`}>
              <div className={`absolute top-[2px] left-[2px] w-4 h-4 rounded-full bg-white transition-all shadow-sm ${providerEnabled ? 'translate-x-4' : ''}`} />
            </div>
          </label>
          {onCheckHealth && (
            <button
              onClick={() => onCheckHealth(provider.name)}
              disabled={isCheckingHealth}
              className="px-3 py-2 rounded-full text-xs font-semibold border border-[#E8EDEB] text-[#5C6C75] hover:bg-[#F4F7F6] hover:text-[#001E2B] transition-all disabled:opacity-50 flex items-center gap-1.5"
            >
              {isCheckingHealth ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-[#889397] border-t-transparent rounded-full animate-spin" />
                  {t('CHECKING')}
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  {t('CHECK')}
                </>
              )}
            </button>
          )}
          <button
            onClick={onEdit}
            className="btn-primary px-3 py-2 text-xs"
          >
            {t('EDIT')}
          </button>
          {onAddModel && (
            <button
              onClick={onAddModel}
              className="btn-primary px-3 py-2 text-xs"
            >
              + Add Model
            </button>
          )}
        </div>
      </div>

      {/* API Key 编辑区域 */}
      <div className="px-4 py-3 border-b border-[#E8EDEB] bg-[#F9FBFA]">
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium text-[#889397] uppercase tracking-wider whitespace-nowrap">
            {t('API KEY')}
          </span>
          {provider.key_type.startsWith('env:') ? (
            <span className="text-sm text-[#889397]">
              {t('ENV')}: {provider.key_type}
            </span>
          ) : (
            <>
              <div className="flex-1 flex items-center gap-2">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={keyInput}
                  placeholder={provider.masked_key || t('NOT SET')}
                  onChange={(e) => setKeyInput(e.target.value)}
                  className="flex-1 min-w-0 px-3 py-1.5 rounded-lg text-sm tech-input placeholder-[#889397]"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="text-[#889397] hover:text-[#00A34D] text-xs px-2 transition-colors font-medium"
                  title={showKey ? t('HIDE') : t('SHOW')}
                >
                  {showKey ? t('HIDE') : t('SHOW')}
                </button>
              </div>
              <button
                onClick={() => { onSaveKey(keyInput); setKeyInput('') }}
                disabled={isSaving}
                className="btn-primary px-3 py-1.5 text-xs disabled:opacity-50"
              >
                {isSaving ? t('SAVING') : t('SAVE')}
              </button>
            </>
          )}
        </div>
        {!provider.key_type.startsWith('env:') && (
          <p className="text-xs text-[#889397] mt-1.5">
            {provider.has_key ? t('saveHint1') : t('saveHint2')}
          </p>
        )}
      </div>

      {providerModels.length === 0 ? (
        <div className="p-8 text-center text-[#889397]">
          {t('NO MODELS')}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="border-b border-[#E8EDEB]">
              <tr>
                <th onClick={() => handleSort('name')} className="px-4 py-3 text-xs text-[#889397] font-medium uppercase tracking-wider cursor-pointer hover:text-[#00A34D] select-none transition-colors">
                  {t('MODEL')}<SortIcon active={sortConfig.key === 'name'} asc={sortConfig.asc} />
                </th>
                <th onClick={() => handleSort('status')} className="px-4 py-3 text-xs text-[#889397] font-medium uppercase tracking-wider cursor-pointer hover:text-[#00A34D] select-none transition-colors">
                  {t('STATUS')}<SortIcon active={sortConfig.key === 'status'} asc={sortConfig.asc} />
                </th>
                <th className="px-4 py-3 text-xs text-[#889397] font-medium uppercase tracking-wider">{t('ENABLED')}</th>
                <th onClick={() => handleSort('context')} className="px-4 py-3 text-xs text-[#889397] font-medium uppercase tracking-wider cursor-pointer hover:text-[#00A34D] select-none transition-colors">
                  {t('CTX')}<SortIcon active={sortConfig.key === 'context'} asc={sortConfig.asc} />
                </th>
                <th className="px-4 py-3 text-xs text-[#889397] font-medium uppercase tracking-wider">{t('TASKS')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8EDEB]">
              {sortedModels.map((model) => {
                const display = getModelHealthDisplay(model, provider, providerHealth)
                const toggleKey = `${model.provider}/${model.name}`
                const isToggling = isTogglingModel[toggleKey] || false
                return (
                  <tr key={model.name} className="data-row">
                    <td className="px-4 py-3 font-medium text-[#001E2B] text-xs">{model.name}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 ${display.color} text-xs cursor-help font-medium`}
                        title={display.tooltip}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${display.dotColor} ${display.label === 'CHECKING' ? 'animate-pulse' : ''}`} />
                        {t(display.label)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <label className="relative inline-flex items-center cursor-pointer" title={!providerEnabled ? 'Provider 已禁用' : ''}>
                        <input
                          type="checkbox"
                          className="sr-only peer"
                          checked={model.enabled}
                          onChange={() => toggleModel(model.provider, model.name, !model.enabled)}
                          disabled={isToggling || !providerEnabled}
                        />
                        <div className={`w-9 h-5 rounded-full peer relative transition-all ${model.enabled ? 'bg-[#00A34D]' : 'bg-[#C1C7C6]'} ${isToggling || !providerEnabled ? 'opacity-50' : ''}`}>
                          <div className={`absolute top-[2px] left-[2px] w-4 h-4 rounded-full bg-white transition-all shadow-sm ${model.enabled ? 'translate-x-4' : ''}`} />
                        </div>
                      </label>
                    </td>
                    <td className="px-4 py-3 text-[#889397] text-xs mono-num">
                      {model.context >= 1000 ? `${Math.floor(model.context / 1000)}k` : model.context}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {model.supported_tasks.slice(0, 3).map((task) => (
                          <TaskBadge key={task} task={task} />
                        ))}
                        {model.supported_tasks.length > 3 && (
                          <span className="text-[10px] text-[#889397] font-medium">+{model.supported_tasks.length - 3}</span>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
