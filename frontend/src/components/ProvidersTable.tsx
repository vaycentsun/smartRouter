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
      className={`inline-block w-2.5 h-2.5 rounded-full ${hasKey ? 'bg-green-500' : 'bg-red-500'}`}
      title={hasKey ? 'Key 已配置' : 'Key 缺失'}
    />
  )
}

export function ProvidersTable() {
  const { providers, saveProviders, isSavingProviders, toast, clearToast } = useDashboardStore()
  const [edits, setEdits] = useState<Record<string, EditableProvider>>({})
  const [hasChanges, setHasChanges] = useState(false)

  // Initialize edits from providers data
  useEffect(() => {
    const initial: Record<string, EditableProvider> = {}
    providers.forEach((p) => {
      initial[p.name] = {
        api_base: p.api_base,
        api_key: p.key_type.startsWith('env:')
          ? `os.environ/${p.key_type.replace('env:', '')}`
          : '', // direct key not exposed by GET for security
        timeout: p.timeout,
        showKey: false,
        dirty: false,
      }
    })
    setEdits(initial)
  }, [providers])

  // Check if any provider is dirty
  useEffect(() => {
    const dirty = Object.values(edits).some((e) => e.dirty)
    setHasChanges(dirty)
  }, [edits])

  // Auto clear toast after 3s
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
        // Only send api_key if it has a value; avoids overwriting a direct key
        // that we don't know (GET never exposes real direct keys)
        if (edit.api_key.trim()) {
          entry.api_key = edit.api_key
        }
        payload[name] = entry
      }
    })
    if (Object.keys(payload).length === 0) return
    await saveProviders(payload)
    // Mark all as clean after save attempt
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
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Provider 配置</h2>
        <p className="text-gray-500 text-sm">暂无 Provider 数据</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Provider 配置</h2>
        <div className="flex items-center gap-3">
          {toast && (
            <span
              className={`text-sm px-3 py-1 rounded ${toast.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}
            >
              {toast.message}
            </span>
          )}
          <button
            onClick={handleSave}
            disabled={!hasChanges || isSavingProviders}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              hasChanges && !isSavingProviders
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            {isSavingProviders ? '保存中...' : '保存所有修改'}
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-50 text-gray-700">
            <tr>
              <th className="px-4 py-3 font-medium w-10">状态</th>
              <th className="px-4 py-3 font-medium">名称</th>
              <th className="px-4 py-3 font-medium">API Base</th>
              <th className="px-4 py-3 font-medium">API Key</th>
              <th className="px-4 py-3 font-medium w-24">Timeout</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {providers.map((provider) => {
              const edit = edits[provider.name]
              if (!edit) return null
              return (
                <tr
                  key={provider.name}
                  className={`hover:bg-gray-50 ${edit.dirty ? 'bg-yellow-50/50' : ''}`}
                >
                  <td className="px-4 py-3">
                    <StatusDot hasKey={provider.has_key} />
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-900">{provider.name}</td>
                  <td className="px-4 py-3">
                    <input
                      type="text"
                      value={edit.api_base}
                      onChange={(e) => handleChange(provider.name, 'api_base', e.target.value)}
                      className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <input
                        type={edit.showKey ? 'text' : 'password'}
                        value={edit.api_key}
                        onChange={(e) => handleChange(provider.name, 'api_key', e.target.value)}
                        className="flex-1 min-w-0 px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                      <button
                        type="button"
                        onClick={() => handleChange(provider.name, 'showKey', !edit.showKey)}
                        className="text-gray-400 hover:text-gray-600 text-xs px-1"
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
                      className="w-20 px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
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
