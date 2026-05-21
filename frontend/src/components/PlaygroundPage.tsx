import { useEffect } from 'react'
import { useTranslation } from '../i18n/I18nProvider'
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
        <div className="card-base rounded-xl p-4 flex items-center justify-between border border-[#E65C5C]/20 bg-[#FDECEC]">
          <p className="text-sm text-[#E65C5C] font-medium">{playgroundError}</p>
          <button
            onClick={clearPlaygroundError}
            className="text-sm text-[#E65C5C] hover:opacity-70 transition-opacity font-medium"
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
