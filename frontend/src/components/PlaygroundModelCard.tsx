import type { PlaygroundResult } from '../types'

interface PlaygroundModelCardProps {
  result: PlaygroundResult
}

export function PlaygroundModelCard({ result }: PlaygroundModelCardProps) {
  const isError = !!result.error

  return (
    <div className={`glass-card rounded-2xl overflow-hidden ${isError ? 'border-red-400/30' : ''}`}>
      {/* Header */}
      <div className="px-5 py-4 border-b border-[rgba(0,0,0,0.06)] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isError ? 'bg-[#FF3B30]' : 'bg-[#34C759]'}`} />
          <h3 className="text-sm font-semibold text-[#1d1d1f]">{result.model}</h3>
          <span className="text-xs text-[#86868b]">({result.provider})</span>
        </div>
      </div>

      {/* Content */}
      <div className="p-5 space-y-4">
        {isError ? (
          <div className="p-3 bg-[rgba(255,59,48,0.04)] border border-[rgba(255,59,48,0.12)] rounded-xl">
            <p className="text-sm text-[#FF3B30]">{result.error}</p>
          </div>
        ) : (
          <>
            <div className="max-h-96 overflow-y-auto">
              <pre className="text-sm text-[#1d1d1f] whitespace-pre-wrap font-sans leading-relaxed">
                {result.response}
              </pre>
            </div>

            {/* MetaBar */}
            <div className="flex flex-wrap gap-3 text-xs text-[#86868b]">
              <div className="flex items-center gap-1">
                <span>⏱️</span>
                <span>{result.latency_ms}ms</span>
              </div>
              <div className="flex items-center gap-1">
                <span>📝</span>
                <span>{result.prompt_tokens} prompt</span>
              </div>
              <div className="flex items-center gap-1">
                <span>✨</span>
                <span>{result.completion_tokens} completion</span>
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
              <div className="p-4 bg-[rgba(0,0,0,0.02)] border border-[rgba(0,0,0,0.06)] rounded-xl space-y-3">
                <h4 className="text-xs font-mono text-[#007AFF] uppercase tracking-wider">路由结果</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex justify-between py-1 border-b border-[rgba(0,0,0,0.06)]">
                    <span className="text-[#86868b]">任务类型</span>
                    <span className="font-medium text-[#1d1d1f]">{result.routing_info.task_type}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[rgba(0,0,0,0.06)]">
                    <span className="text-[#86868b]">策略</span>
                    <span className="font-medium text-[#1d1d1f]">{result.routing_info.strategy}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[rgba(0,0,0,0.06)]">
                    <span className="text-[#86868b]">得分</span>
                    <span className="font-medium text-[#1d1d1f]">{result.routing_info.score}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[rgba(0,0,0,0.06)]">
                    <span className="text-[#86868b]">选中模型</span>
                    <span className="font-medium text-[#007AFF]">{result.routing_info.selected_model}</span>
                  </div>
                </div>
                <div className="pt-2">
                  <span className="text-[#86868b] text-xs font-mono uppercase">原因</span>
                  <p className="text-sm text-[#1d1d1f] mt-1 leading-relaxed">{result.routing_info.reason}</p>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
