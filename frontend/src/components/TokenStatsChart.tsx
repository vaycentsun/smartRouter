import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useTranslation } from '../i18n/I18nProvider'
import { useDashboardStore } from '../store/useDashboardStore'

const COLORS = [
  '#00d4aa', '#9b59b6', '#00d4aa', '#f39c12',
  '#e74c3c', '#6c5ce7', '#e84393', '#00cec9',
]

export function TokenStatsChart() {
  const { t } = useTranslation()
  const { tokenStats } = useDashboardStore()

  if (tokenStats.length === 0) {
    return (
      <div className="text-center py-8 text-[#636366] text-sm">
        {t('NO DATA. SEND REQUESTS TO GENERATE STATISTICS.')}
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
          label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
        >
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => {
            const num = typeof value === 'number' ? value : 0
            return [num.toLocaleString(), t('Token')]
          }}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}
