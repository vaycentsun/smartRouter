import { useDashboardStore } from '../store/useDashboardStore'

export function TokenStatsOverview() {
  const { tokenStats } = useDashboardStore()

  const totalRequests = tokenStats.reduce((sum, s) => sum + s.request_count, 0)
  const totalPrompt = tokenStats.reduce((sum, s) => sum + s.prompt_tokens, 0)
  const totalCompletion = tokenStats.reduce((sum, s) => sum + s.completion_tokens, 0)
  const totalReasoning = tokenStats.reduce((sum, s) => sum + (s.reasoning_tokens || 0), 0)
  const totalCached = tokenStats.reduce((sum, s) => sum + (s.cached_tokens || 0), 0)

  const stats = [
    {
      label: '总请求数',
      value: totalRequests,
      sub: '次 API 调用',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      ),
      accent: 'blue',
    },
    {
      label: '总输入 Token',
      value: totalPrompt,
      sub: 'Prompt 消耗',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
        </svg>
      ),
      accent: 'purple',
    },
    {
      label: '总输出 Token',
      value: totalCompletion,
      sub: 'Completion 消耗',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      accent: 'green',
    },
    {
      label: '推理 Token',
      value: totalReasoning,
      sub: 'Reasoning 消耗',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      ),
      accent: 'orange',
    },
    {
      label: '缓存命中',
      value: totalCached,
      sub: 'Cached 命中',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      ),
      accent: 'pink',
    },
  ]

  const accentMap: Record<string, { border: string; text: string; glow: string; bg: string }> = {
    blue: {
      border: 'border-[rgba(0,122,255,0.12)]',
      text: 'text-[#007AFF]',
      glow: 'shadow-[rgba(0,122,255,0.06)]',
      bg: 'bg-[rgba(0,122,255,0.05)]',
    },
    purple: {
      border: 'border-[rgba(175,82,222,0.12)]',
      text: 'text-[#AF52DE]',
      glow: 'shadow-[rgba(175,82,222,0.06)]',
      bg: 'bg-[rgba(175,82,222,0.05)]',
    },
    green: {
      border: 'border-[rgba(52,199,89,0.12)]',
      text: 'text-[#34C759]',
      glow: 'shadow-[rgba(52,199,89,0.06)]',
      bg: 'bg-[rgba(52,199,89,0.05)]',
    },
    orange: {
      border: 'border-[rgba(255,149,0,0.12)]',
      text: 'text-[#FF9500]',
      glow: 'shadow-[rgba(255,149,0,0.06)]',
      bg: 'bg-[rgba(255,149,0,0.05)]',
    },
    pink: {
      border: 'border-[rgba(255,45,85,0.12)]',
      text: 'text-[#FF2D55]',
      glow: 'shadow-[rgba(255,45,85,0.06)]',
      bg: 'bg-[rgba(255,45,85,0.05)]',
    },
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
      {stats.map((stat) => {
        const style = accentMap[stat.accent]
        return (
          <div
            key={stat.label}
            className={`glass-card rounded-2xl p-5 ${style.border} hover:shadow-lg ${style.glow}`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-[#86868b] font-mono uppercase tracking-wider">
                {stat.label}
              </span>
              <span className={`${style.text} ${style.bg} p-1.5 rounded-lg`}>
                {stat.icon}
              </span>
            </div>
            <p className={`text-3xl font-bold ${style.text} tracking-tight`}>
              {typeof stat.value === 'number' ? stat.value.toLocaleString() : stat.value}
            </p>
            <p className="text-xs text-[#a1a1a6] mt-1 font-mono">{stat.sub}</p>
          </div>
        )
      })}
    </div>
  )
}
