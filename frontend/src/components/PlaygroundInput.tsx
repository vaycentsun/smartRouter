import { useState } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import type { PlaygroundRequest } from '../types'

interface PlaygroundInputProps {
  onSubmit: (request: PlaygroundRequest) => void
}

export function PlaygroundInput({ onSubmit }: PlaygroundInputProps) {
  const { models, isLoadingPlayground } = useDashboardStore()
  const [prompt, setPrompt] = useState('')
  const [mode, setMode] = useState<'single' | 'compare'>('single')
  const [selectedModels, setSelectedModels] = useState<string[]>([])

  const availableModels = models.filter((m) => m.available)

  const toggleModel = (modelName: string) => {
    setSelectedModels((prev) => {
      if (prev.includes(modelName)) {
        return prev.filter((m) => m !== modelName)
      }
      if (prev.length >= 3) return prev
      return [...prev, modelName]
    })
  }

  const handleSubmit = () => {
    if (!prompt.trim() || selectedModels.length === 0) return
    onSubmit({ mode, prompt: prompt.trim(), models: selectedModels })
  }

  return (
    <div className="glass-card rounded-2xl">
      <div className="p-4 border-b border-[rgba(0,0,0,0.06)] flex items-center gap-2">
        <div className="w-1 h-5 bg-[#007AFF] rounded-full" />
        <h2 className="text-base font-semibold text-[#1d1d1f] tracking-wide">Playground</h2>
      </div>
      <div className="p-5 space-y-4">
        {/* Mode Switch */}
        <div>
          <label className="block text-xs font-mono text-[#86868b] uppercase tracking-wider mb-2">
            模式
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => setMode('single')}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                mode === 'single'
                  ? 'strategy-btn-active'
                  : 'strategy-btn text-[#86868b] hover:text-[#1d1d1f]'
              }`}
            >
              单模型
            </button>
            <button
              onClick={() => setMode('compare')}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                mode === 'compare'
                  ? 'strategy-btn-active'
                  : 'strategy-btn text-[#86868b] hover:text-[#1d1d1f]'
              }`}
            >
              对比模式
            </button>
          </div>
        </div>

        {/* Model Selection */}
        <div>
          <label className="block text-xs font-mono text-[#86868b] uppercase tracking-wider mb-2">
            选择模型（最多3个）
          </label>
          <div className="flex flex-wrap gap-2">
            {availableModels.map((m) => (
              <button
                key={m.name}
                onClick={() => toggleModel(m.name)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all border ${
                  selectedModels.includes(m.name)
                    ? 'bg-[rgba(0,122,255,0.08)] text-[#007AFF] border-[rgba(0,122,255,0.15)]'
                    : 'text-[#86868b] border-transparent hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
                }`}
              >
                {m.name}
              </button>
            ))}
            {availableModels.length === 0 && (
              <span className="text-sm text-[#86868b]">暂无可用模型</span>
            )}
          </div>
        </div>

        {/* Prompt Input */}
        <div>
          <label className="block text-xs font-mono text-[#86868b] uppercase tracking-wider mb-2">
            输入提示词
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="例如：帮我写一个快速排序算法"
            rows={4}
            className="w-full px-3 py-2 rounded-xl text-sm input-glow resize-none"
          />
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={isLoadingPlayground || !prompt.trim() || selectedModels.length === 0}
          className="w-full px-4 py-2.5 bg-[rgba(0,122,255,0.08)] text-[#007AFF] border border-[rgba(0,122,255,0.15)] rounded-xl hover:bg-[rgba(0,122,255,0.12)] hover:border-[rgba(0,122,255,0.25)] disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium backdrop-blur-sm"
        >
          {isLoadingPlayground ? '请求中...' : '提交'}
        </button>
      </div>
    </div>
  )
}
