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
import { useTranslation } from '../i18n/I18nProvider'
import { useDashboardStore } from '../store/useDashboardStore'

const COLORS = [
  '#00A34D', '#B45AF2', '#2F87FC', '#F08B1E',
  '#E65C5C', '#6C5CE7', '#E54B9E', '#00A3A3',
]

export function ModelUsageChart() {
  const { analyticsByModel } = useDashboardStore()
  const [chartType, setChartType] = useState<'pie' | 'bar'>('pie')
  const { t } = useTranslation()

  if (analyticsByModel.length === 0) {
    return (
      <div className="card-base p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-1 h-5 bg-[#2F87FC] rounded-full" />
          <h3 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider">{t('Model Usage')}</h3>
        </div>
        <div className="text-center py-8 text-[#889397] text-sm">{t('NO DATA')}</div>
      </div>
    )
  }

  const data = analyticsByModel.map((item) => ({
    name: item.model,
    value: item.prompt_tokens + item.completion_tokens,
    prompt: item.prompt_tokens,
    completion: item.completion_tokens,
    reasoning: item.reasoning_tokens,
    cached: item.cached_tokens,
    cost: item.cost,
    requests: item.request_count,
  }))

  return (
    <div className="card-base p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-1 h-5 bg-[#2F87FC] rounded-full" />
          <h3 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider">{t('Model Usage')}</h3>
        </div>
        <div className="flex gap-1 bg-[#F4F7F6] rounded-full p-0.5">
          <button
            onClick={() => setChartType('pie')}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
              chartType === 'pie'
                ? 'bg-white text-[#00A34D] shadow-sm'
                : 'text-[#889397] hover:text-[#5C6C75]'
            }`}
          >
            {t('PIE')}
          </button>
          <button
            onClick={() => setChartType('bar')}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
              chartType === 'bar'
                ? 'bg-white text-[#00A34D] shadow-sm'
                : 'text-[#889397] hover:text-[#5C6C75]'
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
                background: '#FFFFFF',
                border: '1px solid #E8EDEB',
                borderRadius: '12px',
                fontSize: '12px',
                fontFamily: 'Source Code Pro',
                color: '#001E2B',
                boxShadow: 'rgba(0, 30, 43, 0.08) 0px 4px 12px 0px',
              }}
            />
            <Legend />
          </PieChart>
        ) : (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E8EDEB" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: '#889397', fontFamily: 'Source Code Pro' }}
              axisLine={{ stroke: '#E8EDEB' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#889397', fontFamily: 'Source Code Pro' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              formatter={(value) => [Number(value).toLocaleString(), t('Token')]}
              contentStyle={{
                background: '#FFFFFF',
                border: '1px solid #E8EDEB',
                borderRadius: '12px',
                fontSize: '12px',
                fontFamily: 'Source Code Pro',
                color: '#001E2B',
                boxShadow: 'rgba(0, 30, 43, 0.08) 0px 4px 12px 0px',
              }}
            />
            <Bar dataKey="value" fill="#00A34D" radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
