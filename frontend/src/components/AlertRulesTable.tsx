import { useState } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import type { AlertRule } from '../types'

interface AlertRulesTableProps {
  onEdit: (rule: AlertRule) => void
}

export function AlertRulesTable({ onEdit }: AlertRulesTableProps) {
  const { alertRules, isLoadingAlerts, updateAlertRule, deleteAlertRule } = useDashboardStore()
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const handleToggle = async (rule: AlertRule) => {
    await updateAlertRule(rule.id, { enabled: !rule.enabled })
  }

  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除这条告警规则吗？')) return
    setDeletingId(id)
    await deleteAlertRule(id)
    setDeletingId(null)
  }

  if (isLoadingAlerts && alertRules.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-8 text-center">
        <p className="text-sm text-[#86868b]">加载中...</p>
      </div>
    )
  }

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-black/5">
              <th className="text-left font-medium text-[#86868b] px-6 py-3">名称</th>
              <th className="text-left font-medium text-[#86868b] px-6 py-3">指标</th>
              <th className="text-left font-medium text-[#86868b] px-6 py-3">条件</th>
              <th className="text-left font-medium text-[#86868b] px-6 py-3">严重级别</th>
              <th className="text-left font-medium text-[#86868b] px-6 py-3">状态</th>
              <th className="text-right font-medium text-[#86868b] px-6 py-3">操作</th>
            </tr>
          </thead>
          <tbody>
            {alertRules.map((rule) => (
              <tr key={rule.id} className="border-b border-black/5 last:border-0 hover:bg-[rgba(0,0,0,0.02)]">
                <td className="px-6 py-4">
                  <div className="font-medium text-[#1d1d1f]">{rule.name}</div>
                  <div className="text-xs text-[#86868b]">{rule.id}</div>
                </td>
                <td className="px-6 py-4 text-[#1d1d1f]">{rule.condition.metric}</td>
                <td className="px-6 py-4 text-[#1d1d1f]">
                  {rule.condition.operator} {rule.condition.threshold}
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    rule.severity === 'critical'
                      ? 'bg-red-100 text-red-700'
                      : rule.severity === 'warning'
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-blue-100 text-blue-700'
                  }`}>
                    {rule.severity}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <button
                    onClick={() => handleToggle(rule)}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                      rule.enabled ? 'bg-[#007AFF]' : 'bg-[#d1d1d6]'
                    }`}
                  >
                    <span
                      className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                        rule.enabled ? 'translate-x-5' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={() => onEdit(rule)}
                    className="text-[#007AFF] hover:text-[#007AFF]/70 text-xs font-medium mr-3"
                  >
                    编辑
                  </button>
                  <button
                    onClick={() => handleDelete(rule.id)}
                    disabled={deletingId === rule.id}
                    className="text-[#FF3B30] hover:text-[#FF3B30]/70 text-xs font-medium disabled:opacity-50"
                  >
                    {deletingId === rule.id ? '删除中...' : '删除'}
                  </button>
                </td>
              </tr>
            ))}
            {alertRules.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-sm text-[#86868b]">
                  暂无告警规则
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
