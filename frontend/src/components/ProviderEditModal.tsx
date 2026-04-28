import { useState, useEffect } from 'react'
import type { ProviderInfo, ProviderUpdate } from '../types'

interface ProviderEditModalProps {
  provider: ProviderInfo | null
  isOpen: boolean
  onClose: () => void
  onSave: (name: string, update: ProviderUpdate) => void
  isSaving: boolean
}

export function ProviderEditModal({ provider, isOpen, onClose, onSave, isSaving }: ProviderEditModalProps) {
  const [apiBase, setApiBase] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [timeout, setTimeout] = useState(30)
  const [showKey, setShowKey] = useState(false)

  useEffect(() => {
    if (provider) {
      setApiBase(provider.api_base)
      setApiKey(provider.key_type.startsWith('env:') ? `os.environ/${provider.key_type.replace('env:', '')}` : '')
      setTimeout(provider.timeout)
      setShowKey(false)
    }
  }, [provider])

  if (!isOpen || !provider) return null

  const handleSave = () => {
    const update: ProviderUpdate = { api_base: apiBase, timeout }
    if (apiKey.trim()) {
      update.api_key = apiKey
    }
    onSave(provider.name, update)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 overflow-hidden">
        <div className="p-4 border-b border-[rgba(0,0,0,0.06)] flex items-center justify-between">
          <h3 className="text-base font-semibold text-[#1d1d1f]">编辑 Provider: {provider.name}</h3>
          <button onClick={onClose} className="text-[#a1a1a6] hover:text-[#1d1d1f] transition-colors text-xl">&times;</button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-mono text-[#86868b] uppercase tracking-wider mb-1.5">API Base</label>
            <input
              type="text"
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
              className="w-full px-3 py-2 rounded-xl text-sm text-[#1d1d1f] input-glow"
            />
          </div>
          <div>
            <label className="block text-xs font-mono text-[#86868b] uppercase tracking-wider mb-1.5">API Key</label>
            <div className="flex items-center gap-2">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                placeholder={provider.masked_key || '未配置 API Key'}
                onChange={(e) => setApiKey(e.target.value)}
                className="flex-1 px-3 py-2 rounded-xl text-sm text-[#1d1d1f] input-glow placeholder-[#a1a1a6]"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="text-[#a1a1a6] hover:text-[#007AFF] text-xs px-2 transition-colors"
                title={showKey ? '隐藏' : '显示'}
              >
                {showKey ? '🙈' : '👁'}
              </button>
            </div>
            <p className="text-xs text-[#a1a1a6] mt-1">留空则保持现有配置</p>
          </div>
          <div>
            <label className="block text-xs font-mono text-[#86868b] uppercase tracking-wider mb-1.5">Timeout</label>
            <input
              type="number"
              value={timeout}
              onChange={(e) => setTimeout(parseInt(e.target.value) || 30)}
              className="w-32 px-3 py-2 rounded-xl text-sm text-[#1d1d1f] input-glow"
            />
          </div>
        </div>
        <div className="p-4 border-t border-[rgba(0,0,0,0.06)] flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-sm text-[#86868b] hover:bg-[rgba(0,0,0,0.03)] transition-all"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 bg-[#007AFF] text-white rounded-xl text-sm font-medium hover:bg-[#0051D5] disabled:opacity-50 transition-all"
          >
            {isSaving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}
