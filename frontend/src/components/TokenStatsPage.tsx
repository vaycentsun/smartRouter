import { useTranslation } from '../i18n/useTranslation'
import { TokenStatsOverview } from './TokenStatsOverview'
import { TokenStatsTable } from './TokenStatsTable'
import { TokenStatsChart } from './TokenStatsChart'

export function TokenStatsPage() {
  const { t } = useTranslation()
  return (
    <div className="space-y-6">
      <TokenStatsOverview />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="tech-card rounded-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-1 h-4 bg-[#00d4aa]" />
            <h3 className="text-sm font-medium text-[#636366] uppercase tracking-wider font-mono">
              {t('模型消耗明细')}
            </h3>
          </div>
          <TokenStatsTable />
        </div>
        <div className="tech-card rounded-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-1 h-4 bg-[#00d4aa]" />
            <h3 className="text-sm font-medium text-[#636366] uppercase tracking-wider font-mono">
              {t('Token 分布')}
            </h3>
          </div>
          <TokenStatsChart />
        </div>
      </div>
    </div>
  )
}
