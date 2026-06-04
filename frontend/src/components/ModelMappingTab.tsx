import { useState, useEffect } from 'react'
import { useTranslation } from '../i18n/I18nProvider'
import { api } from '../api/client'
import type { ModelMappingConfig, ModelMappingRule } from '../types'

const EMPTY_RULE: ModelMappingRule = {
  id: '',
  enabled: true,
  from_model: '',
  to_provider: '',
  to_model: '',
  to_litellm_provider: '',
  to_base_url: '',
  to_api_key: '',
}

function ToggleSwitch({ checked, onChange, disabled = false }: { checked: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <label className="relative inline-flex items-center cursor-pointer">
      <input
        type="checkbox"
        className="sr-only peer"
        checked={checked}
        onChange={onChange}
        disabled={disabled}
      />
      <div className={`w-9 h-5 rounded-sm peer relative border transition-all ${checked ? 'bg-[rgba(0,212,170,0.15)] border-[rgba(0,212,170,0.3)]' : 'bg-[#1a1a2e] border-[#2a2a3e]'} ${disabled ? 'opacity-50' : ''}`}>
        <div className={`absolute top-[2px] left-[2px] w-4 h-4 rounded-sm transition-all ${checked ? 'translate-x-4 bg-[#00d4aa]' : 'bg-[#636366]'}`} />
      </div>
    </label>
  )
}

interface RuleFormModalProps {
  rule: ModelMappingRule | null
  onClose: () => void
  onSave: (rule: ModelMappingRule) => void
}

