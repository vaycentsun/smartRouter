import { useState } from 'react'
import { useTranslation } from '../i18n/I18nProvider'
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
    <div className="card-base">
      <div className="p-4 border-b border-[#E8EDEB] flex items-center gap-3">
        <div className="w-1 h-5 bg-[#00A34D] rounded-full" />
        <h2 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider">{t('Route Test')}</h2>
      </div>
      <div className="p-5 space-y-4">
        {/* Prompt Input */}
        <div>
          <label className="block text-xs text-[#889397] uppercase font-medium tracking-wider mb-2">
            {t('Input Prompt')}
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="例如：帮我写一个快速排序算法"
            rows={3}
            className="w-full px-3 py-2 rounded-lg text-sm tech-input resize-none"
          />
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={isLoading || !prompt.trim()}
          className="btn-primary w-full px-4 py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? t('TESTING') : t('EXECUTE TEST')}
        </button>

        {/* Error */}
        {error && (
          <div className="p-3 bg-[#FDECEC] border border-[#E65C5C]/20 rounded-lg">
            <p className="text-sm text-[#E65C5C]">{error}</p>
          </div>
        )}

        {/* Result */}
        {dryRunResult && !dryRunResult.error && (
          <div className="p-4 bg-[#F9FBFA] border border-[#E8EDEB] rounded-xl space-y-3">
            <h3 className="text-xs text-[#00A34D] font-semibold uppercase tracking-wider">{t('Routing Result')}</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="flex justify-between py-1 border-b border-[#E8EDEB]">
                <span className="text-[#889397] text-xs">{t('TASK_TYPE')}</span>
                <span className="font-medium text-[#001E2B]">{dryRunResult.task_type}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#E8EDEB]">
                <span className="text-[#889397] text-xs">{t('CONFIDENCE')}</span>
                <span className="font-medium text-[#001E2B]">{dryRunResult.task_confidence}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#E8EDEB]">
                <span className="text-[#889397] text-xs">{t('DIFFICULTY')}</span>
                <span className="font-medium text-[#001E2B]">{dryRunResult.difficulty}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#E8EDEB]">
                <span className="text-[#889397] text-xs">{t('MODEL')}</span>
                <span className="font-medium text-[#00A34D]">{dryRunResult.selected_model}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#E8EDEB]">
                <span className="text-[#889397] text-xs">{t('STRATEGY')}</span>
                <span className="font-medium text-[#001E2B]">{dryRunResult.strategy}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#E8EDEB]">
                <span className="text-[#889397] text-xs">{t('SCORE')}</span>
                <span className="font-medium text-[#001E2B]">{dryRunResult.score}</span>
              </div>
            </div>
            <div className="pt-2">
              <span className="text-[#889397] text-xs font-semibold uppercase tracking-wider">{t('REASON')}</span>
              <p className="text-sm text-[#001E2B] mt-1 leading-relaxed">
                {dryRunResult.reason}
              </p>
            </div>
            {dryRunResult.fallback_chain && dryRunResult.fallback_chain.length > 0 && (
              <div className="pt-2 border-t border-[#E8EDEB]">
                <span className="text-[#889397] text-xs font-semibold uppercase tracking-wider">{t('FALLBACK CHAIN')}</span>
                <p className="text-sm text-[#001E2B] mt-1 leading-relaxed font-medium">
                  {dryRunResult.selected_model}
                  <span className="text-[#889397] mx-1">→</span>
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
