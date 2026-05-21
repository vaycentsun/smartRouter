import { useTranslation } from '../i18n/I18nProvider'
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
      <div className="card-base rounded-xl p-6">
        <h3 className="text-sm font-medium text-[#889397] mb-2">{t('Active Rules')}</h3>
        <p className="text-3xl font-semibold text-[#001E2B]">{activeRules}</p>
        <p className="text-xs text-[#889397] mt-1">{t('Total Rules').replace('{count}', String(alertRules.length))}</p>
      </div>
      <div className="card-base rounded-xl p-6">
        <h3 className="text-sm font-medium text-[#889397] mb-2">{t('Today Triggers')}</h3>
        <p className="text-3xl font-semibold text-[#001E2B]">{todayTriggers}</p>
        <p className="text-xs text-[#889397] mt-1">{t('Last 24h')}</p>
      </div>
    </div>
  )
}
