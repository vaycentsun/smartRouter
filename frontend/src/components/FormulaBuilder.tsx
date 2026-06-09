import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from '../i18n/useTranslation'
import { api } from '../api/client'
import { useDashboardStore } from '../store/useDashboardStore'
import { PlaygroundModelCard } from './PlaygroundModelCard'

interface FormulaTemplate {
  id: string
  name: string
  description: string
  weights: Record<string, number>
}

const FORMULA_TEMPLATES: FormulaTemplate[] = [
  {
    id: 'quality_first',
    name: 'QUALITY FIRST',
    description: 'qualityDesc',
    weights: { quality: 0.9, cost: 0.1 },
  },
  {
    id: 'cost_first',
    name: 'COST FIRST',
    description: 'costDesc',
    weights: { quality: 0.1, cost: 0.9 },
  },
  {
    id: 'balanced',
    name: 'BALANCED',
    description: 'balancedDesc',
    weights: { quality: 0.5, cost: 0.5 },
  },
]

const DIMENSIONS = [
  { key: 'quality', name: 'QUALITY', description: 'qualityDesc2' },
  { key: 'cost', name: 'COST', description: 'costDesc2' },
]

const DEFAULT_WEIGHTS: Record<string, number> = {
  quality: 0.5,
  cost: 0.5,
}

