import { useTranslation } from '../i18n/I18nProvider'
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
      <div className="card-base p-6">
        <p className="text-[#889397] text-sm">{t('LOADING')}</p>
      </div>
    )
  }

  return (
    <div className="card-base p-5">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-1 h-5 bg-[#00A34D] rounded-full" />
        <h2 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider">{t('Service Status')}</h2>
      </div>
      <div className="space-y-3">
        <div className="flex items-center gap-2 pb-3 border-b border-[#E8EDEB]">
          <span className={`status-indicator ${status.running ? 'status-online' : 'status-offline'}`} />
          <span className="text-sm text-[#001E2B] font-medium">
            {status.running ? t('RUNNING') : t('STOPPED')}
          </span>
        </div>
        {status.running && (
          <>
            <div className="flex items-center justify-between py-1 border-b border-[#E8EDEB]">
              <span className="text-xs text-[#889397] uppercase font-medium">{t('PID')}</span>
              <span className="text-sm text-[#00A34D] mono-num">{status.pid}</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-[#E8EDEB]">
              <span className="text-xs text-[#889397] uppercase font-medium">{t('Uptime')}</span>
              <span className="text-sm text-[#001E2B] mono-num">
                {formatUptime(status.uptime_seconds)}
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-[#E8EDEB]">
              <span className="text-xs text-[#889397] uppercase font-medium">{t('Endpoint')}</span>
              <a
                href={status.service_url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-[#00A34D] hover:opacity-70 transition-opacity"
              >
                {status.service_url}
              </a>
            </div>
          </>
        )}
        <div className="flex items-center justify-between py-1">
          <span className="text-xs text-[#889397] uppercase font-medium">{t('Version')}</span>
          <span className="text-sm text-[#001E2B] mono-num">{status.version}</span>
        </div>
      </div>
    </div>
  )
}
