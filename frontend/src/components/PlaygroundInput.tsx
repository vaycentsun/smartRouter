import { useState } from 'react'
import { useTranslation } from '../i18n/I18nProvider'
import { useDashboardStore } from '../store/useDashboardStore'
import type { PlaygroundRequest } from '../types'

interface PlaygroundInputProps {
  onSubmit: (request: PlaygroundRequest) => void
}

export function PlaygroundInput({ onSubmit }: PlaygroundInputProps) {
  const { t } = useTranslation()
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
    <div className="card-base rounded-xl">
      <div className="p-4 border-b border-[#E8EDEB] flex items-center gap-2">
        <div className="w-1 h-4 bg-[#00A34D]" />
        <h2 className="text-base font-semibold text-[#001E2B]">{t('Playground')}</h2>
      </div>
      <div className="p-5 space-y-4">
        {/* Mode Switch */}
        <div>
          <label className="block text-xs text-[#889397] mb-2">
            {t('MODE')}
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => setMode('single')}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                mode === 'single'
                  ? 'strategy-btn-active'
                  : 'strategy-btn text-[#889397] hover:text-[#001E2B]'
              }`}
            >
              {t('Single')}
            </button>
            <button
              onClick={() => setMode('compare')}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                mode === 'compare'
                  ? 'strategy-btn-active'
                  : 'strategy-btn text-[#889397] hover:text-[#001E2B]'
              }`}
            >
              {t('Compare')}
            </button>
          </div>
        </div>

        {/* Model Selection */}
        <div>
          <label className="block text-xs text-[#889397] mb-2">
            {t('MODELS (MAX 3)')}
          </label>
          <div className="flex flex-wrap gap-2">
            {availableModels.map((m) => (
              <button
                key={m.name}
                onClick={() => toggleModel(m.name)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all border ${
                  selectedModels.includes(m.name)
                    ? 'bg-[rgba(0,163,77,0.08)] text-[#00A34D] border-[rgba(0,163,77,0.15)]'
                    : 'text-[#889397] border-transparent hover:text-[#001E2B] hover:bg-[#F9FBFA]'
                }`}
              >
                {m.name}
              </button>
            ))}
            {availableModels.length === 0 && (
              <span className="text-sm text-[#889397]">{t('NO MODELS AVAILABLE')}</span>
            )}
          </div>
        </div>

        {/* Prompt Input */}
        <div>
          <label className="block text-xs text-[#889397] mb-2">
            {t('PROMPT')}
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={t('Enter prompt...')}
            rows={4}
            className="w-full px-3 py-2 rounded-lg text-sm input-glow resize-none"
          />
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={isLoadingPlayground || !prompt.trim() || selectedModels.length === 0}
          className="w-full px-4 py-2.5 btn-primary rounded-full disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium"
        >
          {isLoadingPlayground ? t('LOADING...') : t('SUBMIT')}
        </button>
      </div>
    </div>
  )
}
