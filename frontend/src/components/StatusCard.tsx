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
      <div className="glass-card rounded-2xl p-6">
        <p className="text-[#a1a1a6]">加载中...</p>
      </div>
    )
  }

  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-center gap-2 mb-5">
        <div className="w-1 h-5 bg-[#007AFF] rounded-full" />
        <h2 className="text-base font-semibold text-[#1d1d1f] tracking-wide">服务状态</h2>
      </div>
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <span
            className={`inline-block w-3 h-3 rounded-full ${
              status.running
                ? 'bg-[#34C759] pulse-glow'
                : 'bg-[#FF3B30] pulse-glow-red'
            }`}
          />
          <span className="text-[#1d1d1f] text-sm">
            {status.running ? '运行中' : '已停止'}
          </span>
        </div>
        {status.running && (
          <>
            <div className="flex items-center justify-between py-2 border-b border-[rgba(0,0,0,0.06)]">
              <span className="text-xs text-[#86868b] font-mono uppercase">PID</span>
              <span className="text-sm text-[#007AFF] font-mono">{status.pid}</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-[rgba(0,0,0,0.06)]">
              <span className="text-xs text-[#86868b] font-mono uppercase">已运行</span>
              <span className="text-sm text-[#1d1d1f] font-mono">
                {formatUptime(status.uptime_seconds)}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-[rgba(0,0,0,0.06)]">
              <span className="text-xs text-[#86868b] font-mono uppercase">服务地址</span>
              <a
                href={status.service_url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-[#007AFF] hover:text-[#007AFF]/70 transition-colors font-mono"
              >
                {status.service_url}
              </a>
            </div>
          </>
        )}
        <div className="flex items-center justify-between py-2">
          <span className="text-xs text-[#86868b] font-mono uppercase">版本</span>
          <span className="text-sm text-[#1d1d1f] font-mono">{status.version}</span>
        </div>
      </div>
    </div>
  )
}
