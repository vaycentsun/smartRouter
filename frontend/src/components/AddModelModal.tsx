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
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-[#111118] border border-[#1a1a2e] rounded-sm w-full max-w-lg mx-4 overflow-hidden">
        <div className="p-4 border-b border-[#1a1a2e] flex items-center justify-between">
          <h3 className="text-base font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">
            添加模型: {providerName}
          </h3>
          <button onClick={onClose} className="text-[#636366] hover:text-[#e8e8ed] transition-colors text-xl font-mono">
            &times;
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">名称</label>
            <input
              type="text"
              value={name}
              placeholder="模型名称"
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input placeholder-[#636366]"
            />
            {errors.name && <p className="text-xs text-red-400 mt-1 font-mono">{errors.name}</p>}
          </div>

          <div>
            <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">LiteLLM 模型</label>
            <input
              type="text"
              value={litellmModel}
              placeholder="litellm 模型名称"
              onChange={(e) => setLitellmModel(e.target.value)}
              className="w-full px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input placeholder-[#636366]"
            />
            {errors.litellm_model && <p className="text-xs text-red-400 mt-1 font-mono">{errors.litellm_model}</p>}
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">质量</label>
              <input
                type="number"
                value={quality}
                min={1}
                max={10}
                aria-label="质量"
                onChange={(e) => setQuality(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input"
              />
              {errors.quality && <p className="text-xs text-red-400 mt-1 font-mono">{errors.quality}</p>}
            </div>
            <div>
              <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">成本</label>
              <input
                type="number"
                value={cost}
                min={1}
                max={10}
                aria-label="成本"
                onChange={(e) => setCost(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input"
              />
              {errors.cost && <p className="text-xs text-red-400 mt-1 font-mono">{errors.cost}</p>}
            </div>
            <div>
              <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">上下文</label>
              <input
                type="number"
                value={context}
                min={1}
                aria-label="上下文"
                onChange={(e) => setContext(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input"
              />
              {errors.context && <p className="text-xs text-red-400 mt-1 font-mono">{errors.context}</p>}
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">支持任务</label>
            <input
              type="text"
              value={supportedTasks}
              placeholder="chat,code,embedding"
              onChange={(e) => setSupportedTasks(e.target.value)}
              className="w-full px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input placeholder-[#636366]"
            />
            {errors.supported_tasks && <p className="text-xs text-red-400 mt-1 font-mono">{errors.supported_tasks}</p>}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="enabled"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="rounded-sm border-[#1a1a2e] bg-[#0a0a0f] text-[#00d4aa] focus:ring-[#00d4aa]"
            />
            <label htmlFor="enabled" className="text-sm text-[#e8e8ed] font-mono cursor-pointer">启用</label>
          </div>
        </div>
        <div className="p-4 border-t border-[#1a1a2e] flex justify-end gap-3">
          <button
            onClick={onClose}
            className="tech-btn px-4 py-2 rounded-sm text-xs"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSaving}
            className="tech-btn tech-btn-primary px-4 py-2 rounded-sm text-xs disabled:opacity-50"
          >
            {isSaving ? '添加中...' : '添加'}
          </button>
        </div>
      </div>
    </div>
  )
}
