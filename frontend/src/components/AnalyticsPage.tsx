import { useEffect } from 'react'
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

  useEffect(() => {
    fetchAnalytics(7)
  }, [fetchAnalytics])

  if (isLoadingAnalytics && !analyticsError) {
    return (
      <div className="space-y-6">
        <div className="glass-card rounded-2xl p-8 text-center">
          <p className="text-sm text-[#86868b]">加载中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {analyticsError && (
        <div className="glass-card rounded-2xl p-4 border border-red-400/20">
          <p className="text-sm text-[#FF3B30]">{analyticsError}</p>
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
