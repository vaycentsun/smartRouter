import { useEffect } from 'react'
import { useTranslation } from '../i18n/useTranslation'
import { useDashboardStore } from '../store/useDashboardStore'
import { PlaygroundInput } from './PlaygroundInput'
import { PlaygroundResult } from './PlaygroundResult'
import { PlaygroundCompare } from './PlaygroundCompare'

export function PlaygroundPage() {
  const { t } = useTranslation()
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
        <div className="tech-card rounded-sm p-4 flex items-center justify-between border border-[rgba(231,76,60,0.2)]">
          <p className="text-sm text-[#e74c3c]">{playgroundError}</p>
          <button
            onClick={clearPlaygroundError}
            className="text-sm text-[#e74c3c] hover:text-[#e74c3c]/70 transition-colors"
          >
            {t('DISMISS')}
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
