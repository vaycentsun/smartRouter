import { useEffect } from 'react'
import { useDashboardStore } from './store/useDashboardStore'
import { Header } from './components/Header'
import { StatusCard } from './components/StatusCard'
import { StatsOverview } from './components/StatsOverview'
import { ProvidersTable } from './components/ProvidersTable'
import { ModelsTable } from './components/ModelsTable'
import { DryRunPanel } from './components/DryRunPanel'

function App() {
  const { fetchAll, error, clearError } = useDashboardStore()

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

        {/* Stats Overview */}
        <StatsOverview />

        {/* Status + DryRun Side by Side */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <StatusCard />
          </div>
          <div className="lg:col-span-2">
            <DryRunPanel />
          </div>
        </div>

        {/* Providers Table */}
        <ProvidersTable />

        {/* Models Table */}
        <ModelsTable />
      </main>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 text-center text-sm text-[#a1a1a6] relative z-10">
        Smart Router Dashboard
      </footer>
    </div>
  )
}

export default App
