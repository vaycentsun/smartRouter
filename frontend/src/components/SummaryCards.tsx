import { useTranslation } from '../i18n/I18nProvider'
import { useDashboardStore } from '../store/useDashboardStore'

export function SummaryCards() {
  const { analyticsSummary, isLoadingAnalytics } = useDashboardStore()
  const { t } = useTranslation()

  const stats = [
    {
      label: t('Total Cost'),
      value: analyticsSummary?.total_cost,
      format: (v: number) => `¥${v.toFixed(2)}`,
      sub: t('ACCUMULATED'),
      accent: 'blue',
      showIncomplete: analyticsSummary?.incomplete && analyticsSummary?.total_cost !== null,
    },
    {
      label: t('Daily Avg'),
      value: analyticsSummary?.avg_daily_cost,
      format: (v: number) => `¥${v.toFixed(2)}`,
      sub: t('PER DAY'),
      accent: 'orange',
      showIncomplete: analyticsSummary?.incomplete && analyticsSummary?.avg_daily_cost !== null,
    },
    {
      label: t('Total Requests'),
      value: analyticsSummary?.total_requests,
      format: (v: number) => v.toLocaleString(),
      sub: t('API CALLS'),
      accent: 'purple',
      showIncomplete: false,
    },
    {
      label: t('Total Tokens'),
      value: analyticsSummary?.total_tokens,
      format: (v: number) => v.toLocaleString(),
      sub: t('CONSUMED'),
      accent: 'green',
      showIncomplete: false,
    },
    {
      label: t('Input Tokens'),
      value: analyticsSummary?.total_prompt_tokens,
      format: (v: number) => v.toLocaleString(),
      sub: t('PROMPT'),
      accent: 'indigo',
      showIncomplete: false,
    },
    {
      label: t('Reasoning Tokens'),
      value: analyticsSummary?.total_reasoning_tokens,
      format: (v: number) => v.toLocaleString(),
      sub: t('REASONING'),
      accent: 'pink',
      showIncomplete: false,
    },
    {
      label: t('Output Tokens'),
      value: analyticsSummary?.total_completion_tokens,
      format: (v: number) => v.toLocaleString(),
      sub: t('COMPLETION'),
      accent: 'teal',
      showIncomplete: false,
    },
    {
      label: t('Cache Hits'),
      value: analyticsSummary?.total_cached_tokens,
      format: (v: number) => v.toLocaleString(),
      sub: t('CACHED'),
      accent: 'cyan',
      showIncomplete: false,
    },
  ]

  const accentMap: Record<string, { border: string; text: string; glow: string; bg: string }> = {
    blue: {
      border: 'border-[rgba(52,152,219,0.12)]',
      text: 'text-[#3498db]',
      glow: 'shadow-[rgba(52,152,219,0.06)]',
      bg: 'bg-[rgba(52,152,219,0.05)]',
    },
    purple: {
      border: 'border-[rgba(155,89,182,0.12)]',
      text: 'text-[#9b59b6]',
      glow: 'shadow-[rgba(155,89,182,0.06)]',
      bg: 'bg-[rgba(155,89,182,0.05)]',
    },
    green: {
      border: 'border-[rgba(0,212,170,0.12)]',
      text: 'text-[#00d4aa]',
      glow: 'shadow-[rgba(0,212,170,0.06)]',
      bg: 'bg-[rgba(0,212,170,0.05)]',
    },
    orange: {
      border: 'border-[rgba(243,156,18,0.12)]',
      text: 'text-[#f39c12]',
      glow: 'shadow-[rgba(243,156,18,0.06)]',
      bg: 'bg-[rgba(243,156,18,0.05)]',
    },
    pink: {
      border: 'border-[rgba(232,67,147,0.12)]',
      text: 'text-[#e84393]',
      glow: 'shadow-[rgba(232,67,147,0.06)]',
      bg: 'bg-[rgba(232,67,147,0.05)]',
    },
    cyan: {
      border: 'border-[rgba(0,206,201,0.12)]',
      text: 'text-[#00cec9]',
      glow: 'shadow-[rgba(0,206,201,0.06)]',
      bg: 'bg-[rgba(0,206,201,0.05)]',
    },
    indigo: {
      border: 'border-[rgba(108,92,231,0.12)]',
      text: 'text-[#6c5ce7]',
      glow: 'shadow-[rgba(108,92,231,0.06)]',
      bg: 'bg-[rgba(108,92,231,0.05)]',
    },
    teal: {
      border: 'border-[rgba(26,188,156,0.12)]',
      text: 'text-[#1abc9c]',
      glow: 'shadow-[rgba(26,188,156,0.06)]',
      bg: 'bg-[rgba(26,188,156,0.05)]',
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
            className={`tech-card p-5 relative corner-bracket ${style.border} hover:shadow-lg ${style.glow}`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] text-[#636366] font-mono uppercase tracking-widest">
                {stat.label}
              </span>
              {stat.showIncomplete && (
                <span className="text-[#f39c12] text-sm font-bold font-mono" title="部分模型未配置单价">
                  *
                </span>
              )}
            </div>
            <p className={`text-3xl font-bold ${style.text} mono-num tracking-tight`}>
              {hasValue ? stat.format(stat.value as number) : '--'}
            </p>
            <p className="text-xs text-[#636366] mt-1 font-mono">{stat.sub}</p>
          </div>
        )
      })}
    </div>
  )
}
