import { useEffect, useState } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import { AlertSummaryCard } from './AlertSummaryCard'
import { AlertRulesTable } from './AlertRulesTable'
import { AlertRuleEditor } from './AlertRuleEditor'
import { AlertHistoryTable } from './AlertHistoryTable'
import type { AlertRule } from '../types'
import { useTranslation } from '../i18n/useTranslation'

export function AlertsPage() {
  const { t } = useTranslation()
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
        <div className="tech-card rounded-sm p-4 border border-[rgba(231,76,60,0.2)]">
          <p className="text-sm text-[#e74c3c] font-mono">{alertsError}</p>
          <button
            onClick={clearAlertsError}
            className="text-sm text-[#e74c3c] hover:opacity-70 transition-opacity mt-1 font-mono uppercase"
          >
            {t('DISMISS')}
          </button>
        </div>
      )}

      <AlertSummaryCard />

      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('Alert Rules')}</h2>
        <button
          onClick={handleNew}
          className="tech-btn tech-btn-primary px-4 py-2 rounded-sm text-xs"
        >
          {t('+ NEW RULE')}
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
