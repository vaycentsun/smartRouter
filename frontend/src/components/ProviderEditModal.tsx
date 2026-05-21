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
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white border border-[#E8EDEB] rounded-xl w-full max-w-lg mx-4 overflow-hidden shadow-modal">
        <div className="p-4 border-b border-[#E8EDEB] flex items-center justify-between">
          <h3 className="text-base font-semibold text-[#001E2B]">{t('EDIT')}: {provider.name}</h3>
          <button onClick={onClose} className="text-[#889397] hover:text-[#001E2B] transition-colors text-xl">&times;</button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-1.5">{t('API BASE')}</label>
            <input
              type="text"
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
              className="w-full px-3 py-2 rounded-lg text-sm tech-input"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-1.5">{t('API KEY')}</label>
            <div className="flex items-center gap-2">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                placeholder={provider.masked_key || t('NOT CONFIGURED')}
                onChange={(e) => setApiKey(e.target.value)}
                className="flex-1 px-3 py-2 rounded-lg text-sm tech-input placeholder-[#889397]"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="text-[#889397] hover:text-[#00A34D] text-xs px-2 transition-colors font-medium"
                title={showKey ? t('HIDE') : t('SHOW')}
              >
                {showKey ? t('HIDE') : t('SHOW')}
              </button>
            </div>
            <p className="text-xs text-[#889397] mt-1">{t('Leave empty to keep current')}</p>
          </div>
          <div>
            <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-1.5">{t('TIMEOUT')}</label>
            <input
              type="number"
              value={timeout}
              onChange={(e) => setTimeout(parseInt(e.target.value) || 30)}
              className="w-32 px-3 py-2 rounded-lg text-sm tech-input"
            />
          </div>
        </div>
        <div className="p-4 border-t border-[#E8EDEB] flex justify-end gap-3">
          <button
            onClick={onClose}
            className="btn-secondary px-4 py-2 text-xs"
          >
            {t('CANCEL')}
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="btn-primary px-4 py-2 text-xs disabled:opacity-50"
          >
            {isSaving ? t('SAVING') : t('SAVE')}
          </button>
        </div>
      </div>
    </div>
  )
}
