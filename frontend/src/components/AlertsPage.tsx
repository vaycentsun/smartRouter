import { useEffect, useState } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import { AlertSummaryCard } from './AlertSummaryCard'
import { AlertRulesTable } from './AlertRulesTable'
import { AlertRuleEditor } from './AlertRuleEditor'
import { AlertHistoryTable } from './AlertHistoryTable'
import type { AlertRule } from '../types'

export function AlertsPage() {
  const { alertsError, fetchAlertRules, fetchAlertHistory, clearAlertsError } = useDashboardStore()
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null)
  const [showEditor, setShowEditor] = useState(false)

  useEffect(() => {
    fetchAlertRules()
    fetchAlertHistory()
  }, [fetchAlertRules, fetchAlertHistory])

  const handleEdit = (rule: AlertRule) => {
    setEditingRule(rule)
    setShowEditor(true)
  }

  const handleNew = () => {
    setEditingRule(null)
    setShowEditor(true)
  }

  const handleCloseEditor = () => {
    setShowEditor(false)
    setEditingRule(null)
  }

  return (
    <div className="space-y-6">
      {alertsError && (
        <div className="glass-card rounded-2xl p-4 border border-red-400/20">
          <p className="text-sm text-[#FF3B30]">{alertsError}</p>
          <button
            onClick={clearAlertsError}
            className="text-sm text-[#FF3B30] hover:text-[#FF3B30]/70 transition-colors mt-1"
          >
            关闭
          </button>
        </div>
      )}

      <AlertSummaryCard />

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-[#1d1d1f]">告警规则</h2>
        <button
          onClick={handleNew}
          className="px-4 py-2 rounded-xl bg-[#007AFF] text-white text-sm font-medium hover:bg-[#007AFF]/90 transition-colors"
        >
          + 新建规则
        </button>
      </div>

      {showEditor && (
        <AlertRuleEditor rule={editingRule} onClose={handleCloseEditor} />
      )}

      <AlertRulesTable onEdit={handleEdit} />

      <AlertHistoryTable />
    </div>
  )
}
