import { useDashboardStore } from '../store/useDashboardStore'
import { useTranslation } from '../i18n/I18nProvider'

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
    <header className="bg-[#001E2B] sticky top-0 z-40 border-b border-[#3D4F58]">
      <div className="max-w-[1280px] mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-4">
          {/* Logo */}
          <div className="w-8 h-8 bg-[#00ED64] rounded-full flex items-center justify-center">
            <svg className="w-5 h-5 text-[#001E2B]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white tracking-tight">
              Smart Router
            </h1>
            <p className="text-xs text-white/70 mt-0">
              {t('Gateway Monitor')} {status?.version ? `v${status.version}` : ''}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Language Switcher */}
          <div className="flex items-center gap-1 bg-[#3D4F58]/50 rounded-full p-0.5">
            <button
              onClick={() => setLang('zh')}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                lang === 'zh'
                  ? 'bg-[#00ED64] text-[#001E2B]'
                  : 'text-white/70 hover:text-white'
              }`}
            >
              中
            </button>
            <button
              onClick={() => setLang('en')}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                lang === 'en'
                  ? 'bg-[#00ED64] text-[#001E2B]'
                  : 'text-white/70 hover:text-white'
              }`}
            >
              EN
            </button>
          </div>
          <div className="w-px h-4 bg-[#3D4F58]" />
          {/* Status Indicator */}
          <span className="flex items-center gap-2 text-sm font-medium text-white/90">
            <span className={`status-indicator ${isRunning ? 'status-online' : 'status-offline'}`} />
            {isRunning ? t('ONLINE') : t('OFFLINE')}
          </span>
          <div className="w-px h-4 bg-[#3D4F58]" />
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="btn-secondary-on-dark px-4 py-1.5 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? t('LOADING') : t('REFRESH')}
          </button>
          {isRunning ? (
            <button
              onClick={handleStop}
              disabled={isLoading}
              className="px-4 py-1.5 rounded-full text-xs font-semibold bg-[#FDECEC] text-[#E65C5C] border border-[#E65C5C]/20 transition-all hover:bg-[#E65C5C] hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('STOP')}
            </button>
          ) : (
            <button
              onClick={handleStart}
              disabled={isLoading}
              className="btn-on-dark px-4 py-1.5 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('START')}
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
