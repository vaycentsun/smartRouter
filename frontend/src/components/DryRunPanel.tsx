import { useState } from 'react'
import { useTranslation } from '../i18n/useTranslation'
import { useDashboardStore } from '../store/useDashboardStore'

export function DryRunPanel() {
  const { t } = useTranslation()
  const [prompt, setPrompt] = useState('')
  const { runDryRun, dryRunResult, isLoading, error, clearError } =
    useDashboardStore()

  const handleSubmit = async () => {
    if (!prompt.trim()) return
    clearError()
    await runDryRun(prompt.trim(), 'auto')
  }

  return (
    <div className="tech-card rounded-sm">
      <div className="p-4 border-b border-[#1a1a2e] flex items-center gap-3">
        <div className="w-1 h-4 bg-[#00d4aa]" />
        <h2 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('Route Test')}</h2>
      </div>
      <div className="p-5 space-y-4">
        {/* Prompt Input */}
        <div>
          <label className="block text-[10px] text-[#636366] font-mono uppercase tracking-widest mb-2">
            {t('Input Prompt')}
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="例如：帮我写一个快速排序算法"
            rows={3}
            className="w-full px-3 py-2 rounded-sm text-sm tech-input resize-none"
          />
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={isLoading || !prompt.trim()}
          className="tech-btn tech-btn-primary w-full px-4 py-2.5 rounded-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? t('TESTING') : t('EXECUTE TEST')}
        </button>

        {/* Error */}
        {error && (
          <div className="p-3 bg-[rgba(231,76,60,0.04)] border border-[rgba(231,76,60,0.12)] rounded-sm">
            <p className="text-sm text-[#e74c3c] font-mono">{error}</p>
          </div>
        )}

        {/* Result */}
        {dryRunResult && !dryRunResult.error && (
          <div className="p-4 bg-[#0a0a0f] border border-[#1a1a2e] rounded-sm space-y-3">
            <h3 className="text-[10px] text-[#00d4aa] font-mono uppercase tracking-widest">{t('Routing Result')}</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="flex justify-between py-1 border-b border-[#1a1a2e]">
                <span className="text-[#636366] text-xs font-mono">{t('TASK_TYPE')}</span>
                <span className="font-medium text-[#e8e8ed] font-mono">{dryRunResult.task_type}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1a1a2e]">
                <span className="text-[#636366] text-xs font-mono">{t('CONFIDENCE')}</span>
                <span className="font-medium text-[#e8e8ed] font-mono">{dryRunResult.task_confidence}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1a1a2e]">
                <span className="text-[#636366] text-xs font-mono">{t('DIFFICULTY')}</span>
                <span className="font-medium text-[#e8e8ed] font-mono">{dryRunResult.difficulty}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1a1a2e]">
                <span className="text-[#636366] text-xs font-mono">{t('MODEL')}</span>
                <span className="font-medium text-[#00d4aa] font-mono">{dryRunResult.selected_model}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1a1a2e]">
                <span className="text-[#636366] text-xs font-mono">{t('STRATEGY')}</span>
                <span className="font-medium text-[#e8e8ed] font-mono">{dryRunResult.strategy}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1a1a2e]">
                <span className="text-[#636366] text-xs font-mono">{t('SCORE')}</span>
                <span className="font-medium text-[#e8e8ed] font-mono">{dryRunResult.score}</span>
              </div>
            </div>
            <div className="pt-2">
              <span className="text-[#636366] text-[10px] font-mono uppercase tracking-widest">{t('REASON')}</span>
              <p className="text-sm text-[#e8e8ed] mt-1 leading-relaxed font-mono text-xs">
                {dryRunResult.reason}
              </p>
            </div>
            {dryRunResult.fallback_chain && dryRunResult.fallback_chain.length > 0 && (
              <div className="pt-2 border-t border-[#1a1a2e]">
                <span className="text-[#636366] text-[10px] font-mono uppercase tracking-widest">{t('FALLBACK CHAIN')}</span>
                <p className="text-sm text-[#e8e8ed] mt-1 leading-relaxed font-medium font-mono">
                  {dryRunResult.selected_model}
                  <span className="text-[#636366] mx-1">→</span>
                  {dryRunResult.fallback_chain.join(' → ')}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
