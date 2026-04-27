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
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-500">加载中...</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">服务状态</h2>
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <span
            className={`inline-block w-3 h-3 rounded-full ${
              status.running ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          <span className="text-gray-700">
            {status.running ? '运行中' : '已停止'}
          </span>
        </div>
        {status.running && (
          <>
            <p className="text-sm text-gray-600">
              PID: <span className="font-mono">{status.pid}</span>
            </p>
            <p className="text-sm text-gray-600">
              已运行:{' '}
              <span className="font-mono">
                {formatUptime(status.uptime_seconds)}
              </span>
            </p>
            <p className="text-sm text-gray-600">
              服务地址:{' '}
              <a
                href={status.service_url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                {status.service_url}
              </a>
            </p>
          </>
        )}
        <p className="text-sm text-gray-600">
          版本: <span className="font-mono">{status.version}</span>
        </p>
      </div>
    </div>
  )
}
