import { useDashboardStore } from '../store/useDashboardStore'

function formatUptime(seconds: number | null): string {
  if (seconds === null) return '-'
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  if (hours > 0) {
    return `${hours}h ${mins}m`
  }
  return `${mins}m`
}

export function StatusCard() {
  const { status } = useDashboardStore()

  if (!status) {
    return (
      <div className="glass-card rounded-xl p-6">
        <p className="text-slate-500">加载中...</p>
      </div>
    )
  }

  return (
    <div className="glass-card rounded-xl p-6">
      <div className="flex items-center gap-2 mb-5">
        <div className="w-1 h-5 bg-cyan-400 rounded-full" />
        <h2 className="text-base font-semibold text-slate-100 tracking-wide">服务状态</h2>
      </div>
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <span
            className={`inline-block w-3 h-3 rounded-full ${
              status.running
                ? 'bg-emerald-400 pulse-glow'
                : 'bg-red-400 pulse-glow-red'
            }`}
          />
          <span className="text-slate-300 text-sm">
            {status.running ? '运行中' : '已停止'}
          </span>
        </div>
        {status.running && (
          <>
            <div className="flex items-center justify-between py-2 border-b border-slate-700/30">
              <span className="text-xs text-slate-500 font-mono uppercase">PID</span>
              <span className="text-sm text-cyan-300 font-mono">{status.pid}</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-slate-700/30">
              <span className="text-xs text-slate-500 font-mono uppercase">已运行</span>
              <span className="text-sm text-slate-300 font-mono">
                {formatUptime(status.uptime_seconds)}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-slate-700/30">
              <span className="text-xs text-slate-500 font-mono uppercase">服务地址</span>
              <a
                href={status.service_url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors font-mono"
              >
                {status.service_url}
              </a>
            </div>
          </>
        )}
        <div className="flex items-center justify-between py-2">
          <span className="text-xs text-slate-500 font-mono uppercase">版本</span>
          <span className="text-sm text-slate-300 font-mono">{status.version}</span>
        </div>
      </div>
    </div>
  )
}
