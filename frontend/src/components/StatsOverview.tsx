import { useDashboardStore } from '../store/useDashboardStore'

export function StatsOverview() {
  const { models, providers, status } = useDashboardStore()

  const availableModels = models.filter((m) => m.available).length
  const totalProviders = providers.length
  const missingKeys = providers.filter((p) => !p.has_key).length

  const stats = [
    {
      label: '模型总数',
      value: models.length,
      sub: `${availableModels} 可用`,
      color: 'text-blue-600',
    },
    {
      label: 'Provider 数',
      value: totalProviders,
      sub: `${missingKeys} Key 缺失`,
      color: 'text-purple-600',
    },
    {
      label: '服务状态',
      value: status?.running ? '运行中' : '已停止',
      sub: status?.running ? `PID: ${status.pid}` : '-',
      color: status?.running ? 'text-green-600' : 'text-red-600',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {stats.map((stat) => (
        <div key={stat.label} className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500 mb-1">{stat.label}</p>
          <p className={`text-3xl font-bold ${stat.color}`}>{stat.value}</p>
          <p className="text-xs text-gray-400 mt-1">{stat.sub}</p>
        </div>
      ))}
    </div>
  )
}
