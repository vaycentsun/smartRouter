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

export function RequestTrendChart() {
  const { analyticsDaily } = useDashboardStore()
  const { t } = useTranslation()

  if (analyticsDaily.length === 0) {
    return (
      <div className="card-base p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-1 h-5 bg-[#B45AF2] rounded-full" />
          <h3 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider">{t('Request Trend')}</h3>
        </div>
        <div className="text-center py-8 text-[#889397] text-sm">{t('NO DATA')}</div>
      </div>
    )
  }

  const data = analyticsDaily.map((item) => ({
    date: item.date.slice(5),
    requests: item.requests,
  }))

  return (
    <div className="card-base p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-1 h-5 bg-[#B45AF2] rounded-full" />
        <h3 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider">{t('Request Trend')}</h3>
      </div>
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="reqGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#B45AF2" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#B45AF2" stopOpacity={0} />
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
          />
          <Tooltip
            formatter={(value) => [Number(value).toLocaleString(), t('Requests')]}
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
            dataKey="requests"
            stroke="#B45AF2"
            strokeWidth={1.5}
            fill="url(#reqGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
