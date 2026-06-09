import { useState, useEffect, useMemo } from 'react'
import { useTranslation } from '../i18n/useTranslation'
import { useDashboardStore } from '../store/useDashboardStore'

interface EditableProvider {
  api_base: string
  api_key: string
  timeout: number
  showKey: boolean
  dirty: boolean
  apiKeyDirty: boolean
}

function StatusDot({ hasKey }: { hasKey: boolean }) {
  const { t } = useTranslation()
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-sm ${
        hasKey ? 'bg-[#00d4aa] pulse-glow' : 'bg-[#e74c3c] pulse-glow'
      }`}
      title={hasKey ? t('KEY CONFIGURED') : t('KEY MISSING')}
    />
  )
}

export function ProvidersTable() {
  const { t } = useTranslation()
  const { providers, saveProviders, isSavingProviders, toast, clearToast } = useDashboardStore()
  const [edits, setEdits] = useState<Record<string, EditableProvider>>({})

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    const initial: Record<string, EditableProvider> = {}
    providers.forEach((p) => {
      initial[p.name] = {
        api_base: p.api_base,
        api_key: p.key_type.startsWith('env:')
          ? `os.environ/${p.key_type.replace('env:', '')}`
          : '',
        timeout: p.timeout,
        showKey: false,
        dirty: false,
        apiKeyDirty: false,
      }
    })
    setEdits(initial)
  }, [providers])
  /* eslint-enable react-hooks/set-state-in-effect */

  const hasChanges = useMemo(() => Object.values(edits).some((e) => e.dirty), [edits])

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => clearToast(), 3000)
      return () => clearTimeout(timer)
    }
  }, [toast, clearToast])

  const handleChange = (name: string, field: keyof EditableProvider, value: string | number | boolean) => {
    setEdits((prev) => ({
      ...prev,
      [name]: {
        ...prev[name],
        [field]: value,
        dirty: true,
        ...(field === 'api_key' ? { apiKeyDirty: true } : {}),
      },
    }))
  }

  const handleSave = async () => {
    const payload: Record<string, { api_base: string; api_key?: string; timeout: number }> = {}
    Object.entries(edits).forEach(([name, edit]) => {
      if (edit.dirty) {
        const entry: { api_base: string; api_key?: string; timeout: number } = {
          api_base: edit.api_base,
          timeout: edit.timeout,
        }
        if (edit.apiKeyDirty) {
          entry.api_key = edit.api_key
        }
        payload[name] = entry
      }
    })
    if (Object.keys(payload).length === 0) return
    await saveProviders(payload)
    setEdits((prev) => {
      const next: Record<string, EditableProvider> = {}
      Object.entries(prev).forEach(([name, edit]) => {
        next[name] = { ...edit, dirty: false, apiKeyDirty: false }
      })
      return next
    })
  }

  if (providers.length === 0) {
    return (
      <div className="tech-card rounded-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1 h-4 bg-[#00d4aa]" />
          <h2 className="text-base font-semibold text-[#e8e8ed] uppercase tracking-wider font-mono">{t('PROVIDERS')}</h2>
        </div>
        <p className="text-[#636366] text-sm">{t('NO PROVIDER DATA')}</p>
      </div>
    )
  }

  return (
    <div className="tech-card rounded-sm">
      <div className="p-4 border-b border-[#1a1a2e] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-1 h-4 bg-[#00d4aa]" />
          <h2 className="text-base font-semibold text-[#e8e8ed] uppercase tracking-wider font-mono">{t('PROVIDERS')}</h2>
        </div>
        <div className="flex items-center gap-3">
          {toast && (
            <span
              className={`text-xs px-3 py-1 rounded-sm font-mono ${
                toast.type === 'success'
                  ? 'tech-tag tech-tag-accent'
                  : 'tech-tag tech-tag-danger'
              }`}
            >
              {toast.message}
            </span>
          )}
          <button
            onClick={handleSave}
            disabled={!hasChanges || isSavingProviders}
            className={`px-4 py-2 rounded-sm text-sm font-medium transition-all ${
              hasChanges && !isSavingProviders
                ? 'tech-btn-primary'
                : 'tech-btn-muted cursor-not-allowed'
            }`}
          >
            {isSavingProviders ? t('SAVING...') : t('SAVE CHANGES')}
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-[#0a0a0f] text-[#636366]">
            <tr>
              <th className="px-4 py-3 text-[10px] text-[#636366] font-mono uppercase tracking-widest w-10">{t('STATUS')}</th>
              <th className="px-4 py-3 text-[10px] text-[#636366] font-mono uppercase tracking-widest">{t('NAME')}</th>
              <th className="px-4 py-3 text-[10px] text-[#636366] font-mono uppercase tracking-widest">{t('API BASE')}</th>
              <th className="px-4 py-3 text-[10px] text-[#636366] font-mono uppercase tracking-widest">{t('API KEY')}</th>
              <th className="px-4 py-3 text-[10px] text-[#636366] font-mono uppercase tracking-widest w-24">{t('TIMEOUT')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1a1a2e]">
            {providers.map((provider) => {
              const edit = edits[provider.name]
              if (!edit) return null

              const isEnvKey = provider.key_type.startsWith('env:')
              const keyPlaceholder = isEnvKey
                ? ''
                : provider.masked_key || t('NO API KEY')

              return (
                <tr
                  key={provider.name}
                  className={`data-row ${edit.dirty ? 'bg-[rgba(0,212,170,0.03)]' : ''}`}
                >
                  <td className="px-4 py-3">
                    <StatusDot hasKey={provider.has_key} />
                  </td>
                  <td className="px-4 py-3 font-medium text-[#e8e8ed]">{provider.name}</td>
                  <td className="px-4 py-3">
                    <input
                      type="text"
                      value={edit.api_base}
                      onChange={(e) => handleChange(provider.name, 'api_base', e.target.value)}
                      className="w-full px-2 py-1 rounded-sm text-sm text-[#e8e8ed] input-glow"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <input
                        type={edit.showKey ? 'text' : 'password'}
                        value={edit.api_key}
                        placeholder={keyPlaceholder}
                        onChange={(e) => handleChange(provider.name, 'api_key', e.target.value)}
                        className="flex-1 min-w-0 px-2 py-1 rounded-sm text-sm text-[#e8e8ed] input-glow placeholder-[#636366]"
                      />
                      <button
                        type="button"
                        onClick={() => handleChange(provider.name, 'showKey', !edit.showKey)}
                        className="text-[#636366] hover:text-[#00d4aa] text-xs px-1 transition-colors font-mono uppercase tracking-wider"
                        title={edit.showKey ? t('HIDE') : t('SHOW')}
                      >
                        {edit.showKey ? t('HIDE') : t('SHOW')}
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="number"
                      value={edit.timeout}
                      onChange={(e) => handleChange(provider.name, 'timeout', parseInt(e.target.value) || 30)}
                      className="w-20 px-2 py-1 rounded-sm text-sm text-[#e8e8ed] input-glow"
                    />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
