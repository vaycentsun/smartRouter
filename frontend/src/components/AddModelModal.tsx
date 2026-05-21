import { useState } from 'react'
import type { AddModelRequest } from '../types'
import { useTranslation } from '../i18n/I18nProvider'

interface AddModelModalProps {
  providerName: string
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: AddModelRequest) => void
  isSaving: boolean
}

export function AddModelModal({ providerName, isOpen, onClose, onSubmit, isSaving }: AddModelModalProps) {
  const { t } = useTranslation()
  const [name, setName] = useState('')
  const [litellmModel, setLitellmModel] = useState('')
  const [quality, setQuality] = useState(5)
  const [cost, setCost] = useState(5)
  const [context, setContext] = useState(4096)
  const [supportedTasks, setSupportedTasks] = useState('')
  const [enabled, setEnabled] = useState(true)
  const [errors, setErrors] = useState<Record<string, string>>({})

  if (!isOpen) return null

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!name.trim()) {
      newErrors.name = t('Name is required')
    }

    if (!litellmModel.trim()) {
      newErrors.litellm_model = t('LiteLLM model is required')
    }

    const qualityNum = Number(quality)
    if (!Number.isInteger(qualityNum) || qualityNum < 1 || qualityNum > 10) {
      newErrors.quality = t('Quality must be 1-10')
    }

    const costNum = Number(cost)
    if (!Number.isInteger(costNum) || costNum < 1 || costNum > 10) {
      newErrors.cost = t('Cost must be 1-10')
    }

    const contextNum = Number(context)
    if (!Number.isInteger(contextNum) || contextNum < 1) {
      newErrors.context = t('Context must be positive')
    }

    const tasks = supportedTasks.split(',').map((t) => t.trim()).filter(Boolean)
    if (tasks.length === 0) {
      newErrors.supported_tasks = t('At least one task required')
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = () => {
    if (!validate()) return

    const tasks = supportedTasks.split(',').map((t) => t.trim()).filter(Boolean)
    const data: AddModelRequest = {
      name: name.trim(),
      litellm_model: litellmModel.trim(),
      quality: Number(quality),
      cost: Number(cost),
      context: Number(context),
      supported_tasks: tasks,
      enabled,
    }
    onSubmit(data)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-[#111118] border border-[#1a1a2e] rounded-sm w-full max-w-lg mx-4 overflow-hidden">
        <div className="p-4 border-b border-[#1a1a2e] flex items-center justify-between">
          <h3 className="text-base font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">
            {t('ADD MODEL')}: {providerName}
          </h3>
          <button onClick={onClose} className="text-[#636366] hover:text-[#e8e8ed] transition-colors text-xl font-mono">
            &times;
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">{t('NAME')}</label>
            <input
              type="text"
              value={name}
              placeholder={t('NAME')}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input placeholder-[#636366]"
            />
            {errors.name && <p className="text-xs text-[#e74c3c] mt-1 font-mono">{errors.name}</p>}
          </div>

          <div>
            <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">{t('LITELLM MODEL')}</label>
            <input
              type="text"
              value={litellmModel}
              placeholder={t('LITELLM MODEL')}
              onChange={(e) => setLitellmModel(e.target.value)}
              className="w-full px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input placeholder-[#636366]"
            />
            {errors.litellm_model && <p className="text-xs text-[#e74c3c] mt-1 font-mono">{errors.litellm_model}</p>}
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">{t('QUALITY')}</label>
              <input
                type="number"
                value={quality}
                min={1}
                max={10}
                aria-label={t('QUALITY')}
                onChange={(e) => setQuality(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input"
              />
              {errors.quality && <p className="text-xs text-[#e74c3c] mt-1 font-mono">{errors.quality}</p>}
            </div>
            <div>
              <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">{t('COST')}</label>
              <input
                type="number"
                value={cost}
                min={1}
                max={10}
                aria-label={t('COST')}
                onChange={(e) => setCost(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input"
              />
              {errors.cost && <p className="text-xs text-[#e74c3c] mt-1 font-mono">{errors.cost}</p>}
            </div>
            <div>
              <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">{t('CONTEXT')}</label>
              <input
                type="number"
                value={context}
                min={1}
                aria-label={t('CONTEXT')}
                onChange={(e) => setContext(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input"
              />
              {errors.context && <p className="text-xs text-[#e74c3c] mt-1 font-mono">{errors.context}</p>}
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">{t('SUPPORTED TASKS')}</label>
            <input
              type="text"
              value={supportedTasks}
              placeholder="chat,code,embedding"
              onChange={(e) => setSupportedTasks(e.target.value)}
              className="w-full px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input placeholder-[#636366]"
            />
            {errors.supported_tasks && <p className="text-xs text-[#e74c3c] mt-1 font-mono">{errors.supported_tasks}</p>}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="enabled"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="rounded-sm border-[#1a1a2e] bg-[#0a0a0f] text-[#00d4aa] focus:ring-[#00d4aa]"
            />
            <label htmlFor="enabled" className="text-sm text-[#e8e8ed] font-mono cursor-pointer">{t('ENABLED')}</label>
          </div>
        </div>
        <div className="p-4 border-t border-[#1a1a2e] flex justify-end gap-3">
          <button
            onClick={onClose}
            className="tech-btn px-4 py-2 rounded-sm text-xs font-mono uppercase tracking-wider"
          >
            {t('CANCEL')}
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSaving}
            className="tech-btn tech-btn-primary px-4 py-2 rounded-sm text-xs disabled:opacity-50 font-mono uppercase tracking-wider"
          >
            {isSaving ? t('ADDING...') : t('CREATE')}
          </button>
        </div>
      </div>
    </div>
  )
}
