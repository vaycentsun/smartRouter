import { useMemo } from 'react'
import type { ProviderInfo } from '../types'
import { useTranslation } from '../i18n/I18nProvider'

interface ProviderSidebarProps {
  providers: ProviderInfo[]
  selectedProvider: string | null
  modelsCount: Record<string, number>
  onSelect: (name: string) => void
}

function StatusDot({ hasKey, enabled }: { hasKey: boolean; enabled: boolean }) {
  const { t } = useTranslation()
  const colorClass = !enabled ? 'bg-[#636366]' : hasKey ? 'bg-[#00d4aa]' : 'bg-[#e74c3c]'
  const title = !enabled ? t('Provider disabled') : hasKey ? t('Key configured') : t('Key missing')
  return (
    <span
      className={`inline-block w-1.5 h-1.5 rounded-sm ${colorClass}`}
      title={title}
    />
  )
}

export function ProviderSidebar({ providers, selectedProvider, modelsCount, onSelect }: ProviderSidebarProps) {
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
      <div className="tech-card rounded-sm p-6">
        <p className="text-[#636366] text-sm font-mono">{t('NO PROVIDERS')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {sortedProviders.map((provider) => {
        const isSelected = selectedProvider === provider.name
        const count = modelsCount[provider.name] || 0
        return (
          <button
            key={provider.name}
            onClick={() => onSelect(provider.name)}
            className={`w-full text-left p-3 rounded-sm border transition-all duration-200 ${
              isSelected
                ? 'bg-[rgba(0,212,170,0.04)] border-[rgba(0,212,170,0.2)]'
                : 'bg-transparent border-transparent hover:bg-white/[0.02] hover:border-[#1a1a2e]'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <StatusDot hasKey={provider.has_key} enabled={provider.enabled ?? true} />
                <span className="font-semibold text-[#e8e8ed] text-sm font-mono">{provider.name}</span>
              </div>
              <span className="text-xs bg-[#0a0a0f] text-[#636366] px-2 py-0.5 rounded-sm font-mono border border-[#1a1a2e]">
                {count}
              </span>
            </div>
            <p className="text-xs text-[#636366] truncate font-mono">{provider.api_base}</p>
            <div className="mt-1.5 flex items-center gap-2">
              <span className={`text-[10px] px-2 py-0.5 rounded-sm border font-mono uppercase tracking-wider ${
                !(provider.enabled ?? true)
                  ? 'bg-[rgba(99,99,102,0.06)] text-[#636366] border-[rgba(99,99,102,0.12)]'
                  : provider.has_key
                    ? 'bg-[rgba(0,212,170,0.06)] text-[#00d4aa] border-[rgba(0,212,170,0.12)]'
                    : 'bg-[rgba(231,76,60,0.06)] text-[#e74c3c] border-[rgba(231,76,60,0.12)]'
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
