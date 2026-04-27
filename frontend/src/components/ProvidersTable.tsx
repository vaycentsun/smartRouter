import { useState, useEffect } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'

interface EditableProvider {
  api_base: string
  api_key: string
  timeout: number
  showKey: boolean
  dirty: boolean
}

function StatusDot({ hasKey }: { hasKey: boolean }) {
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${
        hasKey ? 'bg-emerald-400 pulse-glow' : 'bg-red-400 pulse-glow-red'
      }`}
      title={hasKey ? 'Key 已配置' : 'Key 缺失'}
    />
  )
}

export function ProvidersTable() {
  const { providers, saveProviders, isSavingProviders, toast, clearToast } = useDashboardStore()
  const [edits, setEdits] = useState<Record<string, EditableProvider>>({})
  const [hasChanges, setHasChanges] = useState(false)

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
      }
    })
    setEdits(initial)
  }, [providers])

  useEffect(() => {
    const dirty = Object.values(edits).some((e) => e.dirty)
    setHasChanges(dirty)
  }, [edits])

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
        if (edit.api_key.trim()) {
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
        next[name] = { ...edit, dirty: false }
      })
      return next
    })
  }

  if (providers.length === 0) {
    return (
      <div className="glass-card rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1 h-5 bg-violet-400 rounded-full" />
          <h2 className="text-base font-semibold text-slate-100 tracking-wide">Provider 配置</h2>
        </div>
        <p className="text-slate-500 text-sm">暂无 Provider 数据</p>
      </div>
    )
  }

  return (
    <div className="glass-card rounded-xl">
      <div className="p-4 border-b border-cyan-400/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-1 h-5 bg-violet-400 rounded-full" />
          <h2 className="text-base font-semibold text-slate-100 tracking-wide">Provider 配置</h2>
        </div>
        <div className="flex items-center gap-3">
          {toast && (
            <span
              className={`text-xs px-3 py-1 rounded-full font-mono ${
                toast.type === 'success'
                  ? 'bg-emerald-400/10 text-emerald-300 border border-emerald-400/20'
                  : 'bg-red-400/10 text-red-300 border border-red-400/20'
              }`}
            >
              {toast.message}
            </span>
          )}
          <button
            onClick={handleSave}
            disabled={!hasChanges || isSavingProviders}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              hasChanges && !isSavingProviders
                ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-400/30 hover:bg-cyan-500/20 hover:border-cyan-400/50 hover:shadow-lg hover:shadow-cyan-400/10'
                : 'bg-slate-700/30 text-slate-600 border border-slate-600/20 cursor-not-allowed'
            }`}
          >
            {isSavingProviders ? '保存中...' : '保存所有修改'}
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-800/40 text-slate-400">
            <tr>
              <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider w-10">状态</th>
              <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">名称</th>
              <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">API Base</th>
              <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">API Key</th>
              <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider w-24">Timeout</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/20">
            {providers.map((provider) => {
              const edit = edits[provider.name]
              if (!edit) return null
              return (
                <tr
                  key={provider.name}
                  className={`table-row-hover ${edit.dirty ? 'bg-cyan-400/5' : ''}`}
                >
                  <td className="px-4 py-3">
                    <StatusDot hasKey={provider.has_key} />
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-200">{provider.name}</td>
                  <td className="px-4 py-3">
                    <input
                      type="text"
                      value={edit.api_base}
                      onChange={(e) => handleChange(provider.name, 'api_base', e.target.value)}
                      className="w-full px-2 py-1 rounded text-sm text-slate-200 input-glow"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <input
                        type={edit.showKey ? 'text' : 'password'}
                        value={edit.api_key}
                        onChange={(e) => handleChange(provider.name, 'api_key', e.target.value)}
                        className="flex-1 min-w-0 px-2 py-1 rounded text-sm text-slate-200 input-glow"
                      />
                      <button
                        type="button"
                        onClick={() => handleChange(provider.name, 'showKey', !edit.showKey)}
                        className="text-slate-500 hover:text-cyan-400 text-xs px-1 transition-colors"
                        title={edit.showKey ? '隐藏' : '显示'}
                      >
                        {edit.showKey ? '🙈' : '👁'}
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="number"
                      value={edit.timeout}
                      onChange={(e) => handleChange(provider.name, 'timeout', parseInt(e.target.value) || 30)}
                      className="w-20 px-2 py-1 rounded text-sm text-slate-200 input-glow"
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