function RuleFormModal({ rule, onClose, onSave }: RuleFormModalProps) {
  const { t } = useTranslation()
  const isEditing = !!rule
  const [form, setForm] = useState<ModelMappingRule>(rule ? { ...rule } : { ...EMPTY_RULE })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(form)
  }

  const updateField = (field: keyof ModelMappingRule, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="tech-card rounded-sm w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-1 h-4 bg-[#00d4aa]" />
            <h3 className="text-lg font-semibold text-[#e8e8ed] uppercase tracking-wider font-mono">
              {isEditing ? t('Edit Mapping') : t('Add Mapping')}
            </h3>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">{t('From Model')}</label>
                <input
                  type="text"
                  value={form.from_model}
                  onChange={(e) => updateField('from_model', e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm text-[#e8e8ed] focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
                  placeholder="gpt-4"
                />
              </div>
              <div>
                <label className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">{t('To Model')}</label>
                <input
                  type="text"
                  value={form.to_model}
                  onChange={(e) => updateField('to_model', e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm text-[#e8e8ed] focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
                  placeholder="claude-3-opus"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">{t('To Provider')}</label>
                <input
                  type="text"
                  value={form.to_provider}
                  onChange={(e) => updateField('to_provider', e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm text-[#e8e8ed] focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
                  placeholder="anthropic"
                />
              </div>
              <div>
                <label className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">LiteLLM Provider</label>
                <input
                  type="text"
                  value={form.to_litellm_provider}
                  onChange={(e) => updateField('to_litellm_provider', e.target.value)}
                  className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm text-[#e8e8ed] focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
                  placeholder="anthropic"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">{t('To Base URL')}</label>
              <input
                type="text"
                value={form.to_base_url}
                onChange={(e) => updateField('to_base_url', e.target.value)}
                className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm text-[#e8e8ed] focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
                placeholder="https://api.anthropic.com/v1"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">{t('To API Key')}</label>
              <input
                type="text"
                value={form.to_api_key}
                onChange={(e) => updateField('to_api_key', e.target.value)}
                className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm text-[#e8e8ed] focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
                placeholder="sk-... or os.environ/KEY_NAME"
              />
            </div>
            <div className="flex items-center gap-3 pt-2">
              <ToggleSwitch checked={form.enabled} onChange={() => updateField('enabled', !form.enabled)} />
              <span className="text-sm text-[#e8e8ed] font-mono">{t('ENABLED')}</span>
            </div>
            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                className="px-5 py-2 rounded-sm tech-btn-primary text-xs font-mono uppercase tracking-wider"
              >
                {t('SAVE')}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2 rounded-sm tech-btn text-xs font-mono uppercase tracking-wider"
              >
                {t('CANCEL')}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export function ModelMappingTab() {
  const [config, setConfig] = useState<ModelMappingConfig>({ enabled: false, mappings: [] })
  const [viewMode, setViewMode] = useState<'table' | 'yaml'>('table')
  const [yamlText, setYamlText] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingRule, setEditingRule] = useState<ModelMappingRule | null>(null)
  const { t } = useTranslation()

  useEffect(() => {
    let cancelled = false

    const loadData = async () => {
      setLoading(true)
      setError(null)
      try {
        const [configData, yamlData] = await Promise.all([
          api.getModelMappings(),
          api.getModelMappingsYaml(),
        ])
        if (!cancelled) {
          setConfig(configData)
          setYamlText(yamlData.yaml)
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(`${t('LOAD FAILED')}: ${err.message}`)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadData()

    return () => {
      cancelled = true
    }
  }, [t])

  const fetchConfig = async () => {
    const data = await api.getModelMappings()
    setConfig(data)
  }

  const fetchYaml = async () => {
    const data = await api.getModelMappingsYaml()
    setYamlText(data.yaml)
  }

  const saveConfig = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.updateModelMappings(config)
      if (result.success) {
        await fetchConfig()
        await fetchYaml()
      } else {
        setError(t('SAVE FAILED'))
      }
    } catch (err: any) {
      setError(`${t('SAVE FAILED')}: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const saveYaml = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.updateModelMappingsYaml(yamlText)
      if (result.success) {
        await fetchConfig()
        await fetchYaml()
      } else {
        setError(t('SAVE FAILED'))
      }
    } catch (err: any) {
      setError(`${t('SAVE FAILED')}: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleRule = (id: string, enabled: boolean) => {
    setConfig((prev) => ({
      ...prev,
      mappings: prev.mappings.map((m) => (m.id === id ? { ...m, enabled } : m)),
    }))
  }

  const handleDeleteRule = (id: string) => {
    setConfig((prev) => ({
      ...prev,
      mappings: prev.mappings.filter((m) => m.id !== id),
    }))
  }

  const handleSaveRule = (rule: ModelMappingRule) => {
    setConfig((prev) => {
      const exists = prev.mappings.find((m) => m.id === rule.id)
      if (exists) {
        return {
          ...prev,
          mappings: prev.mappings.map((m) => (m.id === rule.id ? rule : m)),
        }
      }
      return {
        ...prev,
        mappings: [...prev.mappings, { ...rule, id: rule.id || `rule-${Date.now()}` }],
      }
    })
    setShowForm(false)
    setEditingRule(null)
  }

  const openAddForm = () => {
    setEditingRule(null)
    setShowForm(true)
  }

  const openEditForm = (rule: ModelMappingRule) => {
    setEditingRule(rule)
    setShowForm(true)
  }

  const closeForm = () => {
    setShowForm(false)
    setEditingRule(null)
  }

  const handleToggleGlobal = () => {
    setConfig((prev) => ({ ...prev, enabled: !prev.enabled }))
  }

  return (
    <div className="space-y-4">
      {/* 说明提示 */}
      <div className="tech-card rounded-sm p-3 border border-[rgba(0,212,170,0.15)]">
        <p className="text-xs font-mono text-[#636366]">
          <span className="text-[#00d4aa]">ℹ</span> {t('Mapping applies to both chat/completions and responses endpoints')}
        </p>
      </div>

      {/* 全局开关 + 视图切换 */}
      <div className="tech-card rounded-sm p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ToggleSwitch checked={config.enabled} onChange={handleToggleGlobal} disabled={loading} />
          <span className="text-sm text-[#e8e8ed] font-mono">{t('Global Enabled')}</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setViewMode('table')}
            className={`px-3 py-1.5 rounded-sm text-xs font-mono uppercase tracking-wider transition-all ${
              viewMode === 'table' ? 'tech-tab-active' : 'tech-tab'
            }`}
          >
            {t('Table View')}
          </button>
          <button
            onClick={() => setViewMode('yaml')}
            className={`px-3 py-1.5 rounded-sm text-xs font-mono uppercase tracking-wider transition-all ${
              viewMode === 'yaml' ? 'tech-tab-active' : 'tech-tab'
            }`}
          >
            {t('YAML Editor')}
          </button>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="tech-card rounded-sm p-4 flex items-center justify-between border border-[rgba(231,76,60,0.2)]">
          <p className="text-sm font-mono text-[#e74c3c]">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-sm text-[#636366] hover:text-[#e8e8ed] transition-colors font-mono uppercase"
          >
            {t('DISMISS')}
          </button>
        </div>
      )}

      {/* 表格视图 */}
      {viewMode === 'table' && (
        <div className="tech-card rounded-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-[#0a0a0f] text-[#636366]">
                <tr>
                  <th className="px-4 py-3 text-[10px] text-[#636366] font-mono uppercase tracking-widest">{t('From Model')}</th>
                  <th className="px-4 py-3 text-[10px] text-[#636366] font-mono uppercase tracking-widest">{t('To Model')}</th>
                  <th className="px-4 py-3 text-[10px] text-[#636366] font-mono uppercase tracking-widest">{t('To Provider')}</th>
                  <th className="px-4 py-3 text-[10px] text-[#636366] font-mono uppercase tracking-widest">{t('To Base URL')}</th>
                  <th className="px-4 py-3 text-[10px] text-[#636366] font-mono uppercase tracking-widest w-20">{t('ENABLED')}</th>
                  <th className="px-4 py-3 text-[10px] text-[#636366] font-mono uppercase tracking-widest w-28">{t('ACTIONS')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1a1a2e]">
                {loading && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-[#636366] font-mono">
                      {t('LOADING')}
                    </td>
                  </tr>
                )}
                {!loading && config.mappings.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-[#636366] font-mono">
                      {t('No mappings configured')}
                    </td>
                  </tr>
                )}
                {!loading && config.mappings.map((rule) => (
                  <tr key={rule.id} className="data-row">
                    <td className="px-4 py-3 font-medium text-[#e8e8ed] font-mono text-xs">{rule.from_model}</td>
                    <td className="px-4 py-3 text-[#e8e8ed] font-mono text-xs">{rule.to_model}</td>
                    <td className="px-4 py-3 text-[#636366] font-mono text-xs">{rule.to_provider}</td>
                    <td className="px-4 py-3 text-[#636366] font-mono text-xs max-w-[200px] truncate">{rule.to_base_url}</td>
                    <td className="px-4 py-3">
                      <ToggleSwitch checked={rule.enabled} onChange={() => handleToggleRule(rule.id, !rule.enabled)} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEditForm(rule)}
                          className="text-[#00d4aa] hover:text-[#00d4aa]/70 text-xs font-mono uppercase tracking-wider"
                        >
                          {t('EDIT')}
                        </button>
                        <button
                          onClick={() => handleDeleteRule(rule.id)}
                          className="text-[#e74c3c] hover:text-[#e74c3c]/70 text-xs font-mono uppercase tracking-wider"
                        >
                          {t('DELETE')}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="p-4 border-t border-[#1a1a2e] flex items-center justify-between">
            <button
              onClick={openAddForm}
              className="tech-btn tech-btn-primary px-4 py-2 rounded-sm text-xs font-mono uppercase tracking-wider"
            >
              + {t('Add Mapping')}
            </button>
            <button
              onClick={saveConfig}
              disabled={loading}
              className={`px-5 py-2 rounded-sm text-xs font-mono uppercase tracking-wider ${
                loading ? 'tech-btn opacity-50 cursor-not-allowed' : 'tech-btn tech-btn-primary'
              }`}
            >
              {loading ? t('SAVING') : t('SAVE')}
            </button>
          </div>
        </div>
      )}

      {/* YAML 视图 */}
      {viewMode === 'yaml' && (
        <div className="tech-card rounded-sm p-4 space-y-4">
          <textarea
            value={yamlText}
            onChange={(e) => setYamlText(e.target.value)}
            className="w-full min-h-[400px] bg-[#111118] border border-[#1a1a2e] rounded-sm px-3 py-2 text-xs text-[#e0e0e0] font-mono focus:outline-none focus:border-[#00d4aa] resize-y"
            spellCheck={false}
          />
          <div className="flex justify-end">
            <button
              onClick={saveYaml}
              disabled={loading}
              className={`px-5 py-2 rounded-sm text-xs font-mono uppercase tracking-wider ${
                loading ? 'tech-btn opacity-50 cursor-not-allowed' : 'tech-btn tech-btn-primary'
              }`}
            >
              {loading ? t('SAVING') : t('SAVE')}
            </button>
          </div>
        </div>
      )}

      {/* 模态框 */}
      {showForm && (
        <RuleFormModal
          rule={editingRule}
          onClose={closeForm}
          onSave={handleSaveRule}
        />
      )}
    </div>
  )
}
