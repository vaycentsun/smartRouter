import { useTranslation } from '../i18n/useTranslation'
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
  const { t } = useTranslation()
  const { status } = useDashboardStore()

  if (!status) {
    return (
      <div className="tech-card rounded-sm p-6">
        <p className="text-[#636366] font-mono text-sm">{t('LOADING')}</p>
      </div>
    )
  }

  return (
    <div className="tech-card rounded-sm p-5">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-1 h-4 bg-[#00d4aa]" />
        <h2 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('Service Status')}</h2>
      </div>
      <div className="space-y-3">
        <div className="flex items-center gap-2 pb-3 border-b border-[#1a1a2e]">
          <span className={`status-indicator ${status.running ? 'status-online' : 'status-offline'}`} />
          <span className="text-sm text-[#e8e8ed] font-mono">
            {status.running ? t('RUNNING') : t('STOPPED')}
          </span>
        </div>
        {status.running && (
          <>
            <div className="flex items-center justify-between py-1 border-b border-[#1a1a2e]">
              <span className="text-[10px] text-[#636366] font-mono uppercase">{t('PID')}</span>
              <span className="text-sm text-[#00d4aa] font-mono">{status.pid}</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-[#1a1a2e]">
              <span className="text-[10px] text-[#636366] font-mono uppercase">{t('Uptime')}</span>
              <span className="text-sm text-[#e8e8ed] font-mono">
                {formatUptime(status.uptime_seconds)}
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-[#1a1a2e]">
              <span className="text-[10px] text-[#636366] font-mono uppercase">{t('Endpoint')}</span>
              <a
                href={status.service_url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-[#00d4aa] hover:opacity-70 transition-opacity font-mono"
              >
                {status.service_url}
              </a>
            </div>
          </>
        )}
        <div className="flex items-center justify-between py-1">
          <span className="text-[10px] text-[#636366] font-mono uppercase">{t('Version')}</span>
          <span className="text-sm text-[#e8e8ed] font-mono">{status.version}</span>
        </div>
      </div>
    </div>
  )
}
