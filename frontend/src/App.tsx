import { useEffect } from 'react'
import { useDashboardStore } from './store/useDashboardStore'
import { Header } from './components/Header'
import { StatusCard } from './components/StatusCard'
import { StatsOverview } from './components/StatsOverview'
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
    <div className="min-h-screen bg-gray-100">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Error Alert */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center justify-between">
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={clearError}
              className="text-sm text-red-500 hover:text-red-700"
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

        {/* Models Table */}
        <ModelsTable />
      </main>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 text-center text-sm text-gray-400">
        Smart Router Dashboard v0.1
      </footer>
    </div>
  )
}

export default App
