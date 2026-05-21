import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from '../i18n/I18nProvider'
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
  const [hasChanges, setHasChanges] = useState(false)

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
      .catch((err) => {
        setMessage({ type: 'error', text: `${t('LOAD FAILED')}: ${err.message}` })
      })
  }, [t])

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
      setMessage({ type: 'error', text: t('ENTER TEST PROMPT') })
      return
    }
    setLoading(true)
    setMessage(null)
    try {
      const data = await api.previewFormula({ weights, prompt: testPrompt })
      setPreviewModels(data.models)
    } catch (err: any) {
      setMessage({ type: 'error', text: `${t('PREVIEW FAILED')}: ${err.message}` })
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
    } catch (err: any) {
      setMessage({ type: 'error', text: `${t('SAVE FAILED')}: ${err.message}` })
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
      <div className="card-base p-6">
        <h2 className="text-xl font-semibold text-[#001E2B] mb-2">{t('Routing Formula')}</h2>
        <p className="text-sm text-[#889397]">
          {t('formulaDesc')}
        </p>
      </div>

      {/* 消息提示 */}
      {message && (
        <div
          className={`card-base rounded-xl p-4 flex items-center justify-between border ${
            message.type === 'success'
              ? 'border-[#00A34D]/20 bg-[#E3FCEF]'
              : 'border-[#E65C5C]/20 bg-[#FDECEC]'
          }`}
        >
          <p className={`text-sm font-medium ${message.type === 'success' ? 'text-[#00A34D]' : 'text-[#E65C5C]'}`}>
            {message.text}
          </p>
          <button
            onClick={() => setMessage(null)}
            className="text-sm text-[#889397] hover:text-[#001E2B] transition-colors font-medium uppercase"
          >
            {t('DISMISS')}
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：模板 + 滑块 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 预设模板 */}
          <div className="card-base p-6">
            <h3 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider mb-4">{t('Templates')}</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {FORMULA_TEMPLATES.map((template) => (
                <button
                  key={template.id}
                  onClick={() => handleTemplateSelect(template)}
                  className={`p-4 rounded-xl text-left transition-all duration-200 border ${
                    selectedTemplate === template.id
                      ? 'bg-[#E3FCEF] border-[#00A34D]/30 text-[#00A34D]'
                      : 'bg-white border-[#E8EDEB] hover:border-[#C1C7C6] text-[#001E2B]'
                  }`}
                >
                  <div className="text-sm font-semibold">{t(template.name)}</div>
                  <div className="text-xs text-[#889397] mt-1">{t(template.description)}</div>
                </button>
              ))}
            </div>
          </div>

          {/* 能力权重滑块 */}
          <div className="card-base p-6">
            <h3 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider mb-4">{t('Weights')}</h3>
            <div className="space-y-5">
              {DIMENSIONS.map((dim) => (
                <div key={dim.key}>
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="text-sm font-semibold text-[#001E2B]">{t(dim.name)}</span>
                      <span className="text-xs text-[#889397] ml-2">{t(dim.description)}</span>
                    </div>
                    <span className="text-sm font-semibold text-[#00A34D] mono-num">
                      {(weights[dim.key] * 100).toFixed(0)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={Math.round(weights[dim.key] * 100)}
                    onChange={(e) => handleWeightChange(dim.key, parseInt(e.target.value) / 100)}
                    className="w-full h-2 bg-[#E8EDEB] rounded-full appearance-none cursor-pointer accent-[#00A34D]"
                  />
                </div>
              ))}
            </div>

            {/* 公式文本 */}
            <div className="mt-6 p-4 bg-[#F9FBFA] border border-[#E8EDEB] rounded-xl">
              <div className="text-xs text-[#889397] mb-1 font-medium uppercase tracking-wider">{t('FORMULA')}</div>
              <div className="text-sm font-mono text-[#001E2B]">{formulaText}</div>
            </div>

            {/* 操作按钮 */}
            <div className="mt-6 flex gap-3">
              <button
                onClick={handleSave}
                disabled={saving || !hasChanges}
                className={`px-6 py-2.5 rounded-full text-sm font-semibold transition-all duration-200 ${
                  hasChanges
                    ? 'btn-primary'
                    : 'bg-[#E8EDEB] text-[#889397] cursor-not-allowed'
                }`}
              >
                {saving ? t('SAVING') : t('SAVE')}
              </button>
              <button
                onClick={handleReset}
                disabled={!hasChanges}
                className={`px-6 py-2.5 rounded-full text-sm font-semibold transition-all duration-200 border ${
                  hasChanges
                    ? 'border-[#C1C7C6] text-[#001E2B] hover:bg-[#F4F7F6]'
                    : 'border-[#E8EDEB] text-[#889397] cursor-not-allowed'
                }`}
              >
                {t('RESET')}
              </button>
            </div>
          </div>
        </div>

        {/* 右侧：预览 */}
        <div className="space-y-6">
          <div className="card-base p-6">
            <h3 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider mb-4">{t('Preview')}</h3>
            <div className="space-y-3">
              <textarea
                value={testPrompt}
                onChange={(e) => setTestPrompt(e.target.value)}
                placeholder={t('Enter test prompt...')}
                rows={3}
                className="w-full px-3 py-2 rounded-lg text-sm tech-input resize-none"
              />
              <button
                onClick={handlePreview}
                disabled={loading}
                className="btn-primary w-full px-4 py-2.5 disabled:opacity-50"
              >
                {loading ? t('CALCULATING') : t('PREVIEW')}
              </button>
            </div>

            {/* 预览结果 */}
            {previewModels.length > 0 && (
              <div className="mt-4 space-y-2">
                <div className="text-xs text-[#889397] mb-2 font-medium uppercase tracking-wider">{t('RANKING')}</div>
                {previewModels.map((model, index) => (
                  <div
                    key={model.name}
                    className={`flex items-center justify-between p-3 rounded-xl border ${
                      index === 0
                        ? 'bg-[#E3FCEF] border-[#00A34D]/20'
                        : 'bg-[#F9FBFA] border-[#E8EDEB]'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-semibold ${
                          index === 0
                            ? 'bg-[#00A34D] text-white'
                            : 'bg-[#E8EDEB] text-[#889397]'
                        }`}
                      >
                        {index + 1}
                      </span>
                      <span className="text-sm font-semibold text-[#001E2B]">{model.name}</span>
                      {index === 0 && (
                        <span className="text-xs text-[#00A34D] font-semibold">{t('BEST')}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-[#00A34D] mono-num">{model.score.toFixed(2)}</span>
                      <button
                        onClick={() => openPlayground(model.name)}
                        className="px-3 py-1 rounded-full text-xs font-semibold border border-[#E8EDEB] text-[#5C6C75] hover:bg-[#F4F7F6] hover:text-[#001E2B] transition-all"
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
        <div className="card-base p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider">{t('Playground')}</h3>
            <button
              onClick={() => setShowPlayground(false)}
              className="text-sm text-[#889397] hover:text-[#001E2B] transition-colors font-medium uppercase"
            >
              {t('CLOSE')}
            </button>
          </div>

          {/* Prompt */}
          <div>
            <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-2">
              {t('PROMPT')}
            </label>
            <textarea
              value={pgPrompt}
              onChange={(e) => setPgPrompt(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 rounded-lg text-sm tech-input resize-none"
            />
          </div>

          {/* Model Selection */}
          <div>
            <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-2">
              {t('MODELS (MAX 3)')}
            </label>
            <div className="flex flex-wrap gap-2">
              {availableModels.map((m) => (
                <button
                  key={m.name}
                  onClick={() => togglePgModel(m.name)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all border ${
                    pgModels.includes(m.name)
                      ? 'bg-[#E3FCEF] text-[#00A34D] border-[#00A34D]/20'
                      : 'text-[#889397] border-[#E8EDEB] hover:text-[#5C6C75] hover:border-[#C1C7C6]'
                  }`}
                >
                  {m.name}
                </button>
              ))}
              {availableModels.length === 0 && (
                <span className="text-sm text-[#889397]">{t('NO MODELS')}</span>
              )}
            </div>
          </div>

          {/* Run */}
          <button
            onClick={handlePgRun}
            disabled={isLoadingPlayground || !pgPrompt.trim() || pgModels.length === 0}
            className="btn-primary w-full px-4 py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoadingPlayground ? t('RUNNING') : t('RUN TEST')}
          </button>

          {/* Error */}
          {playgroundError && (
            <div className="p-3 bg-[#FDECEC] border border-[#E65C5C]/20 rounded-xl">
              <p className="text-sm text-[#E65C5C] font-medium">{playgroundError}</p>
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
