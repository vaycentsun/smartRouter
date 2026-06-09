import { useEffect } from 'react'
import { useTranslation } from '../i18n/useTranslation'
import { useDashboardStore } from '../store/useDashboardStore'

export function ErrorStatsPanel() {
  const { t } = useTranslation()
  const { errorStats, isLoadingErrorStats, fetchErrorStats } = useDashboardStore()

  useEffect(() => {
    fetchErrorStats()
  }, [fetchErrorStats])

  if (isLoadingErrorStats && !errorStats) {
    return (
      <div className="tech-card rounded-sm p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-[#1a1a2e] rounded-sm w-1/3"></div>
          <div className="h-20 bg-[#1a1a2e] rounded-sm"></div>
        </div>
      </div>
    )
  }

  if (!errorStats || errorStats.total_requests === 0) {
    return (
      <div className="tech-card rounded-sm p-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-1 h-4 bg-[#e74c3c]" />
          <h3 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('Error Stats')}</h3>
        </div>
        <p className="text-sm text-[#636366] font-mono">{t('NO DATA')}</p>
      </div>
    )
  }

  return (
    <div className="tech-card rounded-sm p-5 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-1 h-4 bg-[#e74c3c]" />
          <div>
            <h3 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('Error Stats')}</h3>
            <p className="text-xs text-[#636366] mt-0.5 font-mono">
              {errorStats.total_requests} {t('REQUESTS')} · {t('FAILURE RATE')} {errorStats.failure_rate}%
            </p>
          </div>
        </div>
        <button
          onClick={() => fetchErrorStats()}
          className="text-xs text-[#00d4aa] hover:opacity-70 transition-opacity font-mono uppercase"
        >
          {t('REFRESH')}
        </button>
      </div>

      {/* 模型失败率表格 */}
      {errorStats.models.length > 0 && (
        <div>
          <h4 className="text-[10px] text-[#636366] font-mono uppercase tracking-widest mb-3">
            {t('Model Failure Ranking')}
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#1a1a2e]">
                  <th className="text-left py-2 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest">{t('Model')}</th>
                  <th className="text-left py-2 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest">{t('Provider')}</th>
                  <th className="text-right py-2 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest">{t('Attempts')}</th>
                  <th className="text-right py-2 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest">{t('Failures')}</th>
                  <th className="text-right py-2 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest">{t('Success')}</th>
                </tr>
              </thead>
              <tbody>
                {errorStats.models.map((model) => (
                  <tr key={model.model} className="data-row">
                    <td className="py-2 px-2 text-[#e8e8ed] font-mono text-xs">{model.model}</td>
                    <td className="py-2 px-2 text-[#636366] font-mono text-xs">{model.provider}</td>
                    <td className="py-2 px-2 text-right text-[#e8e8ed] font-mono text-xs">{model.total_attempts}</td>
                    <td className="py-2 px-2 text-right">
                      <span className={`font-mono text-xs ${model.failures > 0 ? 'text-[#e74c3c]' : 'text-[#00d4aa]'}`}>
                        {model.failures}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right">
                      <span className={`font-mono text-xs ${model.success_rate >= 90 ? 'text-[#00d4aa]' : model.success_rate >= 70 ? 'text-[#f39c12]' : 'text-[#e74c3c]'}`}>
                        {model.success_rate}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 错误类型分布 */}
      {errorStats.error_types.length > 0 && (
        <div>
          <h4 className="text-[10px] text-[#636366] font-mono uppercase tracking-widest mb-3">
            {t('Error Type Distribution')}
          </h4>
          <div className="space-y-2">
            {errorStats.error_types.map((et) => (
              <div key={et.error_type} className="flex items-center justify-between">
                <span className="text-sm text-[#e8e8ed] font-mono text-xs">{et.error_type}</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-1.5 bg-[#1a1a2e] rounded-sm overflow-hidden">
                    <div
                      className="h-full bg-[#e74c3c] rounded-sm"
                      style={{
                        width: `${Math.min(100, (et.count / errorStats.total_failures) * 100)}%`,
                      }}
                    />
                  </div>
                  <span className="text-xs text-[#636366] font-mono w-8 text-right">{et.count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Provider 错误分布 */}
      {errorStats.provider_errors.length > 0 && (
        <div>
          <h4 className="text-[10px] text-[#636366] font-mono uppercase tracking-widest mb-3">
            {t('Provider Error Distribution')}
          </h4>
          <div className="grid grid-cols-2 gap-2">
            {errorStats.provider_errors.map((pe) => (
              <div
                key={`${pe.provider}:${pe.error_type}`}
                className="flex items-center justify-between p-2 rounded-sm bg-[#0a0a0f] border border-[#1a1a2e]"
              >
                <div>
                  <span className="text-xs text-[#e8e8ed] font-mono">{pe.provider}</span>
                  <span className="text-xs text-[#636366] font-mono ml-1">{pe.error_type}</span>
                </div>
                <span className="text-xs font-mono text-[#e74c3c]">{pe.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
