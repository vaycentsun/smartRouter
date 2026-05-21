import { useEffect } from 'react'
import { useTranslation } from '../i18n/I18nProvider'
import { useDashboardStore } from '../store/useDashboardStore'

export function ErrorStatsPanel() {
  const { t } = useTranslation()
  const { errorStats, isLoadingErrorStats, fetchErrorStats } = useDashboardStore()

  useEffect(() => {
    fetchErrorStats()
  }, [fetchErrorStats])

  if (isLoadingErrorStats && !errorStats) {
    return (
      <div className="card-base p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-[#E8EDEB] rounded-lg w-1/3"></div>
          <div className="h-20 bg-[#E8EDEB] rounded-lg"></div>
        </div>
      </div>
    )
  }

  if (!errorStats || errorStats.total_requests === 0) {
    return (
      <div className="card-base p-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-1 h-5 bg-[#E65C5C] rounded-full" />
          <h3 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider">{t('Error Stats')}</h3>
        </div>
        <p className="text-sm text-[#889397]">{t('NO DATA')}</p>
      </div>
    )
  }

  return (
    <div className="card-base p-5 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-1 h-5 bg-[#E65C5C] rounded-full" />
          <div>
            <h3 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider">{t('Error Stats')}</h3>
            <p className="text-xs text-[#889397] mt-0.5">
              {errorStats.total_requests} {t('REQUESTS')} · {t('FAILURE RATE')} {errorStats.failure_rate}%
            </p>
          </div>
        </div>
        <button
          onClick={() => fetchErrorStats()}
          className="text-xs text-[#00A34D] hover:opacity-70 transition-opacity font-medium uppercase"
        >
          {t('REFRESH')}
        </button>
      </div>

      {/* 模型失败率表格 */}
      {errorStats.models.length > 0 && (
        <div>
          <h4 className="text-xs text-[#889397] font-medium uppercase tracking-wider mb-3">
            {t('Model Failure Ranking')}
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#E8EDEB]">
                  <th className="text-left py-2 px-2 text-xs text-[#889397] font-medium uppercase tracking-wider">{t('Model')}</th>
                  <th className="text-left py-2 px-2 text-xs text-[#889397] font-medium uppercase tracking-wider">{t('Provider')}</th>
                  <th className="text-right py-2 px-2 text-xs text-[#889397] font-medium uppercase tracking-wider">{t('Attempts')}</th>
                  <th className="text-right py-2 px-2 text-xs text-[#889397] font-medium uppercase tracking-wider">{t('Failures')}</th>
                  <th className="text-right py-2 px-2 text-xs text-[#889397] font-medium uppercase tracking-wider">{t('Success')}</th>
                </tr>
              </thead>
              <tbody>
                {errorStats.models.map((model) => (
                  <tr key={model.model} className="data-row">
                    <td className="py-2 px-2 text-[#001E2B] text-xs font-medium">{model.model}</td>
                    <td className="py-2 px-2 text-[#889397] text-xs">{model.provider}</td>
                    <td className="py-2 px-2 text-right text-[#001E2B] text-xs mono-num">{model.total_attempts}</td>
                    <td className="py-2 px-2 text-right">
                      <span className={`text-xs mono-num ${model.failures > 0 ? 'text-[#E65C5C]' : 'text-[#00A34D]'}`}>
                        {model.failures}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right">
                      <span className={`text-xs mono-num ${model.success_rate >= 90 ? 'text-[#00A34D]' : model.success_rate >= 70 ? 'text-[#F08B1E]' : 'text-[#E65C5C]'}`}>
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
          <h4 className="text-xs text-[#889397] font-medium uppercase tracking-wider mb-3">
            {t('Error Type Distribution')}
          </h4>
          <div className="space-y-2">
            {errorStats.error_types.map((et) => (
              <div key={et.error_type} className="flex items-center justify-between">
                <span className="text-sm text-[#001E2B] text-xs font-medium">{et.error_type}</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-1.5 bg-[#E8EDEB] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#E65C5C] rounded-full"
                      style={{
                        width: `${Math.min(100, (et.count / errorStats.total_failures) * 100)}%`,
                      }}
                    />
                  </div>
                  <span className="text-xs text-[#889397] mono-num w-8 text-right">{et.count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Provider 错误分布 */}
      {errorStats.provider_errors.length > 0 && (
        <div>
          <h4 className="text-xs text-[#889397] font-medium uppercase tracking-wider mb-3">
            {t('Provider Error Distribution')}
          </h4>
          <div className="grid grid-cols-2 gap-2">
            {errorStats.provider_errors.map((pe) => (
              <div
                key={`${pe.provider}:${pe.error_type}`}
                className="flex items-center justify-between p-2 rounded-lg bg-[#F9FBFA] border border-[#E8EDEB]"
              >
                <div>
                  <span className="text-xs text-[#001E2B] font-medium">{pe.provider}</span>
                  <span className="text-xs text-[#889397] ml-1">{pe.error_type}</span>
                </div>
                <span className="text-xs font-semibold text-[#E65C5C] mono-num">{pe.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
