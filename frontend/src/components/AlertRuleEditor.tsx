import { useState, type SyntheticEvent } from 'react'
import { useTranslation } from '../i18n/useTranslation'
import { useDashboardStore } from '../store/useDashboardStore'
import type { AlertRule, AlertCondition, AlertChannel } from '../types'

interface AlertRuleEditorProps {
  rule?: AlertRule | null
  onClose: () => void
}

const EMPTY_RULE: AlertRule = {
  id: '',
  name: '',
  enabled: true,
  condition: {
    metric: 'daily_requests',
    operator: '>',
    threshold: 100,
  },
  severity: 'warning',
  time_window: '1d',
  channels: [{ type: 'log' }],
  cooldown_minutes: 60,
}

export function AlertRuleEditor({ rule, onClose }: AlertRuleEditorProps) {
  const { t } = useTranslation()
  const isEditing = !!rule
  const { createAlertRule, updateAlertRule, testAlertRule } = useDashboardStore()
  const [form, setForm] = useState<AlertRule>(rule ? { ...rule } : { ...EMPTY_RULE })
  const [isSaving, setIsSaving] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)

  const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault()
    setIsSaving(true)
    if (isEditing) {
      await updateAlertRule(form.id, form)
    } else {
      await createAlertRule(form)
    }
    setIsSaving(false)
    onClose()
  }

  const handleTest = async () => {
    const result = await testAlertRule(form)
    if (result) {
      setTestResult(result.triggered ? t('TRIGGERED') : t('NOT TRIGGERED'))
    } else {
      setTestResult(t('TEST FAILED'))
    }
  }

  const updateCondition = (partial: Partial<AlertCondition>) => {
    setForm((prev) => ({
      ...prev,
      condition: { ...prev.condition, ...partial },
    }))
  }

  const updateChannel = (index: number, partial: Partial<AlertChannel>) => {
    setForm((prev) => ({
      ...prev,
      channels: prev.channels.map((ch, i) => (i === index ? { ...ch, ...partial } : ch)),
    }))
  }

  const addChannel = () => {
    setForm((prev) => ({
      ...prev,
      channels: [...prev.channels, { type: 'log' }],
    }))
  }

  const removeChannel = (index: number) => {
    setForm((prev) => ({
      ...prev,
      channels: prev.channels.filter((_, i) => i !== index),
    }))
  }

  return (
    <div className="tech-card rounded-sm p-6">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-1 h-4 bg-[#00d4aa]" />
        <h3 className="text-lg font-semibold text-[#e8e8ed] uppercase tracking-wider font-mono">
          {isEditing ? t('EDIT ALERT RULE') : t('NEW ALERT RULE')}
        </h3>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="rule-id" className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">{t('RULE ID')}</label>
            <input
              id="rule-id"
              type="text"
              value={form.id}
              onChange={(e) => setForm({ ...form, id: e.target.value })}
              disabled={isEditing}
              required
              className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 disabled:opacity-50 tech-input"
              placeholder="rule-1"
            />
          </div>
          <div>
            <label htmlFor="rule-name" className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">{t('RULE NAME')}</label>
            <input
              id="rule-name"
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
              placeholder="high request count"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="rule-metric" className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">{t('METRIC')}</label>
            <select
              id="rule-metric"
              value={form.condition.metric}
              onChange={(e) => updateCondition({ metric: e.target.value as AlertCondition['metric'] })}
              className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
            >
              <option value="daily_cost">daily_cost</option>
              <option value="daily_requests">daily_requests</option>
              <option value="daily_tokens">daily_tokens</option>
              <option value="error_rate">error_rate</option>
            </select>
          </div>
          <div>
            <label htmlFor="rule-operator" className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">{t('OPERATOR')}</label>
            <select
              id="rule-operator"
              value={form.condition.operator}
              onChange={(e) => updateCondition({ operator: e.target.value as AlertCondition['operator'] })}
              className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
            >
              <option value=">">{'>'}</option>
              <option value="<">{'<'}</option>
              <option value=">=">{'>='}</option>
              <option value="<=">{'<='}</option>
            </select>
          </div>
          <div>
            <label htmlFor="rule-threshold" className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">{t('THRESHOLD')}</label>
            <input
              id="rule-threshold"
              type="number"
              step="any"
              value={form.condition.threshold}
              onChange={(e) => updateCondition({ threshold: parseFloat(e.target.value) })}
              required
              className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="rule-severity" className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">{t('SEVERITY')}</label>
            <select
              id="rule-severity"
              value={form.severity}
              onChange={(e) => setForm({ ...form, severity: e.target.value as AlertRule['severity'] })}
              className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
            >
              <option value="info">info</option>
              <option value="warning">warning</option>
              <option value="critical">critical</option>
            </select>
          </div>
          <div>
            <label htmlFor="rule-window" className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">{t('TIME WINDOW')}</label>
            <select
              id="rule-window"
              value={form.time_window}
              onChange={(e) => setForm({ ...form, time_window: e.target.value })}
              className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
            >
              <option value="1d">{t('1 DAY')}</option>
              <option value="7d">{t('7 DAYS')}</option>
              <option value="30d">{t('30 DAYS')}</option>
            </select>
          </div>
          <div>
            <label htmlFor="rule-cooldown" className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-1">{t('COOLDOWN (MIN)')}</label>
            <input
              id="rule-cooldown"
              type="number"
              value={form.cooldown_minutes}
              onChange={(e) => setForm({ ...form, cooldown_minutes: parseInt(e.target.value) })}
              required
              className="w-full px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-mono text-[#636366] uppercase tracking-wider mb-2">{t('NOTIFICATION CHANNELS')}</label>
          <div className="space-y-2">
            {form.channels.map((ch, index) => (
              <div key={index} className="flex gap-2 items-center">
                <select
                  value={ch.type}
                  onChange={(e) => updateChannel(index, { type: e.target.value as AlertChannel['type'] })}
                  className="px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
                >
                  <option value="log">{t('LOG')}</option>
                  <option value="webhook">{t('WEBHOOK')}</option>
                </select>
                {ch.type === 'webhook' && (
                  <input
                    type="url"
                    value={ch.url || ''}
                    onChange={(e) => updateChannel(index, { url: e.target.value })}
                    placeholder="https://hooks.example.com/alert"
                    className="flex-1 px-3 py-2 rounded-sm border border-[#1a1a2e] bg-[#0a0a0f] text-sm focus:outline-none focus:ring-2 focus:ring-[#00d4aa]/20 tech-input"
                  />
                )}
          <button
            type="button"
            onClick={() => removeChannel(index)}
            className="text-[#e74c3c] hover:text-[#e74c3c]/70 text-xs px-2 font-mono uppercase tracking-wider"
          >
            {t('DELETE')}
          </button>
              </div>
            ))}
          <button
            type="button"
            onClick={addChannel}
            className="text-xs text-[#00d4aa] hover:text-[#00d4aa]/70 font-mono uppercase tracking-wider"
          >
            {t('+ ADD CHANNEL')}
          </button>
          </div>
        </div>

        {testResult && (
          <div className="rounded-sm p-3 bg-[rgba(0,212,170,0.08)] text-sm text-[#00d4aa]">
            {testResult}
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={isSaving}
            className="px-5 py-2 rounded-sm tech-btn-primary text-xs font-mono uppercase tracking-wider disabled:opacity-50"
          >
            {isSaving ? t('SAVING...') : isEditing ? t('SAVE') : t('CREATE')}
          </button>
          <button
            type="button"
            onClick={handleTest}
            className="px-5 py-2 rounded-sm tech-btn text-xs font-mono uppercase tracking-wider"
          >
            {t('TEST RULE')}
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
  )
}
