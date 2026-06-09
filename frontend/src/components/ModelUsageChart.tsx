import { useState } from 'react'
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts'
import { useTranslation } from '../i18n/useTranslation'
import { useDashboardStore } from '../store/useDashboardStore'

const COLORS = [
  '#00d4aa', '#9b59b6', '#3498db', '#f39c12',
  '#e74c3c', '#6c5ce7', '#e84393', '#00cec9',
]

export function ModelUsageChart() {
  const { analyticsByModel } = useDashboardStore()
  const [chartType, setChartType] = useState<'pie' | 'bar'>('pie')
  const { t } = useTranslation()

  if (analyticsByModel.length === 0) {
    return (
      <div className="tech-card rounded-sm p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-1 h-4 bg-[#3498db]" />
          <h3 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('Model Usage')}</h3>
        </div>
        <div className="text-center py-8 text-[#636366] text-sm font-mono">{t('NO DATA')}</div>
      </div>
    )
  }

  const MAX_PIE_SLICES = 5

  const sorted = [...analyticsByModel]
    .map((item) => ({
      name: item.model,
      value: item.prompt_tokens + item.completion_tokens,
      prompt: item.prompt_tokens,
      completion: item.completion_tokens,
      reasoning: item.reasoning_tokens,
      cached: item.cached_tokens,
      cost: item.cost,
      requests: item.request_count,
    }))
    .sort((a, b) => b.value - a.value)

  const top = sorted.slice(0, MAX_PIE_SLICES)
  const rest = sorted.slice(MAX_PIE_SLICES)

  const data =
    rest.length > 0
      ? [
          ...top,
          {
            name: t('Others'),
            value: rest.reduce((sum, item) => sum + item.value, 0),
            prompt: rest.reduce((sum, item) => sum + item.prompt, 0),
            completion: rest.reduce((sum, item) => sum + item.completion, 0),
            reasoning: rest.reduce((sum, item) => sum + item.reasoning, 0),
            cached: rest.reduce((sum, item) => sum + item.cached, 0),
            cost: rest.reduce((sum, item) => sum + item.cost, 0),
            requests: rest.reduce((sum, item) => sum + item.requests, 0),
          },
        ]
      : top

  return (
    <div className="tech-card rounded-sm p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-1 h-4 bg-[#3498db]" />
          <h3 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('Model Usage')}</h3>
        </div>
        <div className="flex gap-1 border border-[#1a1a2e] rounded-sm p-0.5">
          <button
            onClick={() => setChartType('pie')}
            className={`px-3 py-1 rounded-sm text-xs font-mono uppercase tracking-wider transition-all ${
              chartType === 'pie'
                ? 'bg-[rgba(0,212,170,0.08)] text-[#00d4aa] border border-[rgba(0,212,170,0.2)]'
                : 'text-[#636366] hover:text-[#8e8e93]'
            }`}
          >
            {t('PIE')}
          </button>
          <button
            onClick={() => setChartType('bar')}
            className={`px-3 py-1 rounded-sm text-xs font-mono uppercase tracking-wider transition-all ${
              chartType === 'bar'
                ? 'bg-[rgba(0,212,170,0.08)] text-[#00d4aa] border border-[rgba(0,212,170,0.2)]'
                : 'text-[#636366] hover:text-[#8e8e93]'
            }`}
          >
            {t('BAR')}
          </button>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        {chartType === 'pie' ? (
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={90}
              label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => [Number(value).toLocaleString(), t('Token')]}
              contentStyle={{
                background: '#111118',
                border: '1px solid #1a1a2e',
                borderRadius: '4px',
                fontSize: '12px',
                fontFamily: 'JetBrains Mono',
                color: '#e8e8ed',
              }}
            />
            <Legend />
          </PieChart>
        ) : (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: '#636366', fontFamily: 'JetBrains Mono' }}
              axisLine={{ stroke: '#1a1a2e' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#636366', fontFamily: 'JetBrains Mono' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              formatter={(value) => [Number(value).toLocaleString(), t('Token')]}
              contentStyle={{
                background: '#111118',
                border: '1px solid #1a1a2e',
                borderRadius: '4px',
                fontSize: '12px',
                fontFamily: 'JetBrains Mono',
                color: '#e8e8ed',
              }}
            />
            <Bar dataKey="value" fill="#00d4aa" radius={[2, 2, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
