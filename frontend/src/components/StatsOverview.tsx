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
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
      ),
      accent: 'cyan',
    },
    {
      label: 'Provider 数',
      value: totalProviders,
      sub: `${missingKeys} Key 缺失`,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      ),
      accent: 'violet',
    },
    {
      label: '服务状态',
      value: status?.running ? '运行中' : '已停止',
      sub: status?.running ? `PID: ${status.pid}` : '-',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
      accent: status?.running ? 'emerald' : 'red',
    },
  ]

  const accentMap: Record<string, { border: string; text: string; glow: string; bg: string }> = {
    cyan: {
      border: 'border-cyan-400/20',
      text: 'text-cyan-300',
      glow: 'shadow-cyan-400/10',
      bg: 'bg-cyan-400/5',
    },
    violet: {
      border: 'border-violet-400/20',
      text: 'text-violet-300',
      glow: 'shadow-violet-400/10',
      bg: 'bg-violet-400/5',
    },
    emerald: {
      border: 'border-emerald-400/20',
      text: 'text-emerald-300',
      glow: 'shadow-emerald-400/10',
      bg: 'bg-emerald-400/5',
    },
    red: {
      border: 'border-red-400/20',
      text: 'text-red-300',
      glow: 'shadow-red-400/10',
      bg: 'bg-red-400/5',
    },
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {stats.map((stat) => {
        const style = accentMap[stat.accent]
        return (
          <div
            key={stat.label}
            className={`glass-card rounded-xl p-5 ${style.border} hover:shadow-lg ${style.glow}`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-slate-400 font-mono uppercase tracking-wider">
                {stat.label}
              </span>
              <span className={`${style.text} ${style.bg} p-1.5 rounded-lg`}>
                {stat.icon}
              </span>
            </div>
            <p className={`text-3xl font-bold ${style.text} tracking-tight`}>
              {stat.value}
            </p>
            <p className="text-xs text-slate-500 mt-1 font-mono">{stat.sub}</p>
          </div>
        )
      })}
    </div>
  )
}
