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
}

export function ProviderModelsPanel({ provider, models, onEdit }: ProviderModelsPanelProps) {
  if (!provider) {
    return (
      <div className="glass-card rounded-2xl p-8 flex items-center justify-center min-h-[300px]">
        <p className="text-[#a1a1a6]">请选择一个 Provider</p>
      </div>
    )
  }

  const providerModels = models.filter((m) => m.provider === provider.name)

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <div className="p-4 border-b border-[rgba(0,0,0,0.06)] flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#1d1d1f]">{provider.name}</h2>
          <p className="text-xs text-[#a1a1a6] font-mono mt-0.5">{providerModels.length} 个模型</p>
        </div>
        <button
          onClick={onEdit}
          className="px-4 py-2 bg-[rgba(0,122,255,0.08)] text-[#007AFF] border border-[rgba(0,122,255,0.15)] rounded-xl hover:bg-[rgba(0,122,255,0.12)] text-sm font-medium transition-all"
        >
          编辑配置
        </button>
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
              {providerModels.map((model) => (
                <tr key={model.name} className="table-row-hover">
                  <td className="px-4 py-3 font-medium text-[#1d1d1f]">{model.name}</td>
                  <td className="px-4 py-3">
                    {model.available ? (
                      <span className="inline-flex items-center gap-1.5 text-[#34C759] text-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#34C759] pulse-glow" />在线
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-[#FF3B30] text-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#FF3B30] pulse-glow-red" />离线
                      </span>
                    )}
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
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
