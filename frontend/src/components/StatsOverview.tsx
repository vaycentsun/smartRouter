import { useTranslation } from '../i18n/I18nProvider'
import { useDashboardStore } from '../store/useDashboardStore'

export function StatsOverview() {
  const { t } = useTranslation()
  const { models, providers, status } = useDashboardStore()

  const availableModels = models.filter((m) => m.available).length
  const totalProviders = providers.length
  const missingKeys = providers.filter((p) => !p.has_key).length

  const stats = [
    {
      label: t('Models Total'),
      value: models.length,
      sub: `${availableModels} ${t('AVAILABLE')}`,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
      ),
      accent: 'blue',
    },
    {
      label: t('Providers'),
      value: totalProviders,
      sub: `${missingKeys} ${t('KEY MISSING')}`,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      ),
      accent: 'purple',
    },
    {
      label: t('Service Status'),
      value: status?.running ? t('RUNNING') : t('STOPPED'),
      sub: status?.running ? `${t('PID')}: ${status.pid}` : '-',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
      accent: status?.running ? 'green' : 'red',
    },
  ]

  const accentMap: Record<string, { border: string; text: string; bg: string; iconBg: string }> = {
    blue: {
      border: 'border-[#2F87FC]/20',
      text: 'text-[#2F87FC]',
      bg: 'bg-[#2F87FC]/5',
      iconBg: 'bg-[#2F87FC]/10',
    },
    purple: {
      border: 'border-[#B45AF2]/20',
      text: 'text-[#B45AF2]',
      bg: 'bg-[#B45AF2]/5',
      iconBg: 'bg-[#B45AF2]/10',
    },
    green: {
      border: 'border-[#00A34D]/20',
      text: 'text-[#00A34D]',
      bg: 'bg-[#00A34D]/5',
      iconBg: 'bg-[#00A34D]/10',
    },
    red: {
      border: 'border-[#E65C5C]/20',
      text: 'text-[#E65C5C]',
      bg: 'bg-[#E65C5C]/5',
      iconBg: 'bg-[#E65C5C]/10',
    },
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {stats.map((stat) => {
        const style = accentMap[stat.accent]
        return (
          <div
            key={stat.label}
            className={`card-base p-5 border ${style.border}`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-[#889397] font-medium uppercase tracking-wider">
                {stat.label}
              </span>
              <span className={`${style.text} ${style.iconBg} p-1.5 rounded-lg`}>
                {stat.icon}
              </span>
            </div>
            <p className={`text-3xl font-semibold ${style.text} mono-num tracking-tight`}>
              {stat.value}
            </p>
            <p className="text-sm text-[#889397] mt-1">{stat.sub}</p>
          </div>
        )
      })}
    </div>
  )
}
