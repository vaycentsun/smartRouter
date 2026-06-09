import { useMemo } from 'react'
import { useTranslation } from '../i18n/useTranslation'
import { useDashboardStore } from '../store/useDashboardStore'

export function ModelOverrideBar() {
  const { t } = useTranslation()
  const {
    modelOverrides,
    modelOverride,
    setModelOverride,
    clearModelOverride,
  } = useDashboardStore()

  const providers = useMemo(() => {
    return Object.keys(modelOverrides).sort()
  }, [modelOverrides])

  const models = useMemo(() => {
    if (!modelOverride.provider) return []
    return (modelOverrides[modelOverride.provider] || []).sort()
  }, [modelOverrides, modelOverride.provider])

  const isEnabled = modelOverride.enabled

  const handleProviderChange = (provider: string) => {
    const availableModels = modelOverrides[provider] || []
    const firstModel = availableModels[0] || null
    setModelOverride(provider || null, firstModel)
  }

  const handleModelChange = (model: string) => {
    setModelOverride(modelOverride.provider, model || null)
  }

  return (
    <div
      className={`tech-card rounded-sm transition-all duration-300 ${
        isEnabled
          ? 'border-[rgba(243,156,18,0.25)]'
          : ''
      }`}
      role="region"
      aria-label="模型覆盖配置"
    >
      <div className="px-4 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        {/* 左侧：状态信息 */}
        <div className="flex items-center gap-3 min-w-0">
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-sm text-xs font-mono uppercase tracking-wider shrink-0 border ${
              isEnabled
                ? 'bg-[rgba(243,156,18,0.08)] text-[#f39c12] border-[rgba(243,156,18,0.2)]'
                : 'bg-transparent text-[#636366] border-[#1a1a2e]'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-sm ${
                isEnabled ? 'bg-[#f39c12]' : 'bg-[#636366]'
              }`}
            />
            {isEnabled ? t('OVERRIDE ON') : t('AUTO ROUTE')}
          </span>
          <span className="text-xs text-[#636366] truncate font-mono">
            {isEnabled
              ? `${t('overridePaused')} → ${modelOverride.provider}/${modelOverride.model}`
              : t('overrideHint')}
          </span>
        </div>

        {/* 右侧：控件 */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex items-center gap-2">
            <label
              htmlFor="override-provider"
              className="text-[10px] text-[#636366] font-mono uppercase tracking-widest hidden sm:inline"
            >
              PROVIDER
            </label>
            <select
              id="override-provider"
              value={modelOverride.provider || ''}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="h-8 px-2 py-1 rounded-sm text-sm tech-input min-w-[120px] bg-[#0a0a0f]"
              aria-label="选择 Provider"
            >
              <option value="">{t('SELECT')}</option>
              {providers.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label
              htmlFor="override-model"
              className="text-[10px] text-[#636366] font-mono uppercase tracking-widest hidden sm:inline"
            >
              MODEL
            </label>
            <select
              id="override-model"
              value={modelOverride.model || ''}
              onChange={(e) => handleModelChange(e.target.value)}
              disabled={!modelOverride.provider}
              className="h-8 px-2 py-1 rounded-sm text-sm tech-input min-w-[140px] disabled:opacity-50 disabled:cursor-not-allowed bg-[#0a0a0f]"
              aria-label="选择模型"
            >
              <option value="">
                {modelOverride.provider ? t('SELECT') : t('SELECT PROVIDER')}
              </option>
              {models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          {isEnabled && (
            <button
              onClick={clearModelOverride}
              className="tech-btn tech-btn-danger h-8 px-3 rounded-sm text-xs"
              aria-label="回到默认路由"
            >
              {t('RESET')}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
