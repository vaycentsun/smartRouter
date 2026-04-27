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
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Smart Router Dashboard
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            智能模型路由网关监控面板
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
          >
            {isLoading ? '刷新中...' : '刷新'}
          </button>
          <button
            onClick={handleStop}
            disabled={isLoading}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
          >
            停止服务
          </button>
        </div>
      </div>
    </header>
  )
}
