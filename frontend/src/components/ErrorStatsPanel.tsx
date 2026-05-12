import { useEffect } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'

export function ErrorStatsPanel() {
  const { errorStats, isLoadingErrorStats, fetchErrorStats } = useDashboardStore()

  useEffect(() => {
    fetchErrorStats()
  }, [fetchErrorStats])

  if (isLoadingErrorStats && !errorStats) {
    return (
      <div className="glass-card rounded-2xl p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/3"></div>
          <div className="h-20 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (!errorStats || errorStats.total_requests === 0) {
    return (
      <div className="glass-card rounded-2xl p-6">
        <h3 className="text-sm font-semibold text-[#1d1d1f] mb-2">模型错误统计</h3>
        <p className="text-sm text-[#86868b]">暂无请求数据</p>
      </div>
    )
  }

  return (
    <div className="glass-card rounded-2xl p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#1d1d1f]">模型错误统计</h3>
          <p className="text-xs text-[#86868b] mt-0.5">
            最近 {errorStats.total_requests} 次请求 · 失败率 {errorStats.failure_rate}%
          </p>
        </div>
        <button
          onClick={() => fetchErrorStats()}
          className="text-xs text-[#007AFF] hover:underline"
        >
          刷新
        </button>
      </div>

      {/* 模型失败率表格 */}
      {errorStats.models.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-[#86868b] uppercase tracking-wider mb-3">
            模型失败排行
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[rgba(0,0,0,0.06)]">
                  <th className="text-left py-2 px-2 text-xs text-[#86868b] font-medium">模型</th>
                  <th className="text-left py-2 px-2 text-xs text-[#86868b] font-medium">Provider</th>
                  <th className="text-right py-2 px-2 text-xs text-[#86868b] font-medium">尝试</th>
                  <th className="text-right py-2 px-2 text-xs text-[#86868b] font-medium">失败</th>
                  <th className="text-right py-2 px-2 text-xs text-[#86868b] font-medium">成功率</th>
                </tr>
              </thead>
              <tbody>
                {errorStats.models.map((model) => (
                  <tr key={model.model} className="border-b border-[rgba(0,0,0,0.04)]">
                    <td className="py-2 px-2 text-[#1d1d1f] font-medium">{model.model}</td>
                    <td className="py-2 px-2 text-[#86868b]">{model.provider}</td>
                    <td className="py-2 px-2 text-right text-[#1d1d1f]">{model.total_attempts}</td>
                    <td className="py-2 px-2 text-right">
                      <span className={`font-medium ${model.failures > 0 ? 'text-[#FF3B30]' : 'text-[#34C759]'}`}>
                        {model.failures}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right">
                      <span className={`font-medium ${model.success_rate >= 90 ? 'text-[#34C759]' : model.success_rate >= 70 ? 'text-[#FF9500]' : 'text-[#FF3B30]'}`}>
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
          <h4 className="text-xs font-medium text-[#86868b] uppercase tracking-wider mb-3">
            错误类型分布
          </h4>
          <div className="space-y-2">
            {errorStats.error_types.map((et) => (
              <div key={et.error_type} className="flex items-center justify-between">
                <span className="text-sm text-[#1d1d1f]">{et.error_type}</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-2 bg-[rgba(0,0,0,0.06)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#FF3B30] rounded-full"
                      style={{
                        width: `${Math.min(100, (et.count / errorStats.total_failures) * 100)}%`,
                      }}
                    />
                  </div>
                  <span className="text-xs text-[#86868b] w-8 text-right">{et.count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Provider 错误分布 */}
      {errorStats.provider_errors.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-[#86868b] uppercase tracking-wider mb-3">
            Provider 错误分布
          </h4>
          <div className="grid grid-cols-2 gap-2">
            {errorStats.provider_errors.map((pe) => (
              <div
                key={`${pe.provider}:${pe.error_type}`}
                className="flex items-center justify-between p-2 rounded-lg bg-[rgba(0,0,0,0.03)]"
              >
                <div>
                  <span className="text-xs text-[#1d1d1f] font-medium">{pe.provider}</span>
                  <span className="text-xs text-[#86868b] ml-1">{pe.error_type}</span>
                </div>
                <span className="text-xs font-medium text-[#FF3B30]">{pe.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
