import { useEffect } from 'react'
import { Route, Switch, useLocation, Redirect } from 'wouter'
import { useDashboardStore } from './store/useDashboardStore'
import { useTranslation } from './i18n/I18nProvider'
import { Header } from './components/Header'
import { ModelOverrideBar } from './components/ModelOverrideBar'
import { DashboardPage } from './components/DashboardPage'
import { ModelsExplorer } from './components/ModelsExplorer'
import { LogsPanel } from './components/LogsPanel'
import { AnalyticsPage } from './components/AnalyticsPage'
import { AlertsPage } from './components/AlertsPage'
import { FormulaBuilder } from './components/FormulaBuilder'

function App() {
  const { fetchAll, error, clearError } = useDashboardStore()
  const [location, setLocation] = useLocation()
  const { t } = useTranslation()

  const tabs = [
    { key: 'dashboard', label: t('DASHBOARD'), path: '/dashboard', icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
      </svg>
    )},
    { key: 'models', label: t('MODELS'), path: '/models', icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    )},
    { key: 'formula', label: t('ROUTING'), path: '/formula', icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    )},
    { key: 'analytics', label: t('ANALYTICS'), path: '/analytics', icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
      </svg>
    )},
    { key: 'logs', label: t('LOGS'), path: '/logs', icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    )},
    { key: 'alerts', label: t('ALERTS'), path: '/alerts', icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
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
    <div className="min-h-screen bg-white flex flex-col">
      <Header />

      <main className="flex-1 max-w-[1280px] w-full mx-auto px-6 py-8 space-y-6">
        <ModelOverrideBar />

        {/* Error Alert */}
        {error && (
          <div className="tech-card rounded-xl p-4 flex items-center justify-between border border-[rgba(230,92,92,0.2)] bg-[#FDECEC]">
            <p className="text-sm text-[#E65C5C] font-medium">{error}</p>
            <button
              onClick={clearError}
              className="text-sm text-[#E65C5C] hover:opacity-70 transition-opacity font-medium"
            >
              {t('DISMISS')}
            </button>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setLocation(tab.path)}
              className={`px-4 py-2 rounded-full text-sm transition-all duration-200 flex items-center gap-2 font-medium ${
                location === tab.path
                  ? 'bg-[#001E2B] text-white'
                  : 'text-[#889397] hover:text-[#5C6C75] hover:bg-[#F4F7F6]'
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
          <Route path="/">
            <Redirect to="/dashboard" />
          </Route>
        </Switch>
      </main>

      {/* Footer */}
      <footer className="bg-[#001E2B] mt-auto">
        <div className="max-w-[1280px] mx-auto px-6 py-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 bg-[#00ED64] rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-[#001E2B]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <span className="text-sm font-semibold text-white">Smart Router</span>
          </div>
          <p className="text-sm text-white/70">
            Dashboard
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
