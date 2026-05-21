import { useMemo } from 'react'
import { useTranslation } from '../i18n/I18nProvider'
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
      className={`card-base transition-all duration-300 ${
        isEnabled
          ? 'border-[#F08B1E]/30 bg-[#FEF8E8]/30'
          : ''
      }`}
      role="region"
      aria-label="模型覆盖配置"
    >
      <div className="px-4 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        {/* 左侧：状态信息 */}
        <div className="flex items-center gap-3 min-w-0">
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold shrink-0 ${
              isEnabled
                ? 'bg-[#FEF8E8] text-[#8B6F18]'
                : 'bg-[#F4F7F6] text-[#889397]'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isEnabled ? 'bg-[#F08B1E]' : 'bg-[#889397]'
              }`}
            />
            {isEnabled ? t('OVERRIDE ON') : t('AUTO ROUTE')}
          </span>
          <span className="text-xs text-[#889397] truncate">
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
              className="text-xs text-[#889397] font-medium uppercase tracking-wider hidden sm:inline"
            >
              PROVIDER
            </label>
            <select
              id="override-provider"
              value={modelOverride.provider || ''}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="h-9 px-3 py-1 rounded-lg text-sm tech-input min-w-[120px] bg-white"
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
              className="text-xs text-[#889397] font-medium uppercase tracking-wider hidden sm:inline"
            >
              MODEL
            </label>
            <select
              id="override-model"
              value={modelOverride.model || ''}
              onChange={(e) => handleModelChange(e.target.value)}
              disabled={!modelOverride.provider}
              className="h-9 px-3 py-1 rounded-lg text-sm tech-input min-w-[140px] disabled:opacity-50 disabled:cursor-not-allowed bg-white"
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
              className="h-9 px-4 rounded-full text-xs font-semibold bg-[#FDECEC] text-[#E65C5C] border border-[#E65C5C]/20 transition-all hover:bg-[#E65C5C] hover:text-white"
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
