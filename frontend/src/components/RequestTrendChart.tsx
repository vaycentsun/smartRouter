import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { useDashboardStore } from '../store/useDashboardStore'

export function RequestTrendChart() {
  const { analyticsDaily } = useDashboardStore()

  if (analyticsDaily.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-5">
        <h3 className="text-sm font-medium text-[#86868b] mb-4">请求趋势</h3>
        <div className="text-center py-8 text-[#a1a1a6] text-sm">暂无数据</div>
      </div>
    )
  }

  const data = analyticsDaily.map((item) => ({
    date: item.date.slice(5),
    requests: item.requests,
  }))

  return (
    <div className="glass-card rounded-2xl p-5">
      <h3 className="text-sm font-medium text-[#86868b] mb-4">请求趋势</h3>
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="reqGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#AF52DE" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#AF52DE" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.04)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12, fill: '#86868b' }}
            axisLine={{ stroke: 'rgba(0,0,0,0.06)' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#86868b' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(value) => [Number(value).toLocaleString(), '请求数']}
            contentStyle={{
              background: 'rgba(255,255,255,0.9)',
              backdropFilter: 'blur(8px)',
              border: '1px solid rgba(0,0,0,0.06)',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
          <Area
            type="monotone"
            dataKey="requests"
            stroke="#AF52DE"
            strokeWidth={2}
            fill="url(#reqGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
