import { StatsOverview } from './StatsOverview'
import { StatusCard } from './StatusCard'
import { DryRunPanel } from './DryRunPanel'
import { ErrorStatsPanel } from './ErrorStatsPanel'

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <StatsOverview />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <StatusCard />
          <ErrorStatsPanel />
        </div>
        <div className="lg:col-span-2">
          <DryRunPanel />
        </div>
      </div>
    </div>
  )
}
