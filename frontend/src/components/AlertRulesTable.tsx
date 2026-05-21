import { useState } from 'react'
import { useTranslation } from '../i18n/I18nProvider'
import { useDashboardStore } from '../store/useDashboardStore'
import type { AlertRule } from '../types'

interface AlertRulesTableProps {
  onEdit: (rule: AlertRule) => void
}

export function AlertRulesTable({ onEdit }: AlertRulesTableProps) {
  const { t } = useTranslation()
  const { alertRules, isLoadingAlerts, updateAlertRule, deleteAlertRule } = useDashboardStore()
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const handleToggle = async (rule: AlertRule) => {
    await updateAlertRule(rule.id, { enabled: !rule.enabled })
  }

  const handleDelete = async (id: string) => {
    if (!confirm(t('Delete this alert rule?'))) return
    setDeletingId(id)
    await deleteAlertRule(id)
    setDeletingId(null)
  }

  if (isLoadingAlerts && alertRules.length === 0) {
    return (
      <div className="card-base rounded-xl p-8 text-center">
        <p className="text-sm text-[#889397]">{t('LOADING...')}</p>
      </div>
    )
  }

  return (
    <div className="card-base rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#E8EDEB]">
              <th className="text-left text-[10px] text-[#889397] font-medium px-6 py-3">{t('NAME')}</th>
              <th className="text-left text-[10px] text-[#889397] font-medium px-6 py-3">{t('METRIC')}</th>
              <th className="text-left text-[10px] text-[#889397] font-medium px-6 py-3">{t('CONDITION')}</th>
              <th className="text-left text-[10px] text-[#889397] font-medium px-6 py-3">{t('SEVERITY')}</th>
              <th className="text-left text-[10px] text-[#889397] font-medium px-6 py-3">{t('STATUS')}</th>
              <th className="text-right text-[10px] text-[#889397] font-medium px-6 py-3">{t('ACTIONS')}</th>
            </tr>
          </thead>
          <tbody>
            {alertRules.map((rule) => (
              <tr key={rule.id} className="data-row border-b border-[#E8EDEB] last:border-0">
                <td className="px-6 py-4">
                  <div className="font-medium text-[#001E2B]">{rule.name}</div>
                  <div className="text-xs text-[#889397]">{rule.id}</div>
                </td>
                <td className="px-6 py-4 text-[#001E2B]">{rule.condition.metric}</td>
                <td className="px-6 py-4 text-[#001E2B]">
                  {rule.condition.operator} {rule.condition.threshold}
                </td>
                <td className="px-6 py-4">
                  <span className={`tech-tag ${
                    rule.severity === 'critical'
                      ? 'tech-tag-danger'
                      : rule.severity === 'warning'
                      ? 'tech-tag-warning'
                      : 'bg-[rgba(47,135,252,0.1)] border-[rgba(47,135,252,0.2)] text-[#2F87FC]'
                  }`}>
                    {rule.severity}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <button
                    onClick={() => handleToggle(rule)}
                    className={`relative inline-flex h-5 w-9 items-center rounded-lg transition-colors ${
                      rule.enabled ? 'bg-[#00A34D]' : 'bg-[#E8EDEB]'
                    }`}
                  >
                    <span
                      className={`inline-block h-3.5 w-3.5 transform rounded-lg bg-white transition-transform ${
                        rule.enabled ? 'translate-x-5' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={() => onEdit(rule)}
                    className="text-[#00A34D] hover:text-[#00A34D]/70 text-xs font-medium mr-3"
                  >
                    {t('EDIT')}
                  </button>
                  <button
                    onClick={() => handleDelete(rule.id)}
                    disabled={deletingId === rule.id}
                    className="text-[#E65C5C] hover:text-[#E65C5C]/70 text-xs font-medium disabled:opacity-50"
                  >
                    {deletingId === rule.id ? t('DELETING...') : t('DELETE')}
                  </button>
                </td>
              </tr>
            ))}
            {alertRules.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-sm text-[#889397]">
                  {t('NO ALERT RULES')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
