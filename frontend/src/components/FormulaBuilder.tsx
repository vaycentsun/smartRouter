import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

interface FormulaTemplate {
  id: string
  name: string
  description: string
  weights: Record<string, number>
}

const FORMULA_TEMPLATES: FormulaTemplate[] = [
  {
    id: 'quality_first',
    name: '质量优先',
    description: '优先选择高质量模型',
    weights: { quality: 0.9, cost: 0.1, reasoning: 0, creative: 0, context: 0 },
  },
  {
    id: 'cost_first',
    name: '成本优先',
    description: '优先选择便宜模型',
    weights: { quality: 0.1, cost: 0.9, reasoning: 0, creative: 0, context: 0 },
  },
  {
    id: 'balanced',
    name: '均衡',
    description: '质量与成本兼顾',
    weights: { quality: 0.5, cost: 0.5, reasoning: 0, creative: 0, context: 0 },
  },
  {
    id: 'reasoning_first',
    name: '推理优先',
    description: '优先选择推理能力强的模型',
    weights: { quality: 0.3, cost: 0.1, reasoning: 0.6, creative: 0, context: 0 },
  },
]

const DIMENSIONS = [
  { key: 'quality', name: '质量', description: '代码质量、推理能力' },
  { key: 'cost', name: '成本', description: '成本效率（越高越便宜）' },
  { key: 'reasoning', name: '推理', description: '数学、逻辑、代码推理' },
  { key: 'creative', name: '创意', description: '写作、广告、头脑风暴' },
  { key: 'context', name: '上下文', description: '上下文窗口处理能力' },
]

const DEFAULT_WEIGHTS: Record<string, number> = {
  quality: 0.5,
  cost: 0.5,
  reasoning: 0,
  creative: 0,
  context: 0,
}

