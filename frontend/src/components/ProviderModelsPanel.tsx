import { useState } from 'react'
import type { ModelInfo, ProviderInfo } from '../types'

function TaskBadge({ task }: { task: string }) {
  return (
    <span className="inline-block px-2 py-0.5 bg-[rgba(0,122,255,0.06)] text-[#007AFF]/80 text-xs rounded border border-[rgba(0,122,255,0.12)] mr-1">
      {task}
    </span>
  )
}

function StarRating({ value, colorClass }: { value: number; colorClass: string }) {
  const filled = Math.floor(value / 2)
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={`text-xs ${i < filled ? colorClass : 'text-[rgba(0,0,0,0.08)]'}`}>★</span>
      ))}
    </div>
  )
}

interface ProviderModelsPanelProps {
  provider: ProviderInfo | null
  models: ModelInfo[]
  onEdit: () => void
  onSaveKey: (apiKey: string) => void
  isSaving: boolean
  onCheckHealth?: (providerName: string) => Promise<void>
  isCheckingHealth?: boolean
}

const healthStatusMap: Record<string, { label: string; color: string; dotColor: string; tooltip: string }> = {
  available: { label: '可用', color: 'text-[#34C759]', dotColor: 'bg-[#34C759]', tooltip: '该模型在 Provider 端确认可用' },
  not_found: { label: '未上架', color: 'text-[#FF9500]', dotColor: 'bg-[#FF9500]', tooltip: 'Provider 返回的模型列表中未找到此模型' },
  unconfigured: { label: '未配置', color: 'text-[#86868b]', dotColor: 'bg-[#86868b]', tooltip: 'API Key 未配置' },
  auth_error: { label: 'Key 无效', color: 'text-[#FF3B30]', dotColor: 'bg-[#FF3B30]', tooltip: 'API Key 无效或权限不足' },
  rate_limited: { label: '频率限制', color: 'text-[#FF9500]', dotColor: 'bg-[#FF9500]', tooltip: '请求频率超限' },
  network_error: { label: '网络异常', color: 'text-[#FF3B30]', dotColor: 'bg-[#FF3B30]', tooltip: '网络连接失败' },
  unknown: { label: '检查失败', color: 'text-[#FF3B30]', dotColor: 'bg-[#FF3B30]', tooltip: '健康检查失败' },
  checking: { label: '检测中...', color: 'text-[#007AFF]', dotColor: 'bg-[#007AFF]', tooltip: '正在检测 Provider 连通性' },
}

function getModelHealthDisplay(model: ModelInfo, providerHealth?: { status: string; error?: string | null }) {
  const status = model.health_status

  // 如果正在检查中
  if (providerHealth?.status === 'checking' || status === 'checking') {
    return healthStatusMap.checking
  }

  // 优先使用模型级的 health_status
  if (status && healthStatusMap[status]) {
    const mapping = healthStatusMap[status]
    // 如果有具体的错误信息，追加到 tooltip
    if (providerHealth?.error && status !== 'available' && status !== 'not_found') {
      return { ...mapping, tooltip: providerHealth.error }
    }
    return mapping
  }

  // 兜底：按 available 字段显示旧状态
  if (model.available) {
    return { label: '已配置', color: 'text-[#34C759]', dotColor: 'bg-[#34C759]', tooltip: 'API Key 已配置（尚未检查连通性）' }
  }
  return { label: '未配置', color: 'text-[#86868b]', dotColor: 'bg-[#86868b]', tooltip: 'API Key 未配置' }
}

