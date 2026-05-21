import { useState, useEffect } from 'react'
import type { CreateProviderRequest } from '../types'
import { useTranslation } from '../i18n/I18nProvider'

interface AddProviderModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: CreateProviderRequest) => void
  isSaving: boolean
}

export function AddProviderModal({ isOpen, onClose, onSubmit, isSaving }: AddProviderModalProps) {
  const { t } = useTranslation()
  const [name, setName] = useState('')
  const [apiBase, setApiBase] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [timeout, setTimeout] = useState(30)
  const [showKey, setShowKey] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isOpen) {
      setName('')
      setApiBase('')
      setApiKey('')
      setTimeout(30)
      setShowKey(false)
      setError('')
    }
  }, [isOpen])

  if (!isOpen) return null

  const handleSubmit = () => {
    setError('')

    if (!name.trim()) {
      setError('Name is required')
      return
    }

    if (!apiBase.trim()) {
      setError('API Base is required')
      return
    }

    const timeoutNum = Number(timeout)
    if (!timeoutNum || timeoutNum < 1 || timeoutNum > 300) {
      setError('Timeout must be between 1 and 300')
      return
    }

    onSubmit({
      name: name.trim(),
      api_base: apiBase.trim(),
      api_key: apiKey,
      timeout: timeoutNum,
    })
  }

  const handleClose = () => {
    setError('')
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={handleClose} />
      <div className="relative bg-white border border-[#E8EDEB] rounded-xl w-full max-w-lg mx-4 overflow-hidden shadow-modal">
        <div className="p-4 border-b border-[#E8EDEB] flex items-center justify-between">
          <h3 className="text-base font-semibold text-[#001E2B]">
            {t('ADD PROVIDER')}
          </h3>
          <button
            onClick={handleClose}
            className="text-[#889397] hover:text-[#001E2B] transition-colors text-xl"
          >
            &times;
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-1.5">
              {t('NAME')}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg text-sm tech-input"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-1.5">
              {t('API BASE')}
            </label>
            <input
              type="text"
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
              className="w-full px-3 py-2 rounded-lg text-sm tech-input"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-1.5">
              {t('API KEY')}
            </label>
            <div className="flex items-center gap-2">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="flex-1 px-3 py-2 rounded-lg text-sm tech-input"
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
          </div>
          <div>
            <label className="block text-xs font-medium text-[#889397] uppercase tracking-wider mb-1.5">
              {t('TIMEOUT')}
            </label>
            <input
              type="number"
              value={timeout}
              onChange={(e) => setTimeout(parseInt(e.target.value) || 0)}
              className="w-32 px-3 py-2 rounded-lg text-sm tech-input"
            />
          </div>
          {error && (
            <div className="text-[#E65C5C] text-xs font-medium">{error}</div>
          )}
        </div>
        <div className="p-4 border-t border-[#E8EDEB] flex justify-end gap-3">
          <button
            onClick={handleClose}
            className="btn-secondary px-4 py-2 text-xs"
          >
            {t('CANCEL')}
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSaving}
            className="btn-primary px-4 py-2 text-xs disabled:opacity-50"
          >
            {isSaving ? t('SAVING') : t('CREATE')}
          </button>
        </div>
      </div>
    </div>
  )
}
