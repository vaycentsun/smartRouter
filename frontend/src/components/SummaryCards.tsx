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
      label: '日均成本',
      value: analyticsSummary?.avg_daily_cost,
      format: (v: number) => `¥${v.toFixed(2)}`,
      sub: '平均每天',
      accent: 'orange',
      showIncomplete: analyticsSummary?.incomplete && analyticsSummary?.avg_daily_cost !== null,
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
      label: '输入 Token',
      value: analyticsSummary?.total_prompt_tokens,
      format: (v: number) => v.toLocaleString(),
      sub: 'Prompt 消耗',
      accent: 'indigo',
      showIncomplete: false,
    },
    {
      label: '推理 Token',
      value: analyticsSummary?.total_reasoning_tokens,
      format: (v: number) => v.toLocaleString(),
      sub: 'Reasoning 消耗',
      accent: 'pink',
      showIncomplete: false,
    },
    {
      label: '输出 Token',
      value: analyticsSummary?.total_completion_tokens,
      format: (v: number) => v.toLocaleString(),
      sub: 'Completion 消耗',
      accent: 'teal',
      showIncomplete: false,
    },
    {
      label: '缓存命中',
      value: analyticsSummary?.total_cached_tokens,
      format: (v: number) => v.toLocaleString(),
      sub: 'Cached 命中',
      accent: 'cyan',
      showIncomplete: false,
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
    pink: {
      border: 'border-[rgba(255,45,85,0.12)]',
      text: 'text-[#FF2D55]',
      glow: 'shadow-[rgba(255,45,85,0.06)]',
      bg: 'bg-[rgba(255,45,85,0.05)]',
    },
    cyan: {
      border: 'border-[rgba(0,199,204,0.12)]',
      text: 'text-[#00C7CC]',
      glow: 'shadow-[rgba(0,199,204,0.06)]',
      bg: 'bg-[rgba(0,199,204,0.05)]',
    },
    indigo: {
      border: 'border-[rgba(88,86,214,0.12)]',
      text: 'text-[#5856D6]',
      glow: 'shadow-[rgba(88,86,214,0.06)]',
      bg: 'bg-[rgba(88,86,214,0.05)]',
    },
    teal: {
      border: 'border-[rgba(48,209,88,0.12)]',
      text: 'text-[#30D158]',
      glow: 'shadow-[rgba(48,209,88,0.06)]',
      bg: 'bg-[rgba(48,209,88,0.05)]',
    },
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
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
