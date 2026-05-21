import { useState, useMemo, useEffect } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import type { ProviderUpdate } from '../types'
import { ProviderSidebar } from './ProviderSidebar'
import { ProviderModelsPanel } from './ProviderModelsPanel'
import { ProviderEditModal } from './ProviderEditModal'
import { AddProviderModal } from './AddProviderModal'
import { AddModelModal } from './AddModelModal'
export function ModelsExplorer() {
  const { providers, models, saveProviders, isSavingProviders, toast, clearToast, checkProviderHealth, isCheckingHealth, createProvider, addModel, isLoading } = useDashboardStore()
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [addProviderOpen, setAddProviderOpen] = useState(false)
  const [addModelOpen, setAddModelOpen] = useState(false)

  // 默认选中第一个 provider
  useEffect(() => {
    if (providers.length > 0 && !selectedProvider) {
      setSelectedProvider(providers[0].name)
    }
  }, [providers, selectedProvider])

  // 若当前选中的 provider 已不存在，回退到第一个
  useEffect(() => {
    if (selectedProvider && providers.length > 0 && !providers.find((p) => p.name === selectedProvider)) {
      setSelectedProvider(providers[0].name)
    }
  }, [providers, selectedProvider])

  const modelsCount = useMemo(() => {
    const count: Record<string, number> = {}
    providers.forEach((p) => {
      count[p.name] = models.filter((m) => m.provider === p.name).length
    })
    return count
  }, [providers, models])

  const currentProvider = providers.find((p) => p.name === selectedProvider) || null

  const handleSave = async (name: string, update: ProviderUpdate) => {
    await saveProviders({ [name]: update })
    setEditModalOpen(false)
  }

  const handleSaveKey = async (apiKey: string) => {
    if (!currentProvider) return
    await saveProviders({ [currentProvider.name]: { api_key: apiKey } })
  }

  // Toast auto dismiss
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => clearToast(), 3000)
      return () => clearTimeout(timer)
    }
  }, [toast, clearToast])

  return (
    <div className="space-y-4">
      {/* Toast */}
      {toast && (
        <div className={`card-base rounded-xl p-3 flex items-center justify-between border ${
          toast.type === 'success' ? 'border-[#00A34D]/20 bg-[#E3FCEF]' : 'border-[#E65C5C]/20 bg-[#FDECEC]'
        }`}>
          <p className={`text-sm font-medium ${toast.type === 'success' ? 'text-[#00A34D]' : 'text-[#E65C5C]'}`}>{toast.message}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[0.7fr_2.3fr] gap-6">
        <div>
          <ProviderSidebar
            providers={providers}
            selectedProvider={selectedProvider}
            modelsCount={modelsCount}
            onSelect={setSelectedProvider}
            onAddProvider={() => setAddProviderOpen(true)}
          />
        </div>
        <div>
          <ProviderModelsPanel
            provider={currentProvider}
            models={models}
            onEdit={() => setEditModalOpen(true)}
            onSaveKey={handleSaveKey}
            isSaving={isSavingProviders}
            onCheckHealth={checkProviderHealth}
            isCheckingHealth={isCheckingHealth[currentProvider?.name || ''] || false}
            onAddModel={() => setAddModelOpen(true)}
          />
        </div>
      </div>

      <ProviderEditModal
        provider={currentProvider}
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        onSave={handleSave}
        isSaving={isSavingProviders}
      />
      <AddProviderModal
        isOpen={addProviderOpen}
        onClose={() => setAddProviderOpen(false)}
        onSubmit={(data) => { createProvider(data); setAddProviderOpen(false) }}
        isSaving={isSavingProviders}
      />
      <AddModelModal
        providerName={currentProvider?.name || ''}
        isOpen={addModelOpen}
        onClose={() => setAddModelOpen(false)}
        onSubmit={(data) => { addModel(currentProvider!.name, data); setAddModelOpen(false) }}
        isSaving={isLoading}
      />
    </div>
  )
}