export function FormulaBuilder() {
  const [weights, setWeights] = useState<Record<string, number>>({ ...DEFAULT_WEIGHTS })
  const [originalWeights, setOriginalWeights] = useState<Record<string, number>>({ ...DEFAULT_WEIGHTS })
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [previewModels, setPreviewModels] = useState<Array<{ name: string; score: number }>>([])
  const [testPrompt, setTestPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [hasChanges, setHasChanges] = useState(false)

  // 加载当前公式
  useEffect(() => {
    api.getFormula()
      .then((data) => {
        const loaded = { ...DEFAULT_WEIGHTS, ...data.weights }
        setWeights(loaded)
        setOriginalWeights(loaded)
      })
      .catch((err) => {
        setMessage({ type: 'error', text: `加载公式失败: ${err.message}` })
      })
  }, [])

  // 检测变化
  useEffect(() => {
    const changed = DIMENSIONS.some((d) => weights[d.key] !== originalWeights[d.key])
    setHasChanges(changed)
  }, [weights, originalWeights])

  const handleWeightChange = useCallback((key: string, value: number) => {
    setWeights((prev) => ({ ...prev, [key]: value }))
    setSelectedTemplate(null)
  }, [])

  const handleTemplateSelect = useCallback((template: FormulaTemplate) => {
    setWeights({ ...template.weights })
    setSelectedTemplate(template.id)
  }, [])

  const handlePreview = useCallback(async () => {
    if (!testPrompt.trim()) {
      setMessage({ type: 'error', text: '请输入测试 prompt' })
      return
    }
    setLoading(true)
    setMessage(null)
    try {
      const data = await api.previewFormula({ weights, prompt: testPrompt })
      setPreviewModels(data.models)
    } catch (err: any) {
      setMessage({ type: 'error', text: `预览失败: ${err.message}` })
    } finally {
      setLoading(false)
    }
  }, [weights, testPrompt])

  const handleSave = useCallback(async () => {
    setSaving(true)
    setMessage(null)
    try {
      const result = await api.updateFormula({ weights })
      if (result.success) {
        setOriginalWeights({ ...weights })
        setMessage({ type: 'success', text: '公式已保存并应用' })
      } else {
        setMessage({ type: 'error', text: `保存失败: ${result.errors?.join(', ') || '未知错误'}` })
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: `保存失败: ${err.message}` })
    } finally {
      setSaving(false)
    }
  }, [weights])

  const handleReset = useCallback(() => {
    setWeights({ ...originalWeights })
    setSelectedTemplate(null)
    setPreviewModels([])
    setMessage(null)
  }, [originalWeights])

  // 构建公式文本
  const formulaText = DIMENSIONS
    .filter((d) => weights[d.key] > 0)
    .map((d) => `${d.key} * ${weights[d.key].toFixed(2)}`)
    .join(' + ') || '未配置'

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="glass-card rounded-2xl p-6">
        <h2 className="text-xl font-semibold text-[#1d1d1f] mb-2">策略公式构建器</h2>
        <p className="text-sm text-[#86868b]">
          配置全局评分公式，所有任务类型将统一使用该公式选择最佳模型。
        </p>
      </div>

      {/* 消息提示 */}
      {message && (
        <div
          className={`glass-card rounded-2xl p-4 flex items-center justify-between border ${
            message.type === 'success'
              ? 'border-green-400/20 bg-green-50/50'
              : 'border-red-400/20 bg-red-50/50'
          }`}
        >
          <p className={`text-sm ${message.type === 'success' ? 'text-green-600' : 'text-[#FF3B30]'}`}>
            {message.text}
          </p>
          <button
            onClick={() => setMessage(null)}
            className="text-sm text-[#86868b] hover:text-[#1d1d1f] transition-colors"
          >
            关闭
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：模板 + 滑块 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 预设模板 */}
          <div className="glass-card rounded-2xl p-6">
            <h3 className="text-lg font-medium text-[#1d1d1f] mb-4">预设模板</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {FORMULA_TEMPLATES.map((template) => (
                <button
                  key={template.id}
                  onClick={() => handleTemplateSelect(template)}
                  className={`p-3 rounded-xl text-left transition-all duration-200 border ${
                    selectedTemplate === template.id
                      ? 'bg-[rgba(0,122,255,0.08)] border-[#007AFF]/30 text-[#007AFF]'
                      : 'bg-white/50 border-transparent hover:bg-white/80 hover:border-[#d2d2d7]'
                  }`}
                >
                  <div className="text-sm font-medium">{template.name}</div>
                  <div className="text-xs text-[#86868b] mt-1">{template.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* 能力权重滑块 */}
          <div className="glass-card rounded-2xl p-6">
            <h3 className="text-lg font-medium text-[#1d1d1f] mb-4">能力权重</h3>
            <div className="space-y-5">
              {DIMENSIONS.map((dim) => (
                <div key={dim.key}>
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="text-sm font-medium text-[#1d1d1f]">{dim.name}</span>
                      <span className="text-xs text-[#86868b] ml-2">{dim.description}</span>
                    </div>
                    <span className="text-sm font-mono text-[#007AFF]">
                      {(weights[dim.key] * 100).toFixed(0)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={Math.round(weights[dim.key] * 100)}
                    onChange={(e) => handleWeightChange(dim.key, parseInt(e.target.value) / 100)}
                    className="w-full h-2 bg-[#e5e5ea] rounded-full appearance-none cursor-pointer accent-[#007AFF]"
                  />
                </div>
              ))}
            </div>

            {/* 公式文本 */}
            <div className="mt-6 p-4 bg-[#f5f5f7] rounded-xl">
              <div className="text-xs text-[#86868b] mb-1">当前公式</div>
              <div className="text-sm font-mono text-[#1d1d1f]">{formulaText}</div>
            </div>

            {/* 操作按钮 */}
            <div className="mt-6 flex gap-3">
              <button
                onClick={handleSave}
                disabled={saving || !hasChanges}
                className={`px-6 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                  hasChanges
                    ? 'bg-[#007AFF] text-white hover:bg-[#0051D5] shadow-sm'
                    : 'bg-[#e5e5ea] text-[#86868b] cursor-not-allowed'
                }`}
              >
                {saving ? '保存中...' : '保存并应用'}
              </button>
              <button
                onClick={handleReset}
                disabled={!hasChanges}
                className={`px-6 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                  hasChanges
                    ? 'bg-white border border-[#d2d2d7] text-[#1d1d1f] hover:bg-[#f5f5f7]'
                    : 'bg-[#e5e5ea] text-[#86868b] cursor-not-allowed'
                }`}
              >
                重置
              </button>
            </div>
          </div>
        </div>

        {/* 右侧：预览 */}
        <div className="space-y-6">
          <div className="glass-card rounded-2xl p-6">
            <h3 className="text-lg font-medium text-[#1d1d1f] mb-4">实时预览</h3>
            <div className="space-y-3">
              <textarea
                value={testPrompt}
                onChange={(e) => setTestPrompt(e.target.value)}
                placeholder="输入测试 prompt..."
                rows={3}
                className="w-full px-4 py-3 rounded-xl border border-[#d2d2d7] bg-white/50 text-sm text-[#1d1d1f] placeholder-[#a1a1a6] focus:outline-none focus:ring-2 focus:ring-[#007AFF]/20 focus:border-[#007AFF] resize-none"
              />
              <button
                onClick={handlePreview}
                disabled={loading}
                className="w-full px-4 py-2.5 rounded-xl text-sm font-medium bg-[#007AFF] text-white hover:bg-[#0051D5] transition-all duration-200 shadow-sm disabled:opacity-50"
              >
                {loading ? '计算中...' : '预览得分'}
              </button>
            </div>

            {/* 预览结果 */}
            {previewModels.length > 0 && (
              <div className="mt-4 space-y-2">
                <div className="text-xs text-[#86868b] mb-2">模型得分排名</div>
                {previewModels.map((model, index) => (
                  <div
                    key={model.name}
                    className={`flex items-center justify-between p-3 rounded-xl ${
                      index === 0
                        ? 'bg-[rgba(0,122,255,0.08)] border border-[#007AFF]/20'
                        : 'bg-white/50'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-medium ${
                          index === 0
                            ? 'bg-[#007AFF] text-white'
                            : 'bg-[#e5e5ea] text-[#86868b]'
                        }`}
                      >
                        {index + 1}
                      </span>
                      <span className="text-sm font-medium text-[#1d1d1f]">{model.name}</span>
                      {index === 0 && (
                        <span className="text-xs text-[#007AFF] font-medium">★ 最佳</span>
                      )}
                    </div>
                    <span className="text-sm font-mono text-[#007AFF]">{model.score.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
