import { useDashboardStore } from '../store/useDashboardStore'

export function AlertHistoryTable() {
  const { alertHistory } = useDashboardStore()

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <div className="px-6 py-4 border-b border-black/5">
        <h3 className="text-base font-semibold text-[#1d1d1f]">告警历史</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-black/5">
              <th className="text-left font-medium text-[#86868b] px-6 py-3">时间</th>
              <th className="text-left font-medium text-[#86868b] px-6 py-3">规则</th>
              <th className="text-left font-medium text-[#86868b] px-6 py-3">级别</th>
              <th className="text-left font-medium text-[#86868b] px-6 py-3">指标</th>
              <th className="text-left font-medium text-[#86868b] px-6 py-3">当前值 / 阈值</th>
              <th className="text-left font-medium text-[#86868b] px-6 py-3">消息</th>
            </tr>
          </thead>
          <tbody>
            {alertHistory.map((item, index) => (
              <tr key={index} className="border-b border-black/5 last:border-0 hover:bg-[rgba(0,0,0,0.02)]">
                <td className="px-6 py-3 text-[#1d1d1f] whitespace-nowrap">
                  {new Date(item.timestamp * 1000).toLocaleString('zh-CN')}
                </td>
                <td className="px-6 py-3 text-[#1d1d1f]">{item.rule_name}</td>
                <td className="px-6 py-3">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    item.severity === 'critical'
                      ? 'bg-red-100 text-red-700'
                      : item.severity === 'warning'
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-blue-100 text-blue-700'
                  }`}>
                    {item.severity}
                  </span>
                </td>
                <td className="px-6 py-3 text-[#1d1d1f]">{item.metric}</td>
                <td className="px-6 py-3 text-[#1d1d1f]">
                  {item.current_value} / {item.threshold}
                </td>
                <td className="px-6 py-3 text-[#86868b] max-w-xs truncate">{item.message}</td>
              </tr>
            ))}
            {alertHistory.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-sm text-[#86868b]">
                  暂无告警历史
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
