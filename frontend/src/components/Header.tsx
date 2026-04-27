import { useDashboardStore } from '../store/useDashboardStore'

export function Header() {
  const { fetchAll, stopService, isLoading, clearError } = useDashboardStore()

  const handleRefresh = () => {
    clearError()
    fetchAll()
  }

  const handleStop = async () => {
    if (confirm('确定要停止 Smart Router 服务吗？')) {
      await stopService()
    }
  }

  return (
    <header className="glass-header sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Logo 图标 */}
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-400/30 flex items-center justify-center">
            <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
              Smart Router Dashboard
            </h1>
            <p className="text-xs text-cyan-400/70 mt-0.5 font-mono tracking-wider uppercase">
              智能模型路由网关监控面板
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="btn-glow px-4 py-2 bg-cyan-500/10 text-cyan-300 border border-cyan-400/30 rounded-lg hover:bg-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium backdrop-blur-sm"
          >
            {isLoading ? '刷新中...' : '刷新'}
          </button>
          <button
            onClick={handleStop}
            disabled={isLoading}
            className="btn-glow px-4 py-2 bg-red-500/10 text-red-300 border border-red-400/30 rounded-lg hover:bg-red-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium backdrop-blur-sm"
          >
            停止服务
          </button>
        </div>
      </div>
    </header>
  )
}
