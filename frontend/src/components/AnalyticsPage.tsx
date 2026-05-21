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
        <div className="card-base p-8 text-center">
          <p className="text-sm text-[#889397]">{t('LOADING')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {analyticsError && (
        <div className="card-base rounded-xl p-4 border border-[#E65C5C]/20 bg-[#FDECEC]">
          <p className="text-sm text-[#E65C5C] font-medium">{analyticsError}</p>
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
