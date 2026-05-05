import { useEffect } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import { PlaygroundInput } from './PlaygroundInput'
import { PlaygroundResult } from './PlaygroundResult'
import { PlaygroundCompare } from './PlaygroundCompare'

export function PlaygroundPage() {
  const {
    playgroundResults,
    playgroundError,
    clearPlaygroundError,
    runPlayground,
    fetchPlaygroundHistory,
  } = useDashboardStore()

  useEffect(() => {
    fetchPlaygroundHistory()
  }, [fetchPlaygroundHistory])

  const handleSubmit = (request: Parameters<typeof runPlayground>[0]) => {
    clearPlaygroundError()
    runPlayground(request)
  }

  const isCompare = playgroundResults.length > 1

  return (
    <div className="space-y-6">
      <PlaygroundInput onSubmit={handleSubmit} />

      {playgroundError && (
        <div className="glass-card rounded-2xl p-4 flex items-center justify-between border border-red-400/20">
          <p className="text-sm text-[#FF3B30]">{playgroundError}</p>
          <button
            onClick={clearPlaygroundError}
            className="text-sm text-[#FF3B30] hover:text-[#FF3B30]/70 transition-colors"
          >
            关闭
          </button>
        </div>
      )}

      {playgroundResults.length > 0 && !isCompare && (
        <PlaygroundResult result={playgroundResults[0]} />
      )}

      {playgroundResults.length > 0 && isCompare && (
        <PlaygroundCompare results={playgroundResults} />
      )}
    </div>
  )
}
