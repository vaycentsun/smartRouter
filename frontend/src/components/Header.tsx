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
          <div className="w-8 h-8 rounded-lg bg-[rgba(0,122,255,0.08)] border border-[rgba(0,122,255,0.15)] flex items-center justify-center">
            <svg className="w-5 h-5 text-[#007AFF]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-semibold text-[#1d1d1f] tracking-tight">
              Smart Router Dashboard
            </h1>
            <p className="text-xs text-[#86868b] mt-0.5 font-mono tracking-wider uppercase">
              智能模型路由网关监控面板
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="px-4 py-2 bg-[rgba(0,122,255,0.08)] text-[#007AFF] border border-[rgba(0,122,255,0.15)] rounded-xl hover:bg-[rgba(0,122,255,0.12)] hover:border-[rgba(0,122,255,0.25)] disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium backdrop-blur-sm"
          >
            {isLoading ? '刷新中...' : '刷新'}
          </button>
          <button
            onClick={handleStop}
            disabled={isLoading}
            className="px-4 py-2 bg-[rgba(255,59,48,0.06)] text-[#FF3B30] border border-[rgba(255,59,48,0.12)] rounded-xl hover:bg-[rgba(255,59,48,0.1)] hover:border-[rgba(255,59,48,0.2)] disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium backdrop-blur-sm"
          >
            停止服务
          </button>
        </div>
      </div>
    </header>
  )
}
