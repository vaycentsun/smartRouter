import { useEffect } from 'react'
import { Route, Switch, useLocation, Redirect } from 'wouter'
import { useDashboardStore } from './store/useDashboardStore'
import { useTranslation } from './i18n/useTranslation'
import { Header } from './components/Header'
import { ModelOverrideBar } from './components/ModelOverrideBar'
import { DashboardPage } from './components/DashboardPage'
import { ModelsExplorer } from './components/ModelsExplorer'
import { LogsPanel } from './components/LogsPanel'
import { AnalyticsPage } from './components/AnalyticsPage'
import { AlertsPage } from './components/AlertsPage'
import { FormulaBuilder } from './components/FormulaBuilder'
import { ModelMappingTab } from './components/ModelMappingTab'

function App() {
  const { fetchAll, error, clearError } = useDashboardStore()
  const [location, setLocation] = useLocation()
  const { t } = useTranslation()

  const tabs = [
    { key: 'dashboard', label: t('DASHBOARD'), path: '/dashboard', icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
      </svg>
    )},
    { key: 'models', label: t('MODELS'), path: '/models', icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    )},
    { key: 'formula', label: t('ROUTING'), path: '/formula', icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    )},
    { key: 'analytics', label: t('ANALYTICS'), path: '/analytics', icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
      </svg>
    )},
    { key: 'logs', label: t('LOGS'), path: '/logs', icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    )},
    { key: 'alerts', label: t('ALERTS'), path: '/alerts', icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    )},
    { key: 'mappings', label: t('MAPPINGS'), path: '/mappings', icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
      </svg>
    )},
  ]

  // Auto refresh every 5 seconds on all pages
  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 5000)
    return () => clearInterval(interval)
  }, [fetchAll])

  return (
    <div className="min-h-screen bg-[#0a0a0f] bg-tech-grid relative">
      {/* 顶部装饰线 */}
      <div className="top-accent-line fixed top-0 left-0 right-0 z-50" />

      <Header />

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6 relative z-10">
        <ModelOverrideBar />

        {/* Error Alert */}
        {error && (
          <div className="tech-card rounded-sm p-4 flex items-center justify-between border border-[rgba(231,76,60,0.2)]">
            <p className="text-sm text-[#e74c3c] font-mono">{error}</p>
            <button
              onClick={clearError}
              className="text-sm text-[#e74c3c] hover:opacity-70 transition-opacity font-mono uppercase"
            >
              {t('DISMISS')}
            </button>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex gap-1 p-1 border border-[#1a1a2e] rounded-sm bg-[#111118]">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setLocation(tab.path)}
              className={`px-4 py-2 rounded-sm transition-all duration-200 flex items-center gap-2 font-mono uppercase tracking-wider text-[10px] ${
                location === tab.path
                  ? 'tech-tab-active'
                  : 'tech-tab'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Page Content */}
        <Switch>
          <Route path="/dashboard" component={DashboardPage} />
          <Route path="/models" component={ModelsExplorer} />
          <Route path="/logs" component={LogsPanel} />
          <Route path="/analytics" component={AnalyticsPage} />
          <Route path="/alerts" component={AlertsPage} />
          <Route path="/formula" component={FormulaBuilder} />
          <Route path="/mappings" component={ModelMappingTab} />
          <Route path="/">
            <Redirect to="/dashboard" />
          </Route>
        </Switch>
      </main>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-6 py-4 text-center text-xs text-[#636366] font-mono relative z-10">
        <span className="text-[#00d4aa]">SMART ROUTER</span> DASHBOARD
      </footer>
    </div>
  )
}

export default App
