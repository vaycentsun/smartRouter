import { useState } from 'react'
import { useTranslation } from '../i18n/I18nProvider'
import type { RequestRoutingRecord } from '../types'

interface RecentRequestsPanelProps {
  requests: RequestRoutingRecord[]
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

export function RecentRequestsPanel({ requests = [] }: RecentRequestsPanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const { t } = useTranslation()

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="card-base rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-[#E8EDEB] flex items-center gap-3">
        <div className="w-1 h-4 bg-[#00A34D]" />
        <h2 className="text-sm font-semibold text-[#001E2B]">{t('Recent Requests')}</h2>
      </div>

      {/* Content */}
      {requests.length === 0 ? (
        <div className="p-8 text-center">
          <p className="text-sm text-[#889397]">{t('NO REQUESTS')}</p>
        </div>
      ) : (
        <div className="divide-y divide-[#E8EDEB]">
          {requests.map((req) => (
            <div key={req.request_id}>
              <div
                data-testid="request-row"
                onClick={() => toggleExpand(req.request_id)}
                className={`flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-[#F9FBFA] transition-colors ${
                  req.did_fallback ? 'border-l-[3px] border-[#F08B1E]' : ''
                }`}
              >
                {/* Timestamp */}
                <div className="w-20 shrink-0">
                  <span className="text-xs text-[#889397]">
                    {formatTime(req.timestamp)}
                  </span>
                </div>

                {/* Model Chain */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1 text-sm">
                    <span className="text-[#001E2B] text-xs">{req.original_model}</span>
                    <span className="text-[#889397] text-xs">→</span>
                    <span className="text-[#001E2B] text-xs">{req.selected_model}</span>
                    {req.did_fallback && req.actual_model && (
                      <>
                        <span className="text-[#F08B1E] text-xs">→</span>
                        <span className="text-[#001E2B] text-xs">{req.actual_model}</span>
                      </>
                    )}
                    {!req.did_fallback && (
                      <span className="text-[#00A34D] ml-1 text-xs">✓</span>
                    )}
                  </div>
                </div>

                {/* Status + Retry Badge + Tokens */}
                <div className="flex items-center gap-3 shrink-0">
                  {req.retry_history && req.retry_history.length > 0 && (
                    <span
                      data-testid="retry-badge"
                      className="text-xs px-2 py-0.5 rounded-lg bg-[rgba(240,139,30,0.1)] text-[#F08B1E] border border-[rgba(240,139,30,0.15)]"
                      title={`重试 ${req.retry_history.length} 次`}
                    >
                      ↻{req.retry_history.length}
                    </span>
                  )}
                  <span
                    data-testid="status-code"
                    className={`text-xs px-2 py-0.5 rounded-lg border ${
                      req.status_code >= 200 && req.status_code < 300
                        ? 'bg-[rgba(0,163,77,0.08)] text-[#00A34D] border-[rgba(0,163,77,0.15)]'
                        : 'bg-[rgba(230,92,92,0.08)] text-[#E65C5C] border-[rgba(230,92,92,0.15)]'
                    }`}
                  >
                    {req.status_code}
                  </span>
                  <span data-testid="total-tokens" className="text-xs text-[#889397]">{req.total_tokens}</span>
                </div>
              </div>

              {/* Detail Card */}
              {expandedId === req.request_id && (
                <div className="px-4 py-3 bg-[#F9FBFA] border-t border-[#E8EDEB]">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-[10px] text-[#889397] block">{t('TASK TYPE')}</span>
                      <span className="text-[#001E2B] text-xs">{req.task_type ?? '-'}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#889397] block">{t('DIFFICULTY')}</span>
                      <span className="text-[#001E2B] text-xs">{req.difficulty ?? '-'}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#889397] block">{t('STRATEGY')}</span>
                      <span className="text-[#001E2B] text-xs">{req.strategy ?? '-'}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#889397] block">{t('ATTEMPTS')}</span>
                      <span className="text-[#001E2B] text-xs">{req.attempted_fallbacks ?? 0}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#889397] block">{t('INPUT TOKENS')}</span>
                      <span className="text-[#001E2B] text-xs">{req.prompt_tokens}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#889397] block">{t('OUTPUT TOKENS')}</span>
                      <span className="text-[#001E2B] text-xs">{req.completion_tokens}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#889397] block">{t('REASONING TOKENS')}</span>
                      <span className="text-[#001E2B] text-xs">{req.reasoning_tokens}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#889397] block">{t('CACHE HITS')}</span>
                      <span className="text-[#001E2B] text-xs">{req.cached_tokens}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-[10px] text-[#889397] block">{t('FALLBACK CHAIN')}</span>
                      <div data-testid="fallback-chain" className="flex flex-wrap gap-1 mt-1">
                        {req.fallback_chain.map((model, idx) => (
                          <span
                            key={idx}
                            className="text-xs bg-white border border-[#E8EDEB] px-2 py-0.5 rounded-lg text-[#001E2B] font-mono"
                          >
                            {model}
                          </span>
                        ))}
                      </div>
                    </div>
                    {req.retry_history && req.retry_history.length > 0 && (
                      <div className="col-span-2">
                        <span className="text-[10px] text-[#889397] block">{t('RETRY HISTORY')}</span>
                        <div data-testid="retry-history" className="mt-1 space-y-1">
                          {req.retry_history.map((retry, idx) => (
                            <div
                              key={idx}
                              className="flex items-center gap-2 text-xs bg-white border border-[#E8EDEB] px-2 py-1 rounded-lg"
                            >
                              <span className="text-[#889397] font-mono">#{idx + 1}</span>
                              <span className="text-[#001E2B] font-medium font-mono">{retry.model}</span>
                              <span
                                className={`px-1.5 py-0.5 rounded-lg font-mono border ${
                                  retry.status_code === 0
                                    ? 'bg-[rgba(230,92,92,0.08)] text-[#E65C5C] border-[rgba(230,92,92,0.15)]'
                                    : 'bg-[rgba(240,139,30,0.08)] text-[#F08B1E] border-[rgba(240,139,30,0.15)]'
                                }`}
                              >
                                {retry.status_code === 0 ? t('ERR') : retry.status_code}
                              </span>
                              {retry.error && (
                                <span className="text-[#E65C5C] truncate font-mono text-xs">{retry.error}</span>
                              )}
                              <span className="text-[#889397] ml-auto shrink-0 font-mono text-xs">
                                {new Date(retry.timestamp).toLocaleTimeString('zh-CN', { hour12: false })}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="col-span-2">
                      <span className="text-[10px] text-[#889397] block">{t('REQUEST ID')}</span>
                      <span className="text-[#001E2B] font-mono text-xs">{req.request_id}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
