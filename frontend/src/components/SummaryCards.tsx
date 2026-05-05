import { useDashboardStore } from '../store/useDashboardStore'

export function SummaryCards() {
  const { analyticsSummary, isLoadingAnalytics } = useDashboardStore()

  const stats = [
    {
      label: '总成本',
      value: analyticsSummary?.total_cost,
      format: (v: number) => `¥${v.toFixed(2)}`,
      sub: '累计费用',
      accent: 'blue',
      showIncomplete: analyticsSummary?.incomplete && analyticsSummary?.total_cost !== null,
    },
    {
      label: '总请求数',
      value: analyticsSummary?.total_requests,
      format: (v: number) => v.toLocaleString(),
      sub: '次 API 调用',
      accent: 'purple',
      showIncomplete: false,
    },
    {
      label: '总 Token 数',
      value: analyticsSummary?.total_tokens,
      format: (v: number) => v.toLocaleString(),
      sub: 'Token 消耗',
      accent: 'green',
      showIncomplete: false,
    },
    {
      label: '日均成本',
      value: analyticsSummary?.avg_daily_cost,
      format: (v: number) => `¥${v.toFixed(2)}`,
      sub: '平均每天',
      accent: 'orange',
      showIncomplete: analyticsSummary?.incomplete && analyticsSummary?.avg_daily_cost !== null,
    },
  ]

  const accentMap: Record<string, { border: string; text: string; glow: string; bg: string }> = {
    blue: {
      border: 'border-[rgba(0,122,255,0.12)]',
      text: 'text-[#007AFF]',
      glow: 'shadow-[rgba(0,122,255,0.06)]',
      bg: 'bg-[rgba(0,122,255,0.05)]',
    },
    purple: {
      border: 'border-[rgba(175,82,222,0.12)]',
      text: 'text-[#AF52DE]',
      glow: 'shadow-[rgba(175,82,222,0.06)]',
      bg: 'bg-[rgba(175,82,222,0.05)]',
    },
    green: {
      border: 'border-[rgba(52,199,89,0.12)]',
      text: 'text-[#34C759]',
      glow: 'shadow-[rgba(52,199,89,0.06)]',
      bg: 'bg-[rgba(52,199,89,0.05)]',
    },
    orange: {
      border: 'border-[rgba(255,149,0,0.12)]',
      text: 'text-[#FF9500]',
      glow: 'shadow-[rgba(255,149,0,0.06)]',
      bg: 'bg-[rgba(255,149,0,0.05)]',
    },
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat) => {
        const style = accentMap[stat.accent]
        const hasValue = stat.value !== undefined && stat.value !== null && !isLoadingAnalytics
        return (
          <div
            key={stat.label}
            className={`glass-card rounded-2xl p-5 ${style.border} hover:shadow-lg ${style.glow}`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-[#86868b] font-mono uppercase tracking-wider">
                {stat.label}
              </span>
              {stat.showIncomplete && (
                <span className="text-[#FF9500] text-sm font-bold" title="部分模型未配置单价">
                  *
                </span>
              )}
            </div>
            <p className={`text-3xl font-bold ${style.text} tracking-tight`}>
              {hasValue ? stat.format(stat.value as number) : '--'}
            </p>
            <p className="text-xs text-[#a1a1a6] mt-1 font-mono">{stat.sub}</p>
          </div>
        )
      })}
    </div>
  )
}
