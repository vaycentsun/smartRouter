import { useState } from 'react'
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

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-[rgba(0,0,0,0.06)] flex items-center gap-4">
        <div className="w-1 h-5 bg-[#007AFF] rounded-full" />
        <h2 className="text-base font-semibold text-[#1d1d1f] tracking-wide">最近请求路由记录</h2>
      </div>

      {/* Content */}
      {requests.length === 0 ? (
        <div className="p-8 text-center">
          <p className="text-sm text-[#86868b]">暂无请求记录</p>
        </div>
      ) : (
        <div className="divide-y divide-[rgba(0,0,0,0.06)]">
          {requests.map((req) => (
            <div key={req.request_id}>
              <div
                data-testid="request-row"
                onClick={() => toggleExpand(req.request_id)}
                className={`flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-[rgba(0,0,0,0.02)] transition-colors ${
                  req.did_fallback ? 'border-l-[3px] border-orange-400' : ''
                }`}
              >
                {/* Timestamp */}
                <div className="w-20 shrink-0">
                  <span className="text-xs font-mono text-[#86868b]">
                    {formatTime(req.timestamp)}
                  </span>
                </div>

                {/* Model Chain */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1 text-sm">
                    <span className="text-[#1d1d1f]">{req.original_model}</span>
                    <span className="text-[#86868b]">→</span>
                    <span className="text-[#1d1d1f]">{req.selected_model}</span>
                    {req.did_fallback && req.actual_model && (
                      <>
                        <span className="text-orange-400">→</span>
                        <span className="text-[#1d1d1f]">{req.actual_model}</span>
                      </>
                    )}
                    {!req.did_fallback && (
                      <span className="text-[#34C759] ml-1">✓</span>
                    )}
                  </div>
                </div>

                {/* Status + Tokens */}
                <div className="flex items-center gap-3 shrink-0">
                  <span
                    data-testid="status-code"
                    className={`text-xs font-mono px-2 py-0.5 rounded ${
                      req.status_code >= 200 && req.status_code < 300
                        ? 'bg-[rgba(52,199,89,0.1)] text-[#34C759]'
                        : 'bg-[rgba(255,59,48,0.1)] text-[#FF3B30]'
                    }`}
                  >
                    {req.status_code}
                  </span>
                  <span data-testid="total-tokens" className="text-xs font-mono text-[#86868b]">{req.total_tokens}</span>
                </div>
              </div>

              {/* Detail Card */}
              {expandedId === req.request_id && (
                <div className="px-4 py-3 bg-[rgba(0,0,0,0.02)] border-t border-[rgba(0,0,0,0.06)]">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-xs text-[#86868b] block">任务类型</span>
                      <span className="text-[#1d1d1f]">{req.task_type ?? '-'}</span>
                    </div>
                    <div>
                      <span className="text-xs text-[#86868b] block">难度</span>
                      <span className="text-[#1d1d1f]">{req.difficulty ?? '-'}</span>
                    </div>
                    <div>
                      <span className="text-xs text-[#86868b] block">策略</span>
                      <span className="text-[#1d1d1f]">{req.strategy ?? '-'}</span>
                    </div>
                    <div>
                      <span className="text-xs text-[#86868b] block">attempted_fallbacks</span>
                      <span className="text-[#1d1d1f]">{req.attempted_fallbacks ?? 0}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-xs text-[#86868b] block">fallback 链</span>
                      <div data-testid="fallback-chain" className="flex flex-wrap gap-1 mt-1">
                        {req.fallback_chain.map((model, idx) => (
                          <span
                            key={idx}
                            className="text-xs bg-[rgba(0,0,0,0.05)] px-2 py-0.5 rounded text-[#1d1d1f]"
                          >
                            {model}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="col-span-2">
                      <span className="text-xs text-[#86868b] block">request_id</span>
                      <span className="text-[#1d1d1f] font-mono text-xs">{req.request_id}</span>
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
