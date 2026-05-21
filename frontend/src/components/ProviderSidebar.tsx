import { useMemo } from 'react'
import type { ProviderInfo } from '../types'
import { useTranslation } from '../i18n/I18nProvider'

interface ProviderSidebarProps {
  providers: ProviderInfo[]
  selectedProvider: string | null
  modelsCount: Record<string, number>
  onSelect: (name: string) => void
  onAddProvider?: () => void
}

function StatusDot({ hasKey, enabled }: { hasKey: boolean; enabled: boolean }) {
  const { t } = useTranslation()
  const colorClass = !enabled ? 'bg-[#889397]' : hasKey ? 'bg-[#00A34D]' : 'bg-[#E65C5C]'
  const title = !enabled ? t('Provider disabled') : hasKey ? t('Key configured') : t('Key missing')
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${colorClass}`}
      title={title}
    />
  )
}

export function ProviderSidebar({ providers, selectedProvider, modelsCount, onSelect, onAddProvider }: ProviderSidebarProps) {
  const { t } = useTranslation()
  const sortedProviders = useMemo(() => {
    return [...providers].sort((a, b) => {
      if (a.has_key !== b.has_key) {
        return a.has_key ? -1 : 1
      }
      return a.name.localeCompare(b.name)
    })
  }, [providers])

  if (providers.length === 0) {
    return (
      <div className="space-y-2">
        {onAddProvider && (
          <button
            onClick={onAddProvider}
            className="w-full btn-primary px-3 py-2 text-xs mb-2"
          >
            + Add Provider
          </button>
        )}
        <div className="card-base p-6">
          <p className="text-[#889397] text-sm">{t('NO PROVIDERS')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {onAddProvider && (
        <button
          onClick={onAddProvider}
          className="w-full btn-primary px-3 py-2 text-xs mb-2"
        >
          + Add Provider
        </button>
      )}
      {sortedProviders.map((provider) => {
        const isSelected = selectedProvider === provider.name
        const count = modelsCount[provider.name] || 0
        return (
          <button
            key={provider.name}
            onClick={() => onSelect(provider.name)}
            className={`w-full text-left p-3 rounded-xl border transition-all duration-200 ${
              isSelected
                ? 'bg-[#E3FCEF] border-[#00A34D]/30'
                : 'bg-white border-transparent hover:bg-[#F9FBFA] hover:border-[#E8EDEB]'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <StatusDot hasKey={provider.has_key} enabled={provider.enabled ?? true} />
                <span className="font-semibold text-[#001E2B] text-sm">{provider.name}</span>
              </div>
              <span className="text-xs bg-[#F4F7F6] text-[#889397] px-2 py-0.5 rounded-full font-medium">
                {count}
              </span>
            </div>
            <p className="text-xs text-[#889397] truncate">{provider.api_base}</p>
            <div className="mt-1.5 flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                !(provider.enabled ?? true)
                  ? 'bg-[#F4F7F6] text-[#889397]'
                  : provider.has_key
                    ? 'bg-[#E3FCEF] text-[#00A34D]'
                    : 'bg-[#FDECEC] text-[#E65C5C]'
              }`}>
                {!(provider.enabled ?? true) ? t('DISABLED') : provider.has_key ? t('CONFIGURED') : t('MISSING')}
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )
}