export function ProviderModelsPanel({
  provider,
  models,
  onEdit,
  onSaveKey,
  isSaving,
  onCheckHealth,
  isCheckingHealth = false,
}: ProviderModelsPanelProps) {
  const [keyInput, setKeyInput] = useState('')
  const [showKey, setShowKey] = useState(false)
  if (!provider) {
    return (
      <div className="glass-card rounded-2xl p-8 flex items-center justify-center min-h-[300px]">
        <p className="text-[#a1a1a6]">请选择一个 Provider</p>
      </div>
    )
  }

  const providerModels = models.filter((m) => m.provider === provider.name)
  const providerHealth = provider.health

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <div className="p-4 border-b border-[rgba(0,0,0,0.06)] flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#1d1d1f]">{provider.name}</h2>
          <p className="text-xs text-[#a1a1a6] font-mono mt-0.5">{providerModels.length} 个模型</p>
        </div>
        <div className="flex items-center gap-2">
          {onCheckHealth && (
            <button
              onClick={() => onCheckHealth(provider.name)}
              disabled={isCheckingHealth}
              className="px-3 py-2 bg-[rgba(0,122,255,0.08)] text-[#007AFF] border border-[rgba(0,122,255,0.15)] rounded-xl hover:bg-[rgba(0,122,255,0.12)] text-sm font-medium transition-all disabled:opacity-50 flex items-center gap-1.5"
            >
              {isCheckingHealth ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-[#007AFF] border-t-transparent rounded-full animate-spin" />
                  检测中...
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  检查连通性
                </>
              )}
            </button>
          )}
          <button
            onClick={onEdit}
            className="px-4 py-2 bg-[rgba(0,122,255,0.08)] text-[#007AFF] border border-[rgba(0,122,255,0.15)] rounded-xl hover:bg-[rgba(0,122,255,0.12)] text-sm font-medium transition-all"
          >
            编辑配置
          </button>
        </div>
      </div>

      {/* API Key 编辑区域 */}
      <div className="px-4 py-3 border-b border-[rgba(0,0,0,0.06)] bg-[rgba(0,0,0,0.015)]">
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-[#86868b] uppercase tracking-wider whitespace-nowrap">
            API Key
          </span>
          {provider.key_type.startsWith('env:') ? (
            <span className="text-sm text-[#a1a1a6]">
              通过环境变量配置（{provider.key_type}）
            </span>
          ) : (
            <>
              <div className="flex-1 flex items-center gap-2">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={keyInput}
                  placeholder={provider.masked_key || '未设置'}
                  onChange={(e) => setKeyInput(e.target.value)}
                  className="flex-1 min-w-0 px-3 py-1.5 rounded-xl text-sm text-[#1d1d1f] input-glow placeholder-[#a1a1a6]"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="text-[#a1a1a6] hover:text-[#007AFF] text-xs px-2 transition-colors"
                  title={showKey ? '隐藏' : '显示'}
                >
                  {showKey ? '🙈' : '👁'}
                </button>
              </div>
              <button
                onClick={() => { onSaveKey(keyInput); setKeyInput('') }}
                disabled={isSaving}
                className="px-3 py-1.5 bg-[#007AFF] text-white rounded-xl text-sm font-medium hover:bg-[#0051D5] disabled:opacity-50 transition-all whitespace-nowrap"
              >
                {isSaving ? '保存中...' : '保存'}
              </button>
            </>
          )}
        </div>
        {!provider.key_type.startsWith('env:') && (
          <p className="text-xs text-[#a1a1a6] mt-1.5">
            {provider.has_key ? '输入新值覆盖当前 Key，留空保存表示删除' : '输入 Key 并保存以启用该 Provider'}
          </p>
        )}
      </div>

      {providerModels.length === 0 ? (
        <div className="p-8 text-center text-[#a1a1a6]">
          该 Provider 暂无模型数据
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-[rgba(0,0,0,0.02)] text-[#86868b]">
              <tr>
                <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">模型名称</th>
                <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">状态</th>
                <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">Quality</th>
                <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">Cost</th>
                <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">Context</th>
                <th className="px-4 py-3 font-mono text-xs uppercase tracking-wider">支持任务</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(0,0,0,0.04)]">
              {providerModels.map((model) => {
                const display = getModelHealthDisplay(model, providerHealth)
                return (
                  <tr key={model.name} className="table-row-hover">
                    <td className="px-4 py-3 font-medium text-[#1d1d1f]">{model.name}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 ${display.color} text-sm cursor-help`}
                        title={display.tooltip}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${display.dotColor} ${display.label === '检测中...' ? 'animate-pulse' : ''}`} />
                        {display.label}
                      </span>
                    </td>
                    <td className="px-4 py-3"><StarRating value={model.quality} colorClass="text-[#FF9500]" /></td>
                    <td className="px-4 py-3"><StarRating value={model.cost} colorClass="text-[#FF9500]" /></td>
                    <td className="px-4 py-3 text-[#86868b] font-mono text-xs">
                      {model.context >= 1000 ? `${Math.floor(model.context / 1000)}k` : model.context}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {model.supported_tasks.slice(0, 3).map((task) => (
                          <TaskBadge key={task} task={task} />
                        ))}
                        {model.supported_tasks.length > 3 && (
                          <span className="text-xs text-[#a1a1a6]">+{model.supported_tasks.length - 3}</span>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
