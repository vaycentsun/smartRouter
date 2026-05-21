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

  const accentMap: Record<string, { border: string; text: string; bg: string }> = {
    blue: {
      border: 'border-[#2F87FC]/20',
      text: 'text-[#2F87FC]',
      bg: 'bg-[#2F87FC]/5',
    },
    purple: {
      border: 'border-[#B45AF2]/20',
      text: 'text-[#B45AF2]',
      bg: 'bg-[#B45AF2]/5',
    },
    green: {
      border: 'border-[#00A34D]/20',
      text: 'text-[#00A34D]',
      bg: 'bg-[#00A34D]/5',
    },
    orange: {
      border: 'border-[#F08B1E]/20',
      text: 'text-[#F08B1E]',
      bg: 'bg-[#F08B1E]/5',
    },
    pink: {
      border: 'border-[#E54B9E]/20',
      text: 'text-[#E54B9E]',
      bg: 'bg-[#E54B9E]/5',
    },
    cyan: {
      border: 'border-[#00A3A3]/20',
      text: 'text-[#00A3A3]',
      bg: 'bg-[#00A3A3]/5',
    },
    indigo: {
      border: 'border-[#6C5CE7]/20',
      text: 'text-[#6C5CE7]',
      bg: 'bg-[#6C5CE7]/5',
    },
    teal: {
      border: 'border-[#023430]/20',
      text: 'text-[#023430]',
      bg: 'bg-[#023430]/5',
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
            className={`card-base p-5 border ${style.border}`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-[#889397] font-medium uppercase tracking-wider">
                {stat.label}
              </span>
              {stat.showIncomplete && (
                <span className="text-[#F08B1E] text-sm font-bold" title="部分模型未配置单价">
                  *
                </span>
              )}
            </div>
            <p className={`text-3xl font-semibold ${style.text} mono-num tracking-tight`}>
              {hasValue ? stat.format(stat.value as number) : '--'}
            </p>
            <p className="text-sm text-[#889397] mt-1">{stat.sub}</p>
          </div>
        )
      })}
    </div>
  )
}
