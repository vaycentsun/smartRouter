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
    <div className="glass-card rounded-xl">
      <div className="p-4 border-b border-cyan-400/10 flex items-center gap-2">
        <div className="w-1 h-5 bg-cyan-400 rounded-full" />
        <h2 className="text-base font-semibold text-slate-100 tracking-wide">快速路由测试</h2>
      </div>
      <div className="p-5 space-y-4">
        {/* Prompt Input */}
        <div>
          <label className="block text-xs font-mono text-slate-400 uppercase tracking-wider mb-2">
            输入提示词
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="例如：帮我写一个快速排序算法"
            rows={3}
            className="w-full px-3 py-2 rounded-lg text-sm text-slate-200 placeholder-slate-600 input-glow resize-none"
          />
        </div>

        {/* Strategy Buttons */}
        <div>
          <label className="block text-xs font-mono text-slate-400 uppercase tracking-wider mb-2">
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
                    : 'strategy-btn text-slate-400 hover:text-slate-200'
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
          className="w-full px-4 py-2.5 bg-cyan-500/10 text-cyan-300 border border-cyan-400/30 rounded-lg hover:bg-cyan-500/20 hover:border-cyan-400/50 hover:shadow-lg hover:shadow-cyan-400/10 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium backdrop-blur-sm"
        >
          {isLoading ? '测试中...' : '测试路由'}
        </button>

        {/* Error */}
        {error && (
          <div className="p-3 bg-red-500/5 border border-red-400/20 rounded-lg">
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        {/* Result */}
        {dryRunResult && !dryRunResult.error && (
          <div className="p-4 bg-slate-800/40 border border-cyan-400/10 rounded-lg space-y-3">
            <h3 className="text-xs font-mono text-cyan-400 uppercase tracking-wider">路由结果</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="flex justify-between py-1 border-b border-slate-700/30">
                <span className="text-slate-500">任务类型</span>
                <span className="font-medium text-slate-200">{dryRunResult.task_type}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-700/30">
                <span className="text-slate-500">置信度</span>
                <span className="font-medium text-slate-200">{dryRunResult.task_confidence}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-700/30">
                <span className="text-slate-500">难度</span>
                <span className="font-medium text-slate-200">{dryRunResult.difficulty}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-700/30">
                <span className="text-slate-500">选中模型</span>
                <span className="font-medium text-cyan-300">{dryRunResult.selected_model}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-700/30">
                <span className="text-slate-500">策略</span>
                <span className="font-medium text-slate-200">{dryRunResult.strategy}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-700/30">
                <span className="text-slate-500">得分</span>
                <span className="font-medium text-slate-200">{dryRunResult.score}</span>
              </div>
            </div>
            <div className="pt-2">
              <span className="text-slate-500 text-xs font-mono uppercase">原因</span>
              <p className="text-sm text-slate-300 mt-1 leading-relaxed">{dryRunResult.reason}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