export function FormulaBuilder() {
  const { t } = useTranslation()
  const {
    models,
    runPlayground,
    playgroundResults,
    isLoadingPlayground,
    playgroundError,
    clearPlaygroundError,
  } = useDashboardStore()

  const [weights, setWeights] = useState<Record<string, number>>({ ...DEFAULT_WEIGHTS })
  const [originalWeights, setOriginalWeights] = useState<Record<string, number>>({ ...DEFAULT_WEIGHTS })
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [previewModels, setPreviewModels] = useState<Array<{ name: string; score: number }>>([])
  const [testPrompt, setTestPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const hasChanges = useMemo(
    () => DIMENSIONS.some((d) => weights[d.key] !== originalWeights[d.key]),
    [weights, originalWeights]
  )

  // Playground 嵌入状态
  const [showPlayground, setShowPlayground] = useState(false)
  const [pgPrompt, setPgPrompt] = useState('')
  const [pgModels, setPgModels] = useState<string[]>([])

  // 加载当前公式
  useEffect(() => {
    api.getFormula()
      .then((data) => {
        const loaded = { ...DEFAULT_WEIGHTS, ...data.weights }
        setWeights(loaded)
        setOriginalWeights(loaded)
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err)
        setMessage({ type: 'error', text: `${t('LOAD FAILED')}: ${msg}` })
      })
  }, [t])

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
      setMessage({ type: 'error', text: t('ENTER TEST PROMPT') })
      return
    }
    setLoading(true)
    setMessage(null)
    try {
      const data = await api.previewFormula({ weights, prompt: testPrompt })
      setPreviewModels(data.models)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setMessage({ type: 'error', text: `${t('PREVIEW FAILED')}: ${msg}` })
    } finally {
      setLoading(false)
    }
  }, [weights, testPrompt, t])

  const handleSave = useCallback(async () => {
    setSaving(true)
    setMessage(null)
    try {
      const result = await api.updateFormula({ weights })
      if (result.success) {
        setOriginalWeights({ ...weights })
        setMessage({ type: 'success', text: t('FORMULA SAVED') })
      } else {
        setMessage({ type: 'error', text: `${t('SAVE FAILED')}: ${result.errors?.join(', ') || t('UNKNOWN')}` })
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setMessage({ type: 'error', text: `${t('SAVE FAILED')}: ${msg}` })
    } finally {
      setSaving(false)
    }
  }, [weights, t])

  const handleReset = useCallback(() => {
    setWeights({ ...originalWeights })
    setSelectedTemplate(null)
    setPreviewModels([])
    setMessage(null)
  }, [originalWeights])

  const openPlayground = useCallback((modelName: string) => {
    setPgPrompt(testPrompt)
    setPgModels([modelName])
    setShowPlayground(true)
    clearPlaygroundError()
  }, [testPrompt, clearPlaygroundError])

  const togglePgModel = useCallback((modelName: string) => {
    setPgModels((prev) => {
      if (prev.includes(modelName)) {
        return prev.filter((m) => m !== modelName)
      }
      if (prev.length >= 3) return prev
      return [...prev, modelName]
    })
  }, [])

  const handlePgRun = useCallback(() => {
    if (!pgPrompt.trim() || pgModels.length === 0) return
    clearPlaygroundError()
    runPlayground({ mode: pgModels.length > 1 ? 'compare' : 'single', prompt: pgPrompt.trim(), models: pgModels })
  }, [pgPrompt, pgModels, runPlayground, clearPlaygroundError])

  const availableModels = models.filter((m) => m.available)

  const formulaText = DIMENSIONS
    .filter((d) => weights[d.key] > 0)
    .map((d) => `${d.key} * ${weights[d.key].toFixed(2)}`)
    .join(' + ') || t('NOT CONFIGURED')

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="tech-card rounded-sm p-6">
        <h2 className="text-xl font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider mb-2">{t('Routing Formula')}</h2>
        <p className="text-sm text-[#636366] font-mono">
          {t('formulaDesc')}
        </p>
      </div>

      {/* 消息提示 */}
      {message && (
        <div
          className={`tech-card rounded-sm p-4 flex items-center justify-between border ${
            message.type === 'success'
              ? 'border-[rgba(0,212,170,0.2)]'
              : 'border-[rgba(231,76,60,0.2)]'
          }`}
        >
          <p className={`text-sm font-mono ${message.type === 'success' ? 'text-[#00d4aa]' : 'text-[#e74c3c]'}`}>
            {message.text}
          </p>
          <button
            onClick={() => setMessage(null)}
            className="text-sm text-[#636366] hover:text-[#e8e8ed] transition-colors font-mono uppercase"
          >
            {t('DISMISS')}
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：模板 + 滑块 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 预设模板 */}
          <div className="tech-card rounded-sm p-6">
            <h3 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider mb-4">{t('Templates')}</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {FORMULA_TEMPLATES.map((template) => (
                <button
                  key={template.id}
                  onClick={() => handleTemplateSelect(template)}
                  className={`p-3 rounded-sm text-left transition-all duration-200 border ${
                    selectedTemplate === template.id
                      ? 'bg-[rgba(0,212,170,0.04)] border-[rgba(0,212,170,0.2)] text-[#00d4aa]'
                      : 'bg-transparent border-[#1a1a2e] hover:border-[#2a2a3e] text-[#e8e8ed]'
                  }`}
                >
                  <div className="text-sm font-medium font-mono">{t(template.name)}</div>
                  <div className="text-xs text-[#636366] mt-1 font-mono">{t(template.description)}</div>
                </button>
              ))}
            </div>
          </div>

          {/* 能力权重滑块 */}
          <div className="tech-card rounded-sm p-6">
            <h3 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider mb-4">{t('Weights')}</h3>
            <div className="space-y-5">
              {DIMENSIONS.map((dim) => (
                <div key={dim.key}>
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="text-sm font-medium text-[#e8e8ed] font-mono">{t(dim.name)}</span>
                      <span className="text-xs text-[#636366] ml-2 font-mono">{t(dim.description)}</span>
                    </div>
                    <span className="text-sm font-mono text-[#00d4aa]">
                      {(weights[dim.key] * 100).toFixed(0)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={Math.round(weights[dim.key] * 100)}
                    onChange={(e) => handleWeightChange(dim.key, parseInt(e.target.value) / 100)}
                    className="w-full h-1 bg-[#1a1a2e] rounded-sm appearance-none cursor-pointer accent-[#00d4aa]"
                  />
                </div>
              ))}
            </div>

            {/* 公式文本 */}
            <div className="mt-6 p-4 bg-[#0a0a0f] border border-[#1a1a2e] rounded-sm">
              <div className="text-xs text-[#636366] mb-1 font-mono uppercase tracking-widest">{t('FORMULA')}</div>
              <div className="text-sm font-mono text-[#e8e8ed]">{formulaText}</div>
            </div>

            {/* 操作按钮 */}
            <div className="mt-6 flex gap-3">
              <button
                onClick={handleSave}
                disabled={saving || !hasChanges}
                className={`px-6 py-2.5 rounded-sm text-sm font-medium transition-all duration-200 font-mono uppercase tracking-wider ${
                  hasChanges
                    ? 'tech-btn tech-btn-primary'
                    : 'tech-btn opacity-50 cursor-not-allowed'
                }`}
              >
                {saving ? t('SAVING') : t('SAVE')}
              </button>
              <button
                onClick={handleReset}
                disabled={!hasChanges}
                className={`px-6 py-2.5 rounded-sm text-sm font-medium transition-all duration-200 font-mono uppercase tracking-wider ${
                  hasChanges
                    ? 'tech-btn'
                    : 'tech-btn opacity-50 cursor-not-allowed'
                }`}
              >
                {t('RESET')}
              </button>
            </div>
          </div>
        </div>

        {/* 右侧：预览 */}
        <div className="space-y-6">
          <div className="tech-card rounded-sm p-6">
            <h3 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider mb-4">{t('Preview')}</h3>
            <div className="space-y-3">
              <textarea
                value={testPrompt}
                onChange={(e) => setTestPrompt(e.target.value)}
                placeholder={t('Enter test prompt...')}
                rows={3}
                className="w-full px-3 py-2 rounded-sm text-sm tech-input resize-none"
              />
              <button
                onClick={handlePreview}
                disabled={loading}
                className="tech-btn tech-btn-primary w-full px-4 py-2.5 rounded-sm disabled:opacity-50"
              >
                {loading ? t('CALCULATING') : t('PREVIEW')}
              </button>
            </div>

            {/* 预览结果 */}
            {previewModels.length > 0 && (
              <div className="mt-4 space-y-2">
                <div className="text-xs text-[#636366] mb-2 font-mono uppercase tracking-widest">{t('RANKING')}</div>
                {previewModels.map((model, index) => (
                  <div
                    key={model.name}
                    className={`flex items-center justify-between p-3 rounded-sm border ${
                      index === 0
                        ? 'bg-[rgba(0,212,170,0.04)] border-[rgba(0,212,170,0.15)]'
                        : 'bg-[#0a0a0f] border-[#1a1a2e]'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-5 h-5 rounded-sm flex items-center justify-center text-xs font-mono ${
                          index === 0
                            ? 'bg-[#00d4aa] text-[#0a0a0f]'
                            : 'bg-[#1a1a2e] text-[#636366]'
                        }`}
                      >
                        {index + 1}
                      </span>
                      <span className="text-sm font-medium text-[#e8e8ed] font-mono">{model.name}</span>
                      {index === 0 && (
                        <span className="text-xs text-[#00d4aa] font-mono">{t('BEST')}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono text-[#00d4aa]">{model.score.toFixed(2)}</span>
                      <button
                        onClick={() => openPlayground(model.name)}
                        className="tech-btn px-2 py-1 text-[10px] rounded-sm"
                      >
                        {t('TEST')}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Playground 验证区域 */}
      {showPlayground && (
        <div className="tech-card rounded-sm p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('Playground')}</h3>
            <button
              onClick={() => setShowPlayground(false)}
              className="text-sm text-[#636366] hover:text-[#e8e8ed] transition-colors font-mono uppercase"
            >
              {t('CLOSE')}
            </button>
          </div>

          {/* Prompt */}
          <div>
            <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-2">
              {t('PROMPT')}
            </label>
            <textarea
              value={pgPrompt}
              onChange={(e) => setPgPrompt(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 rounded-sm text-sm tech-input resize-none"
            />
          </div>

          {/* Model Selection */}
          <div>
            <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-2">
              {t('MODELS (MAX 3)')}
            </label>
            <div className="flex flex-wrap gap-2">
              {availableModels.map((m) => (
                <button
                  key={m.name}
                  onClick={() => togglePgModel(m.name)}
                  className={`px-3 py-1.5 rounded-sm text-sm font-medium transition-all border font-mono text-xs ${
                    pgModels.includes(m.name)
                      ? 'bg-[rgba(0,212,170,0.08)] text-[#00d4aa] border-[rgba(0,212,170,0.2)]'
                      : 'text-[#636366] border-[#1a1a2e] hover:text-[#8e8e93]'
                  }`}
                >
                  {m.name}
                </button>
              ))}
              {availableModels.length === 0 && (
                <span className="text-sm text-[#636366] font-mono">{t('NO MODELS')}</span>
              )}
            </div>
          </div>

          {/* Run */}
          <button
            onClick={handlePgRun}
            disabled={isLoadingPlayground || !pgPrompt.trim() || pgModels.length === 0}
            className="tech-btn tech-btn-primary w-full px-4 py-2.5 rounded-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoadingPlayground ? t('RUNNING') : t('RUN TEST')}
          </button>

          {/* Error */}
          {playgroundError && (
            <div className="p-3 bg-[rgba(231,76,60,0.04)] border border-[rgba(231,76,60,0.12)] rounded-sm">
              <p className="text-sm text-[#e74c3c] font-mono">{playgroundError}</p>
            </div>
          )}

          {/* Results */}
          {playgroundResults.length > 0 && (
            <div className="space-y-4 pt-2">
              {playgroundResults.map((result) => (
                <PlaygroundModelCard key={result.model} result={result} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
