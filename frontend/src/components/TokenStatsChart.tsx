import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useDashboardStore } from '../store/useDashboardStore'

const COLORS = [
  '#007AFF', '#AF52DE', '#34C759', '#FF9500',
  '#FF3B30', '#5856D6', '#FF2D55', '#5AC8FA',
]

export function TokenStatsChart() {
  const { tokenStats } = useDashboardStore()

  if (tokenStats.length === 0) {
    return (
      <div className="text-center py-8 text-[#a1a1a6] text-sm">
        暂无数据，发送请求后将自动统计
      </div>
    )
  }

  const data = tokenStats.map((item) => ({
    name: item.model,
    value: item.total_tokens,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={100}
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
        >
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number) => [value.toLocaleString(), 'Token']}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}
