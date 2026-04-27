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
    <div className="bg-white rounded-lg shadow">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">快速路由测试</h2>
      </div>
      <div className="p-4 space-y-4">
        {/* Prompt Input */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            输入提示词
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="例如：帮我写一个快速排序算法"
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        {/* Strategy Buttons */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            路由策略
          </label>
          <div className="flex flex-wrap gap-2">
            {STRATEGIES.map((s) => (
              <button
                key={s.key}
                onClick={() => setStrategy(s.key)}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  strategy === s.key
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-50'
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
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
        >
          {isLoading ? '测试中...' : '测试路由'}
        </button>

        {/* Error */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Result */}
        {dryRunResult && !dryRunResult.error && (
          <div className="p-4 bg-gray-50 rounded-md space-y-2">
            <h3 className="text-sm font-semibold text-gray-900">路由结果</h3>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-500">任务类型:</span>{' '}
                <span className="font-medium text-gray-900">
                  {dryRunResult.task_type}
                </span>
              </div>
              <div>
                <span className="text-gray-500">置信度:</span>{' '}
                <span className="font-medium text-gray-900">
                  {dryRunResult.task_confidence}
                </span>
              </div>
              <div>
                <span className="text-gray-500">难度:</span>{' '}
                <span className="font-medium text-gray-900">
                  {dryRunResult.difficulty}
                </span>
              </div>
              <div>
                <span className="text-gray-500">选中模型:</span>{' '}
                <span className="font-medium text-blue-600">
                  {dryRunResult.selected_model}
                </span>
              </div>
              <div>
                <span className="text-gray-500">策略:</span>{' '}
                <span className="font-medium text-gray-900">
                  {dryRunResult.strategy}
                </span>
              </div>
              <div>
                <span className="text-gray-500">得分:</span>{' '}
                <span className="font-medium text-gray-900">
                  {dryRunResult.score}
                </span>
              </div>
            </div>
            <div className="pt-2 border-t border-gray-200">
              <span className="text-gray-500 text-sm">原因:</span>{' '}
              <span className="text-sm text-gray-700">
                {dryRunResult.reason}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
