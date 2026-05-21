import type { PlaygroundResult } from '../types'
import { useTranslation } from '../i18n/I18nProvider'

interface PlaygroundModelCardProps {
  result: PlaygroundResult
}

export function PlaygroundModelCard({ result }: PlaygroundModelCardProps) {
  const { t } = useTranslation()
  const isError = !!result.error

  return (
    <div className={`card-base overflow-hidden ${isError ? 'border-[#E65C5C]/30' : ''}`}>
      {/* Header */}
      <div className="px-5 py-4 border-b border-[#E8EDEB] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isError ? 'bg-[#E65C5C]' : 'bg-[#00A34D]'}`} />
          <h3 className="text-sm font-semibold text-[#001E2B]">{result.model}</h3>
          <span className="text-xs text-[#889397]">({result.provider})</span>
        </div>
      </div>

      {/* Content */}
      <div className="p-5 space-y-4">
        {isError ? (
          <div className="p-3 bg-[#FDECEC] border border-[#E65C5C]/20 rounded-lg">
            <p className="text-sm text-[#E65C5C] font-medium">{result.error}</p>
          </div>
        ) : (
          <>
            <div className="max-h-96 overflow-y-auto">
              <pre className="text-sm text-[#001E2B] whitespace-pre-wrap font-mono leading-relaxed">
                {result.response}
              </pre>
            </div>

            {/* MetaBar */}
            <div className="flex flex-wrap gap-3 text-xs text-[#889397]">
              <div className="flex items-center gap-1">
                <span>⏱️</span>
                <span>{result.latency_ms}{t('ms')}</span>
              </div>
              <div className="flex items-center gap-1">
                <span>📝</span>
                <span>{result.prompt_tokens} {t('Prompt Tokens')}</span>
              </div>
              <div className="flex items-center gap-1">
                <span>✨</span>
                <span>{result.completion_tokens} {t('Completion Tokens')}</span>
              </div>
              {result.estimated_cost !== null && (
                <div className="flex items-center gap-1">
                  <span>💰</span>
                  <span>${result.estimated_cost.toFixed(6)}</span>
                </div>
              )}
            </div>

            {/* Routing Info */}
            {result.routing_info && (
              <div className="p-4 bg-[#F9FBFA] border border-[#E8EDEB] rounded-xl space-y-3">
                <h4 className="text-xs font-semibold text-[#00A34D] uppercase tracking-wider">{t('Routing Info')}</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex justify-between py-1 border-b border-[#E8EDEB]">
                    <span className="text-[#889397]">{t('Task Type')}</span>
                    <span className="font-medium text-[#001E2B]">{result.routing_info.task_type}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#E8EDEB]">
                    <span className="text-[#889397]">{t('STRATEGY')}</span>
                    <span className="font-medium text-[#001E2B]">{result.routing_info.strategy}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#E8EDEB]">
                    <span className="text-[#889397]">{t('SCORE')}</span>
                    <span className="font-medium text-[#001E2B]">{result.routing_info.score}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#E8EDEB]">
                    <span className="text-[#889397]">{t('Selected Model')}</span>
                    <span className="font-medium text-[#00A34D]">{result.routing_info.selected_model}</span>
                  </div>
                </div>
                <div className="pt-2">
                  <span className="text-[#889397] text-xs font-medium uppercase">{t('REASON')}</span>
                  <p className="text-sm text-[#001E2B] mt-1 leading-relaxed">{result.routing_info.reason}</p>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
