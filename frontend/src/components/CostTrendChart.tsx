import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { useTranslation } from '../i18n/I18nProvider'
import { useDashboardStore } from '../store/useDashboardStore'

export function CostTrendChart() {
  const { analyticsDaily } = useDashboardStore()
  const { t } = useTranslation()

  if (analyticsDaily.length === 0) {
    return (
      <div className="tech-card rounded-sm p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-1 h-4 bg-[#00d4aa]" />
          <h3 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('Cost Trend')}</h3>
        </div>
        <div className="text-center py-8 text-[#636366] text-sm font-mono">{t('NO DATA')}</div>
      </div>
    )
  }

  const data = analyticsDaily.map((item) => ({
    date: item.date.slice(5),
    cost: item.cost,
  }))

  return (
    <div className="tech-card rounded-sm p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-1 h-4 bg-[#00d4aa]" />
        <h3 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('Cost Trend')}</h3>
      </div>
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00d4aa" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#00d4aa" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: '#636366', fontFamily: 'JetBrains Mono' }}
            axisLine={{ stroke: '#1a1a2e' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#636366', fontFamily: 'JetBrains Mono' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `¥${v}`}
          />
          <Tooltip
            formatter={(value) => [`¥${Number(value).toFixed(2)}`, t('Cost')]}
            contentStyle={{
              background: '#111118',
              border: '1px solid #1a1a2e',
              borderRadius: '4px',
              fontSize: '12px',
              fontFamily: 'JetBrains Mono',
              color: '#e8e8ed',
            }}
          />
          <Area
            type="monotone"
            dataKey="cost"
            stroke="#00d4aa"
            strokeWidth={1.5}
            fill="url(#costGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
