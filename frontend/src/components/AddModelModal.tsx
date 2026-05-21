import { useState } from 'react'
import type { AddModelRequest } from '../types'

interface AddModelModalProps {
  providerName: string
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: AddModelRequest) => void
  isSaving: boolean
}

export function AddModelModal({ providerName, isOpen, onClose, onSubmit, isSaving }: AddModelModalProps) {
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
      newErrors.name = '名称不能为空'
    }

    if (!litellmModel.trim()) {
      newErrors.litellm_model = 'LiteLLM 模型不能为空'
    }

    const qualityNum = Number(quality)
    if (!Number.isInteger(qualityNum) || qualityNum < 1 || qualityNum > 10) {
      newErrors.quality = '质量必须在 1-10 之间'
    }

    const costNum = Number(cost)
    if (!Number.isInteger(costNum) || costNum < 1 || costNum > 10) {
      newErrors.cost = '成本必须在 1-10 之间'
    }

    const contextNum = Number(context)
    if (!Number.isInteger(contextNum) || contextNum < 1) {
      newErrors.context = '上下文必须为正整数'
    }

    const tasks = supportedTasks.split(',').map((t) => t.trim()).filter(Boolean)
    if (tasks.length === 0) {
      newErrors.supported_tasks = '至少需要一个支持的任务类型'
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
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white border border-[#E8EDEB] rounded-xl w-full max-w-lg mx-4 overflow-hidden shadow-modal">
        <div className="p-4 border-b border-[#E8EDEB] flex items-center justify-between">
          <h3 className="text-base font-semibold text-[#001E2B]">
            添加模型: {providerName}
          </h3>
          <button onClick={onClose} className="text-[#889397] hover:text-[#001E2B] transition-colors text-xl">
            &times;
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-1.5">名称</label>
            <input
              type="text"
              value={name}
              placeholder="模型名称"
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg text-sm tech-input placeholder-[#889397]"
            />
            {errors.name && <p className="text-xs text-[#E65C5C] mt-1 font-medium">{errors.name}</p>}
          </div>

          <div>
            <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-1.5">LiteLLM 模型</label>
            <input
              type="text"
              value={litellmModel}
              placeholder="litellm 模型名称"
              onChange={(e) => setLitellmModel(e.target.value)}
              className="w-full px-3 py-2 rounded-lg text-sm tech-input placeholder-[#889397]"
            />
            {errors.litellm_model && <p className="text-xs text-[#E65C5C] mt-1 font-medium">{errors.litellm_model}</p>}
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-1.5">质量</label>
              <input
                type="number"
                value={quality}
                min={1}
                max={10}
                aria-label="质量"
                onChange={(e) => setQuality(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-lg text-sm tech-input"
              />
              {errors.quality && <p className="text-xs text-[#E65C5C] mt-1 font-medium">{errors.quality}</p>}
            </div>
            <div>
              <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-1.5">成本</label>
              <input
                type="number"
                value={cost}
                min={1}
                max={10}
                aria-label="成本"
                onChange={(e) => setCost(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-lg text-sm tech-input"
              />
              {errors.cost && <p className="text-xs text-[#E65C5C] mt-1 font-medium">{errors.cost}</p>}
            </div>
            <div>
              <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-1.5">上下文</label>
              <input
                type="number"
                value={context}
                min={1}
                aria-label="上下文"
                onChange={(e) => setContext(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-lg text-sm tech-input"
              />
              {errors.context && <p className="text-xs text-[#E65C5C] mt-1 font-medium">{errors.context}</p>}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-1.5">支持任务</label>
            <input
              type="text"
              value={supportedTasks}
              placeholder="chat,code,embedding"
              onChange={(e) => setSupportedTasks(e.target.value)}
              className="w-full px-3 py-2 rounded-lg text-sm tech-input placeholder-[#889397]"
            />
            {errors.supported_tasks && <p className="text-xs text-[#E65C5C] mt-1 font-medium">{errors.supported_tasks}</p>}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="enabled"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="rounded border-[#C1C7C6] bg-white text-[#00A34D] focus:ring-[#00A34D]"
            />
            <label htmlFor="enabled" className="text-sm text-[#001E2B] cursor-pointer">启用</label>
          </div>
        </div>
        <div className="p-4 border-t border-[#E8EDEB] flex justify-end gap-3">
          <button
            onClick={onClose}
            className="btn-secondary px-4 py-2 text-xs"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSaving}
            className="btn-primary px-4 py-2 text-xs disabled:opacity-50"
          >
            {isSaving ? '添加中...' : '添加'}
          </button>
        </div>
      </div>
    </div>
  )
}
