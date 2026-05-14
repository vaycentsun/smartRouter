import { useEffect } from 'react'
import { useTranslation } from '../i18n/I18nProvider'
import { useDashboardStore } from '../store/useDashboardStore'
import { SummaryCards } from './SummaryCards'
import { CostTrendChart } from './CostTrendChart'
import { RequestTrendChart } from './RequestTrendChart'
import { ModelUsageChart } from './ModelUsageChart'
import { TopModelsTable } from './TopModelsTable'
import { RecentRequestsPanel } from './RecentRequestsPanel'

export function AnalyticsPage() {
  const {
    isLoadingAnalytics,
    analyticsError,
    fetchAnalytics,
    recentRequests,
  } = useDashboardStore()
  const { t } = useTranslation()

  useEffect(() => {
    fetchAnalytics(7)
  }, [fetchAnalytics])

  if (isLoadingAnalytics && !analyticsError) {
    return (
      <div className="space-y-6">
        <div className="tech-card rounded-sm p-8 text-center">
          <p className="text-sm text-[#636366] font-mono">{t('LOADING')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {analyticsError && (
        <div className="tech-card rounded-sm p-4 border border-[rgba(231,76,60,0.2)]">
          <p className="text-sm text-[#e74c3c] font-mono">{analyticsError}</p>
        </div>
      )}
      <SummaryCards />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CostTrendChart />
        <RequestTrendChart />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ModelUsageChart />
        <TopModelsTable />
      </div>
      <div className="w-full">
        <RecentRequestsPanel requests={recentRequests} />
      </div>
    </div>
  )
}
