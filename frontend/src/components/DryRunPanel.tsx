import { useState } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import type { Strategy } from '../types'

const STRATEGIES: { key: Strategy; label: string }[] = [
  { key: 'auto', label: 'Auto' },
  { key: 'quality', label: 'Quality' },
  { key: 'cost', label: 'Cost' },
  { key: 'speed', label: 'Speed' },
  { key: 'balanced', label: 'Balanced' },
]

export function DryRunPanel() {
  const [prompt, setPrompt] = useState('')
  const [strategy, setStrategy] = useState<Strategy>('auto')
  const { runDryRun, dryRunResult, isLoading, error, clearError } =
    useDashboardStore()

  const handleSubmit = async () => {
    if (!prompt.trim()) return
    clearError()
    await runDryRun(prompt.trim(), strategy)
  }

  return (
    <div className="glass-card rounded-2xl">
      <div className="p-4 border-b border-[rgba(0,0,0,0.06)] flex items-center gap-2">
        <div className="w-1 h-5 bg-[#007AFF] rounded-full" />
        <h2 className="text-base font-semibold text-[#1d1d1f] tracking-wide">快速路由测试</h2>
      </div>
      <div className="p-5 space-y-4">
        {/* Prompt Input */}
        <div>
          <label className="block text-xs font-mono text-[#86868b] uppercase tracking-wider mb-2">
            输入提示词
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="例如：帮我写一个快速排序算法"
            rows={3}
            className="w-full px-3 py-2 rounded-xl text-sm input-glow resize-none"
          />
        </div>

        {/* Strategy Buttons */}
        <div>
          <label className="block text-xs font-mono text-[#86868b] uppercase tracking-wider mb-2">
            路由策略
          </label>
          <div className="flex flex-wrap gap-2">
            {STRATEGIES.map((s) => (
              <button
                key={s.key}
                onClick={() => setStrategy(s.key)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  strategy === s.key
                    ? 'strategy-btn-active'
                    : 'strategy-btn text-[#86868b] hover:text-[#1d1d1f]'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={isLoading || !prompt.trim()}
          className="w-full px-4 py-2.5 bg-[rgba(0,122,255,0.08)] text-[#007AFF] border border-[rgba(0,122,255,0.15)] rounded-xl hover:bg-[rgba(0,122,255,0.12)] hover:border-[rgba(0,122,255,0.25)] disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium backdrop-blur-sm"
        >
          {isLoading ? '测试中...' : '测试路由'}
        </button>

        {/* Error */}
        {error && (
          <div className="p-3 bg-[rgba(255,59,48,0.04)] border border-[rgba(255,59,48,0.12)] rounded-xl">
            <p className="text-sm text-[#FF3B30]">{error}</p>
          </div>
        )}

        {/* Result */}
        {dryRunResult && !dryRunResult.error && (
          <div className="p-4 bg-[rgba(0,0,0,0.02)] border border-[rgba(0,0,0,0.06)] rounded-xl space-y-3">
            <h3 className="text-xs font-mono text-[#007AFF] uppercase tracking-wider">路由结果</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="flex justify-between py-1 border-b border-[rgba(0,0,0,0.06)]">
                <span className="text-[#86868b]">任务类型</span>
                <span className="font-medium text-[#1d1d1f]">{dryRunResult.task_type}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[rgba(0,0,0,0.06)]">
                <span className="text-[#86868b]">置信度</span>
                <span className="font-medium text-[#1d1d1f]">{dryRunResult.task_confidence}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[rgba(0,0,0,0.06)]">
                <span className="text-[#86868b]">难度</span>
                <span className="font-medium text-[#1d1d1f]">{dryRunResult.difficulty}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[rgba(0,0,0,0.06)]">
                <span className="text-[#86868b]">选中模型</span>
                <span className="font-medium text-[#007AFF]">{dryRunResult.selected_model}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[rgba(0,0,0,0.06)]">
                <span className="text-[#86868b]">策略</span>
                <span className="font-medium text-[#1d1d1f]">{dryRunResult.strategy}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[rgba(0,0,0,0.06)]">
                <span className="text-[#86868b]">得分</span>
                <span className="font-medium text-[#1d1d1f]">{dryRunResult.score}</span>
              </div>
            </div>
            <div className="pt-2">
              <span className="text-[#86868b] text-xs font-mono uppercase">原因</span>
              <p className="text-sm text-[#1d1d1f] mt-1 leading-relaxed">{dryRunResult.reason}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
