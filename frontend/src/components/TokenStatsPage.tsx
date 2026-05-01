import { TokenStatsOverview } from './TokenStatsOverview'
import { TokenStatsTable } from './TokenStatsTable'
import { TokenStatsChart } from './TokenStatsChart'

export function TokenStatsPage() {
  return (
    <div className="space-y-6">
      <TokenStatsOverview />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card rounded-2xl p-5">
          <h3 className="text-sm font-medium text-[#86868b] mb-4">
            模型消耗明细
          </h3>
          <TokenStatsTable />
        </div>
        <div className="glass-card rounded-2xl p-5">
          <h3 className="text-sm font-medium text-[#86868b] mb-4">
            Token 分布
          </h3>
          <TokenStatsChart />
        </div>
      </div>
    </div>
  )
}
