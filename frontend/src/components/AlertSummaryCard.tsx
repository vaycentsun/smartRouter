import { useTranslation } from '../i18n/useTranslation'
import { useDashboardStore } from '../store/useDashboardStore'

export function AlertSummaryCard() {
  const { t } = useTranslation()
  const { alertRules, alertHistory } = useDashboardStore()
  const activeRules = alertRules.filter((r) => r.enabled).length
  const todayTriggers = alertHistory.filter((h) => {
    const triggerDate = new Date(h.timestamp * 1000).toISOString().split('T')[0]
    const today = new Date().toISOString().split('T')[0]
    return triggerDate === today
  }).length

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="tech-card rounded-sm p-6">
        <h3 className="text-sm font-medium text-[#636366] mb-2 font-mono uppercase tracking-wider">{t('Active Rules')}</h3>
        <p className="text-3xl font-semibold text-[#e8e8ed] mono-num">{activeRules}</p>
        <p className="text-xs text-[#636366] mt-1 font-mono">{t('Total Rules').replace('{count}', String(alertRules.length))}</p>
      </div>
      <div className="tech-card rounded-sm p-6">
        <h3 className="text-sm font-medium text-[#636366] mb-2 font-mono uppercase tracking-wider">{t('Today Triggers')}</h3>
        <p className="text-3xl font-semibold text-[#e8e8ed] mono-num">{todayTriggers}</p>
        <p className="text-xs text-[#636366] mt-1 font-mono">{t('Last 24h')}</p>
      </div>
    </div>
  )
}
