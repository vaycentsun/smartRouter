import type { PlaygroundResult } from '../types'
import { useTranslation } from '../i18n/useTranslation'

interface PlaygroundModelCardProps {
  result: PlaygroundResult
}

export function PlaygroundModelCard({ result }: PlaygroundModelCardProps) {
  const { t } = useTranslation()
  const isError = !!result.error

  return (
    <div className={`tech-card rounded-sm overflow-hidden ${isError ? 'border-[rgba(231,76,60,0.3)]' : ''}`}>
      {/* Header */}
      <div className="px-5 py-4 border-b border-[#1a1a2e] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-sm ${isError ? 'bg-[#e74c3c]' : 'bg-[#00d4aa]'}`} />
          <h3 className="text-sm font-semibold text-[#e8e8ed]">{result.model}</h3>
          <span className="text-xs text-[#636366]">({result.provider})</span>
        </div>
      </div>

      {/* Content */}
      <div className="p-5 space-y-4">
        {isError ? (
          <div className="p-3 bg-[rgba(231,76,60,0.04)] border border-[rgba(231,76,60,0.12)] rounded-sm">
            <p className="text-sm text-[#e74c3c]">{result.error}</p>
          </div>
        ) : (
          <>
            <div className="max-h-96 overflow-y-auto">
              <pre className="text-sm text-[#e8e8ed] whitespace-pre-wrap font-mono leading-relaxed">
                {result.response}
              </pre>
            </div>

            {/* MetaBar */}
            <div className="flex flex-wrap gap-3 text-xs text-[#636366]">
              <div className="flex items-center gap-1">
                <span className="text-[10px] font-mono uppercase tracking-wider">{t('LAT')}</span>
                <span>{result.latency_ms}{t('ms')}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-[10px] font-mono uppercase tracking-wider">{t('Prompt Tokens')}</span>
                <span>{result.prompt_tokens}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-[10px] font-mono uppercase tracking-wider">{t('Completion Tokens')}</span>
                <span>{result.completion_tokens}</span>
              </div>
              {result.estimated_cost !== null && (
                <div className="flex items-center gap-1">
                  <span className="text-[10px] font-mono uppercase tracking-wider">{t('EST COST')}</span>
                  <span>${result.estimated_cost.toFixed(6)}</span>
                </div>
              )}
            </div>

            {/* Routing Info */}
            {result.routing_info && (
              <div className="p-4 bg-[#111118] border border-[#1a1a2e] rounded-sm space-y-3">
                <h4 className="text-xs font-mono text-[#00d4aa] uppercase tracking-wider">{t('Routing Info')}</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex justify-between py-1 border-b border-[#1a1a2e]">
                    <span className="text-[#636366]">{t('Task Type')}</span>
                    <span className="font-medium text-[#e8e8ed]">{result.routing_info.task_type}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#1a1a2e]">
                    <span className="text-[#636366]">{t('STRATEGY')}</span>
                    <span className="font-medium text-[#e8e8ed]">{result.routing_info.strategy}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#1a1a2e]">
                    <span className="text-[#636366]">{t('SCORE')}</span>
                    <span className="font-medium text-[#e8e8ed]">{result.routing_info.score}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#1a1a2e]">
                    <span className="text-[#636366]">{t('Selected Model')}</span>
                    <span className="font-medium text-[#00d4aa]">{result.routing_info.selected_model}</span>
                  </div>
                </div>
                <div className="pt-2">
                  <span className="text-[#636366] text-xs font-mono uppercase">{t('REASON')}</span>
                  <p className="text-sm text-[#e8e8ed] mt-1 leading-relaxed">{result.routing_info.reason}</p>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
