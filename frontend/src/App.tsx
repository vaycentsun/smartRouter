import { useEffect, useState } from 'react'
import { useDashboardStore } from './store/useDashboardStore'
import { Header } from './components/Header'
import { ModelOverrideBar } from './components/ModelOverrideBar'
import { DashboardPage } from './components/DashboardPage'
import { ModelsExplorer } from './components/ModelsExplorer'
import { LogsPanel } from './components/LogsPanel'
import { AnalyticsPage } from './components/AnalyticsPage'
import { PlaygroundPage } from './components/PlaygroundPage'
import { AlertsPage } from './components/AlertsPage'

function App() {
  const { fetchAll, error, clearError } = useDashboardStore()
  const [activeTab, setActiveTab] = useState<'dashboard' | 'models' | 'logs' | 'analytics' | 'playground' | 'alerts'>('dashboard')

  // Auto refresh every 5 seconds
  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 5000)
    return () => clearInterval(interval)
  }, [fetchAll])

  return (
    <div className="min-h-screen bg-[#f5f5f7] bg-tech-grid bg-tech-gradient relative">
      {/* 顶部极细分隔阴影 */}
      <div className="fixed top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-black/5 to-transparent pointer-events-none" />

      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 relative z-10">
        <ModelOverrideBar />
        {/* Error Alert */}
        {error && (
          <div className="glass-card rounded-2xl p-4 flex items-center justify-between border border-red-400/20">
            <p className="text-sm text-[#FF3B30]">{error}</p>
            <button
              onClick={clearError}
              className="text-sm text-[#FF3B30] hover:text-[#FF3B30]/70 transition-colors"
            >
              关闭
            </button>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="glass-card rounded-2xl p-1.5 inline-flex gap-1">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-5 py-2 rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
              activeTab === 'dashboard'
                ? 'bg-[rgba(0,122,255,0.08)] text-[#007AFF] shadow-sm'
                : 'text-[#86868b] hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
            仪表盘
          </button>
          <button
            onClick={() => setActiveTab('models')}
            className={`px-5 py-2 rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
              activeTab === 'models'
                ? 'bg-[rgba(0,122,255,0.08)] text-[#007AFF] shadow-sm'
                : 'text-[#86868b] hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
            </svg>
            模型清单
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-5 py-2 rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
              activeTab === 'logs'
                ? 'bg-[rgba(0,122,255,0.08)] text-[#007AFF] shadow-sm'
                : 'text-[#86868b] hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            日志
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`px-5 py-2 rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
              activeTab === 'analytics'
                ? 'bg-[rgba(0,122,255,0.08)] text-[#007AFF] shadow-sm'
                : 'text-[#86868b] hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
            </svg>
            数据分析
          </button>
          <button
            onClick={() => setActiveTab('playground')}
            className={`px-5 py-2 rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
              activeTab === 'playground'
                ? 'bg-[rgba(0,122,255,0.08)] text-[#007AFF] shadow-sm'
                : 'text-[#86868b] hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Playground
          </button>
          <button
            onClick={() => setActiveTab('alerts')}
            className={`px-5 py-2 rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
              activeTab === 'alerts'
                ? 'bg-[rgba(0,122,255,0.08)] text-[#007AFF] shadow-sm'
                : 'text-[#86868b] hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            告警
          </button>
        </div>

        {/* Page Content */}
        {activeTab === 'dashboard' ? <DashboardPage /> :
         activeTab === 'models' ? <ModelsExplorer /> :
         activeTab === 'logs' ? <LogsPanel /> :
         activeTab === 'analytics' ? <AnalyticsPage /> :
         activeTab === 'playground' ? <PlaygroundPage /> :
         <AlertsPage />}
      </main>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 text-center text-sm text-[#a1a1a6] relative z-10">
        Smart Router Dashboard
      </footer>
    </div>
  )
}

export default App
