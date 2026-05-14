import { useState, useEffect } from 'react'
import type { ProviderInfo, ProviderUpdate } from '../types'
import { useTranslation } from '../i18n/I18nProvider'

interface ProviderEditModalProps {
  provider: ProviderInfo | null
  isOpen: boolean
  onClose: () => void
  onSave: (name: string, update: ProviderUpdate) => void
  isSaving: boolean
}

export function ProviderEditModal({ provider, isOpen, onClose, onSave, isSaving }: ProviderEditModalProps) {
  const { t } = useTranslation()
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
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-[#111118] border border-[#1a1a2e] rounded-sm w-full max-w-lg mx-4 overflow-hidden">
        <div className="p-4 border-b border-[#1a1a2e] flex items-center justify-between">
          <h3 className="text-base font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('EDIT')}: {provider.name}</h3>
          <button onClick={onClose} className="text-[#636366] hover:text-[#e8e8ed] transition-colors text-xl font-mono">&times;</button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">{t('API BASE')}</label>
            <input
              type="text"
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
              className="w-full px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input"
            />
          </div>
          <div>
            <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">{t('API KEY')}</label>
            <div className="flex items-center gap-2">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                placeholder={provider.masked_key || t('NOT CONFIGURED')}
                onChange={(e) => setApiKey(e.target.value)}
                className="flex-1 px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input placeholder-[#636366]"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="text-[#636366] hover:text-[#00d4aa] text-xs px-2 transition-colors font-mono"
                title={showKey ? t('HIDE') : t('SHOW')}
              >
                {showKey ? t('HIDE') : t('SHOW')}
              </button>
            </div>
            <p className="text-xs text-[#636366] mt-1 font-mono">{t('Leave empty to keep current')}</p>
          </div>
          <div>
            <label className="block text-[10px] font-mono text-[#636366] uppercase tracking-widest mb-1.5">{t('TIMEOUT')}</label>
            <input
              type="number"
              value={timeout}
              onChange={(e) => setTimeout(parseInt(e.target.value) || 30)}
              className="w-32 px-3 py-2 rounded-sm text-sm text-[#e8e8ed] tech-input"
            />
          </div>
        </div>
        <div className="p-4 border-t border-[#1a1a2e] flex justify-end gap-3">
          <button
            onClick={onClose}
            className="tech-btn px-4 py-2 rounded-sm text-xs"
          >
            {t('CANCEL')}
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="tech-btn tech-btn-primary px-4 py-2 rounded-sm text-xs disabled:opacity-50"
          >
            {isSaving ? t('SAVING') : t('SAVE')}
          </button>
        </div>
      </div>
    </div>
  )
}
