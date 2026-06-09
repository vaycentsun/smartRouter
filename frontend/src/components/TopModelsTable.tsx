import { useState } from 'react'
import { useTranslation } from '../i18n/useTranslation'
import { useDashboardStore } from '../store/useDashboardStore'
import type { AnalyticsTopModelItem } from '../types'

type SortKey = keyof AnalyticsTopModelItem

interface SortIconProps {
  column: SortKey
  sortKey: SortKey
  sortAsc: boolean
}

function SortIcon({ column, sortKey, sortAsc }: SortIconProps) {
  if (sortKey !== column) return <span className="text-[#636366] ml-1 font-mono text-xs">↕</span>
  return <span className="text-[#00d4aa] ml-1 font-mono text-xs">{sortAsc ? '▲' : '▼'}</span>
}

export function TopModelsTable() {
  const { analyticsTopModels } = useDashboardStore()
  const [sortKey, setSortKey] = useState<SortKey>('total_tokens')
  const [sortAsc, setSortAsc] = useState(false)
  const { t } = useTranslation()

  const sorted = [...analyticsTopModels].sort((a, b) => {
    const aVal = a[sortKey]
    const bVal = b[sortKey]
    if (typeof aVal === 'string') {
      return sortAsc ? aVal.localeCompare(bVal as string) : (bVal as string).localeCompare(aVal)
    }
    return sortAsc ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number)
  })

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(false)
    }
  }

  if (analyticsTopModels.length === 0) {
    return (
      <div className="tech-card rounded-sm p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-1 h-4 bg-[#e84393]" />
          <h3 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('Top Models')}</h3>
        </div>
        <div className="text-center py-8 text-[#636366] text-sm font-mono">{t('NO DATA')}</div>
      </div>
    )
  }

  return (
    <div className="tech-card rounded-sm p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-1 h-4 bg-[#e84393]" />
        <h3 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('Top Models')}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1a1a2e]">
              <th className="text-left py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest">#</th>
              <th
                className="text-left py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
                onClick={() => handleSort('model')}
              >
                {t('Model')} <SortIcon column="model" sortKey={sortKey} sortAsc={sortAsc} />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
                onClick={() => handleSort('prompt_tokens')}
              >
                {t('Input')} <SortIcon column="prompt_tokens" sortKey={sortKey} sortAsc={sortAsc} />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
                onClick={() => handleSort('completion_tokens')}
              >
                {t('Output')} <SortIcon column="completion_tokens" sortKey={sortKey} sortAsc={sortAsc} />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
                onClick={() => handleSort('reasoning_tokens')}
              >
                {t('Reason')} <SortIcon column="reasoning_tokens" sortKey={sortKey} sortAsc={sortAsc} />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
                onClick={() => handleSort('cached_tokens')}
              >
                {t('Cache')} <SortIcon column="cached_tokens" sortKey={sortKey} sortAsc={sortAsc} />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
                onClick={() => handleSort('total_tokens')}
              >
                {t('Total')} <SortIcon column="total_tokens" sortKey={sortKey} sortAsc={sortAsc} />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
                onClick={() => handleSort('cost')}
              >
                {t('Cost')} <SortIcon column="cost" sortKey={sortKey} sortAsc={sortAsc} />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
                onClick={() => handleSort('request_count')}
              >
                {t('Req')} <SortIcon column="request_count" sortKey={sortKey} sortAsc={sortAsc} />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item, index) => (
              <tr
                key={item.model}
                className="data-row"
              >
                <td className="py-3 px-2 text-[#636366] font-mono text-xs">{index + 1}</td>
                <td className="py-3 px-2 font-medium text-[#e8e8ed] font-mono text-xs">{item.model}</td>
                <td className="py-3 px-2 text-right text-[#e8e8ed] font-mono text-xs">
                  {item.prompt_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#e8e8ed] font-mono text-xs">
                  {item.completion_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#e8e8ed] font-mono text-xs">
                  {item.reasoning_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#e8e8ed] font-mono text-xs">
                  {item.cached_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#00d4aa] font-mono text-xs font-medium">
                  {item.total_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#e8e8ed] font-mono text-xs">
                  ¥{item.cost.toFixed(2)}
                </td>
                <td className="py-3 px-2 text-right text-[#e8e8ed] font-mono text-xs">
                  {item.request_count.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
