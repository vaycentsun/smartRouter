import { useMemo } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'

export function ModelOverrideBar() {
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
      className={`glass-card rounded-2xl transition-all duration-300 ${
        isEnabled
          ? 'border-[rgba(255,149,0,0.25)] shadow-[0_0_0_1px_rgba(255,149,0,0.1)]'
          : 'border-[rgba(0,0,0,0.06)]'
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
                ? 'bg-[rgba(255,149,0,0.12)] text-[#FF9500] border border-[rgba(255,149,0,0.3)]'
                : 'bg-[rgba(0,0,0,0.03)] text-[#86868b] border border-[rgba(0,0,0,0.06)]'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isEnabled ? 'bg-[#FF9500]' : 'bg-[#a1a1a6]'
              }`}
            />
            {isEnabled ? '覆盖已启用' : '使用默认路由'}
          </span>
          <span className="text-xs text-[#86868b] truncate">
            {isEnabled
              ? `路由策略已暂停，请求将直接发送至 ${modelOverride.provider}/${modelOverride.model}`
              : '选择 Provider 和 Model 以绕过路由策略，直接指定目标模型'}
          </span>
        </div>

        {/* 右侧：控件 */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex items-center gap-2">
            <label
              htmlFor="override-provider"
              className="text-xs text-[#86868b] font-mono uppercase tracking-wider hidden sm:inline"
            >
              Provider
            </label>
            <select
              id="override-provider"
              value={modelOverride.provider || ''}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="h-8 px-2 py-1 rounded-lg text-sm input-glow min-w-[120px]"
              aria-label="选择 Provider"
            >
              <option value="">请选择</option>
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
              className="text-xs text-[#86868b] font-mono uppercase tracking-wider hidden sm:inline"
            >
              Model
            </label>
            <select
              id="override-model"
              value={modelOverride.model || ''}
              onChange={(e) => handleModelChange(e.target.value)}
              disabled={!modelOverride.provider}
              className="h-8 px-2 py-1 rounded-lg text-sm input-glow min-w-[140px] disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="选择模型"
            >
              <option value="">
                {modelOverride.provider ? '请选择' : '先选 Provider'}
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
              className="h-8 px-3 rounded-lg text-xs font-medium border border-[rgba(255,59,48,0.2)] text-[#FF3B30] bg-[rgba(255,59,48,0.06)] hover:bg-[rgba(255,59,48,0.1)] hover:border-[rgba(255,59,48,0.3)] transition-all"
              aria-label="回到默认路由"
            >
              回到默认路由
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
