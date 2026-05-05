import { useState } from 'react'
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
  const isEditing = !!rule
  const { createAlertRule, updateAlertRule, testAlertRule } = useDashboardStore()
  const [form, setForm] = useState<AlertRule>(rule ? { ...rule } : { ...EMPTY_RULE })
  const [isSaving, setIsSaving] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
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
      setTestResult(result.triggered ? '条件满足，将触发告警' : '条件不满足，不会触发告警')
    } else {
      setTestResult('测试失败')
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
    <div className="glass-card rounded-2xl p-6">
      <h3 className="text-lg font-semibold text-[#1d1d1f] mb-4">
        {isEditing ? '编辑告警规则' : '新建告警规则'}
      </h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="rule-id" className="block text-sm font-medium text-[#86868b] mb-1">规则 ID</label>
            <input
              id="rule-id"
              type="text"
              value={form.id}
              onChange={(e) => setForm({ ...form, id: e.target.value })}
              disabled={isEditing}
              required
              className="w-full px-3 py-2 rounded-xl border border-black/10 bg-white/50 text-sm focus:outline-none focus:ring-2 focus:ring-[#007AFF]/20 disabled:opacity-50"
              placeholder="rule-1"
            />
          </div>
          <div>
            <label htmlFor="rule-name" className="block text-sm font-medium text-[#86868b] mb-1">规则名称</label>
            <input
              id="rule-name"
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              className="w-full px-3 py-2 rounded-xl border border-black/10 bg-white/50 text-sm focus:outline-none focus:ring-2 focus:ring-[#007AFF]/20"
              placeholder="请求数过高"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="rule-metric" className="block text-sm font-medium text-[#86868b] mb-1">指标</label>
            <select
              id="rule-metric"
              value={form.condition.metric}
              onChange={(e) => updateCondition({ metric: e.target.value as AlertCondition['metric'] })}
              className="w-full px-3 py-2 rounded-xl border border-black/10 bg-white/50 text-sm focus:outline-none focus:ring-2 focus:ring-[#007AFF]/20"
            >
              <option value="daily_cost">daily_cost</option>
              <option value="daily_requests">daily_requests</option>
              <option value="daily_tokens">daily_tokens</option>
              <option value="error_rate">error_rate</option>
            </select>
          </div>
          <div>
            <label htmlFor="rule-operator" className="block text-sm font-medium text-[#86868b] mb-1">运算符</label>
            <select
              id="rule-operator"
              value={form.condition.operator}
              onChange={(e) => updateCondition({ operator: e.target.value as AlertCondition['operator'] })}
              className="w-full px-3 py-2 rounded-xl border border-black/10 bg-white/50 text-sm focus:outline-none focus:ring-2 focus:ring-[#007AFF]/20"
            >
              <option value=">">{'>'}</option>
              <option value="<">{'<'}</option>
              <option value=">=">{'>='}</option>
              <option value="<=">{'<='}</option>
            </select>
          </div>
          <div>
            <label htmlFor="rule-threshold" className="block text-sm font-medium text-[#86868b] mb-1">阈值</label>
            <input
              id="rule-threshold"
              type="number"
              step="any"
              value={form.condition.threshold}
              onChange={(e) => updateCondition({ threshold: parseFloat(e.target.value) })}
              required
              className="w-full px-3 py-2 rounded-xl border border-black/10 bg-white/50 text-sm focus:outline-none focus:ring-2 focus:ring-[#007AFF]/20"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="rule-severity" className="block text-sm font-medium text-[#86868b] mb-1">严重级别</label>
            <select
              id="rule-severity"
              value={form.severity}
              onChange={(e) => setForm({ ...form, severity: e.target.value as AlertRule['severity'] })}
              className="w-full px-3 py-2 rounded-xl border border-black/10 bg-white/50 text-sm focus:outline-none focus:ring-2 focus:ring-[#007AFF]/20"
            >
              <option value="info">info</option>
              <option value="warning">warning</option>
              <option value="critical">critical</option>
            </select>
          </div>
          <div>
            <label htmlFor="rule-window" className="block text-sm font-medium text-[#86868b] mb-1">时间窗口</label>
            <select
              id="rule-window"
              value={form.time_window}
              onChange={(e) => setForm({ ...form, time_window: e.target.value })}
              className="w-full px-3 py-2 rounded-xl border border-black/10 bg-white/50 text-sm focus:outline-none focus:ring-2 focus:ring-[#007AFF]/20"
            >
              <option value="1d">1 天</option>
              <option value="7d">7 天</option>
              <option value="30d">30 天</option>
            </select>
          </div>
          <div>
            <label htmlFor="rule-cooldown" className="block text-sm font-medium text-[#86868b] mb-1">冷却时间（分钟）</label>
            <input
              id="rule-cooldown"
              type="number"
              value={form.cooldown_minutes}
              onChange={(e) => setForm({ ...form, cooldown_minutes: parseInt(e.target.value) })}
              required
              className="w-full px-3 py-2 rounded-xl border border-black/10 bg-white/50 text-sm focus:outline-none focus:ring-2 focus:ring-[#007AFF]/20"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-[#86868b] mb-2">通知渠道</label>
          <div className="space-y-2">
            {form.channels.map((ch, index) => (
              <div key={index} className="flex gap-2 items-center">
                <select
                  value={ch.type}
                  onChange={(e) => updateChannel(index, { type: e.target.value as AlertChannel['type'] })}
                  className="px-3 py-2 rounded-xl border border-black/10 bg-white/50 text-sm focus:outline-none focus:ring-2 focus:ring-[#007AFF]/20"
                >
                  <option value="log">日志</option>
                  <option value="webhook">Webhook</option>
                </select>
                {ch.type === 'webhook' && (
                  <input
                    type="url"
                    value={ch.url || ''}
                    onChange={(e) => updateChannel(index, { url: e.target.value })}
                    placeholder="https://hooks.example.com/alert"
                    className="flex-1 px-3 py-2 rounded-xl border border-black/10 bg-white/50 text-sm focus:outline-none focus:ring-2 focus:ring-[#007AFF]/20"
                  />
                )}
                <button
                  type="button"
                  onClick={() => removeChannel(index)}
                  className="text-[#FF3B30] hover:text-[#FF3B30]/70 text-xs px-2"
                >
                  删除
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={addChannel}
              className="text-sm text-[#007AFF] hover:text-[#007AFF]/70 font-medium"
            >
              + 添加渠道
            </button>
          </div>
        </div>

        {testResult && (
          <div className="rounded-xl p-3 bg-[rgba(0,122,255,0.08)] text-sm text-[#007AFF]">
            {testResult}
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={isSaving}
            className="px-5 py-2 rounded-xl bg-[#007AFF] text-white text-sm font-medium hover:bg-[#007AFF]/90 transition-colors disabled:opacity-50"
          >
            {isSaving ? '保存中...' : isEditing ? '保存' : '创建'}
          </button>
          <button
            type="button"
            onClick={handleTest}
            className="px-5 py-2 rounded-xl bg-[rgba(0,122,255,0.08)] text-[#007AFF] text-sm font-medium hover:bg-[rgba(0,122,255,0.12)] transition-colors"
          >
            测试规则
          </button>
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 rounded-xl border border-black/10 text-[#1d1d1f] text-sm font-medium hover:bg-black/5 transition-colors"
          >
            取消
          </button>
        </div>
      </form>
    </div>
  )
}
