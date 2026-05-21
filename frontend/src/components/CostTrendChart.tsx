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
      <div className="card-base p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-1 h-5 bg-[#00A34D] rounded-full" />
          <h3 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider">{t('Cost Trend')}</h3>
        </div>
        <div className="text-center py-8 text-[#889397] text-sm">{t('NO DATA')}</div>
      </div>
    )
  }

  const data = analyticsDaily.map((item) => ({
    date: item.date.slice(5),
    cost: item.cost,
  }))

  return (
    <div className="card-base p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-1 h-5 bg-[#00A34D] rounded-full" />
        <h3 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider">{t('Cost Trend')}</h3>
      </div>
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00A34D" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#00A34D" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#E8EDEB" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: '#889397', fontFamily: 'Source Code Pro' }}
            axisLine={{ stroke: '#E8EDEB' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#889397', fontFamily: 'Source Code Pro' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `¥${v}`}
          />
          <Tooltip
            formatter={(value) => [`¥${Number(value).toFixed(2)}`, t('Cost')]}
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
          <Area
            type="monotone"
            dataKey="cost"
            stroke="#00A34D"
            strokeWidth={1.5}
            fill="url(#costGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
