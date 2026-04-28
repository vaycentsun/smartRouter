import type { ProviderInfo } from '../types'

interface ProviderSidebarProps {
  providers: ProviderInfo[]
  selectedProvider: string | null
  modelsCount: Record<string, number>
  onSelect: (name: string) => void
}

function StatusDot({ hasKey }: { hasKey: boolean }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${
        hasKey ? 'bg-emerald-400' : 'bg-red-400'
      }`}
      title={hasKey ? 'Key 已配置' : 'Key 缺失'}
    />
  )
}

export function ProviderSidebar({ providers, selectedProvider, modelsCount, onSelect }: ProviderSidebarProps) {
  if (providers.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-6">
        <p className="text-[#a1a1a6] text-sm">暂无 Provider 数据</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {providers.map((provider) => {
        const isSelected = selectedProvider === provider.name
        const count = modelsCount[provider.name] || 0
        return (
          <button
            key={provider.name}
            onClick={() => onSelect(provider.name)}
            className={`w-full text-left p-4 rounded-2xl border transition-all duration-200 ${
              isSelected
                ? 'bg-[rgba(0,122,255,0.06)] border-[rgba(0,122,255,0.2)] shadow-sm'
                : 'bg-white/60 border-transparent hover:bg-white/80 hover:border-[rgba(0,0,0,0.06)]'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <StatusDot hasKey={provider.has_key} />
                <span className="font-semibold text-[#1d1d1f] text-sm">{provider.name}</span>
              </div>
              <span className="text-xs bg-[rgba(0,0,0,0.04)] text-[#86868b] px-2 py-0.5 rounded-full font-mono">
                {count} 模型
              </span>
            </div>
            <p className="text-xs text-[#a1a1a6] truncate font-mono">{provider.api_base}</p>
            <div className="mt-2 flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded-full border ${
                provider.has_key
                  ? 'bg-[rgba(52,199,89,0.06)] text-[#34C759] border-[rgba(52,199,89,0.12)]'
                  : 'bg-[rgba(255,59,48,0.06)] text-[#FF3B30] border-[rgba(255,59,48,0.12)]'
              }`}>
                {provider.has_key ? 'Key 已配置' : 'Key 缺失'}
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )
}
