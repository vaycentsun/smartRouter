import { useDashboardStore } from '../store/useDashboardStore'

export function AlertSummaryCard() {
  const { alertRules, alertHistory } = useDashboardStore()
  const activeRules = alertRules.filter((r) => r.enabled).length
  const todayTriggers = alertHistory.filter((h) => {
    const triggerDate = new Date(h.timestamp * 1000).toISOString().split('T')[0]
    const today = new Date().toISOString().split('T')[0]
    return triggerDate === today
  }).length

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="glass-card rounded-2xl p-6">
        <h3 className="text-sm font-medium text-[#86868b] mb-2">活跃规则</h3>
        <p className="text-3xl font-semibold text-[#1d1d1f]">{activeRules}</p>
        <p className="text-xs text-[#86868b] mt-1">共 {alertRules.length} 条规则</p>
      </div>
      <div className="glass-card rounded-2xl p-6">
        <h3 className="text-sm font-medium text-[#86868b] mb-2">今日触发</h3>
        <p className="text-3xl font-semibold text-[#1d1d1f]">{todayTriggers}</p>
        <p className="text-xs text-[#86868b] mt-1">最近 24 小时</p>
      </div>
    </div>
  )
}
