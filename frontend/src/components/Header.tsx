import { useDashboardStore } from '../store/useDashboardStore'
import { useTranslation } from '../i18n/useTranslation'

export function Header() {
  const { fetchAll, stopService, isLoading, clearError, status } = useDashboardStore()
  const { t, lang, setLang } = useTranslation()

  const handleRefresh = () => {
    clearError()
    fetchAll()
  }

  const handleStop = async () => {
    if (confirm(t('确定要停止 Smart Router 服务吗？'))) {
      await stopService()
    }
  }

  const handleStart = () => {
    alert(t('startHint'))
  }

  const isRunning = status?.running ?? false

  return (
    <header className="tech-header sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          {/* Logo */}
          <div className="w-8 h-8 border border-[#00d4aa]/30 flex items-center justify-center" style={{ borderRadius: '2px' }}>
            <svg className="w-5 h-5 text-[#00d4aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-[#e8e8ed] tracking-wide font-mono uppercase" style={{ letterSpacing: '0.08em' }}>
              Smart Router
            </h1>
            <p className="text-[10px] text-[#636366] font-mono tracking-widest mt-0.5">
              {t('Gateway Monitor')} {status?.version ? `v${status.version}` : ''}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Language Switcher */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setLang('zh')}
              className={`px-2 py-1 rounded-sm text-[10px] font-mono uppercase tracking-wider transition-all ${
                lang === 'zh'
                  ? 'bg-[rgba(0,212,170,0.1)] text-[#00d4aa] border border-[rgba(0,212,170,0.2)]'
                  : 'text-[#636366] hover:text-[#8e8e93]'
              }`}
            >
              中
            </button>
            <button
              onClick={() => setLang('en')}
              className={`px-2 py-1 rounded-sm text-[10px] font-mono uppercase tracking-wider transition-all ${
                lang === 'en'
                  ? 'bg-[rgba(0,212,170,0.1)] text-[#00d4aa] border border-[rgba(0,212,170,0.2)]'
                  : 'text-[#636366] hover:text-[#8e8e93]'
              }`}
            >
              EN
            </button>
          </div>
          <div className="w-px h-4 bg-[#1a1a2e]" />
          {/* Status Indicator */}
          <span className="flex items-center gap-2 text-xs font-mono text-[#00d4aa]">
            <span className={`status-indicator ${isRunning ? 'status-online' : 'status-offline'}`} />
            {isRunning ? t('ONLINE') : t('OFFLINE')}
          </span>
          <div className="w-px h-4 bg-[#1a1a2e]" />
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="tech-btn px-3 py-1.5 rounded-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? t('LOADING') : t('REFRESH')}
          </button>
          {isRunning ? (
            <button
              onClick={handleStop}
              disabled={isLoading}
              className="tech-btn tech-btn-danger px-3 py-1.5 rounded-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('STOP')}
            </button>
          ) : (
            <button
              onClick={handleStart}
              disabled={isLoading}
              className="tech-btn tech-btn-primary px-3 py-1.5 rounded-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('START')}
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
