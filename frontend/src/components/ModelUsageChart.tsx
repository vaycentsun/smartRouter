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
import { useDashboardStore } from '../store/useDashboardStore'

const COLORS = [
  '#007AFF', '#AF52DE', '#34C759', '#FF9500',
  '#FF3B30', '#5856D6', '#FF2D55', '#5AC8FA',
]

export function ModelUsageChart() {
  const { analyticsByModel } = useDashboardStore()
  const [chartType, setChartType] = useState<'pie' | 'bar'>('pie')

  if (analyticsByModel.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-5">
        <h3 className="text-sm font-medium text-[#86868b] mb-4">模型使用分布</h3>
        <div className="text-center py-8 text-[#a1a1a6] text-sm">暂无数据</div>
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
    <div className="glass-card rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-[#86868b]">模型使用分布</h3>
        <div className="flex gap-1 bg-[rgba(0,0,0,0.03)] rounded-lg p-0.5">
          <button
            onClick={() => setChartType('pie')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
              chartType === 'pie'
                ? 'bg-[rgba(0,122,255,0.1)] text-[#007AFF]'
                : 'text-[#86868b] hover:text-[#1d1d1f]'
            }`}
          >
            饼图
          </button>
          <button
            onClick={() => setChartType('bar')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
              chartType === 'bar'
                ? 'bg-[rgba(0,122,255,0.1)] text-[#007AFF]'
                : 'text-[#86868b] hover:text-[#1d1d1f]'
            }`}
          >
            柱状图
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
              formatter={(value) => [Number(value).toLocaleString(), 'Token']}
              contentStyle={{
                background: 'rgba(255,255,255,0.9)',
                backdropFilter: 'blur(8px)',
                border: '1px solid rgba(0,0,0,0.06)',
                borderRadius: '8px',
                fontSize: '12px',
              }}
            />
            <Legend />
          </PieChart>
        ) : (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.04)" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: '#86868b' }}
              axisLine={{ stroke: 'rgba(0,0,0,0.06)' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 12, fill: '#86868b' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              formatter={(value) => [Number(value).toLocaleString(), 'Token']}
              contentStyle={{
                background: 'rgba(255,255,255,0.9)',
                backdropFilter: 'blur(8px)',
                border: '1px solid rgba(0,0,0,0.06)',
                borderRadius: '8px',
                fontSize: '12px',
              }}
            />
            <Bar dataKey="value" fill="#007AFF" radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
