import { useState } from 'react'
import { useTranslation } from '../i18n/I18nProvider'
import { useDashboardStore } from '../store/useDashboardStore'
import type { TokenStatsItem } from '../types'

type SortKey = keyof Omit<TokenStatsItem, 'model'> | 'model'

export function TokenStatsTable() {
  const { t } = useTranslation()
  const { tokenStats } = useDashboardStore()
  const [sortKey, setSortKey] = useState<SortKey>('total_tokens')
  const [sortAsc, setSortAsc] = useState(false)

  const sorted = [...tokenStats].sort((a, b) => {
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

  const SortIcon = ({ column }: { column: SortKey }) => {
    if (sortKey !== column) return <span className="text-[#636366] ml-1">↕</span>
    return <span className="text-[#00d4aa] ml-1">{sortAsc ? '▲' : '▼'}</span>
  }

  if (tokenStats.length === 0) {
    return (
      <div className="text-center py-8 text-[#636366] text-sm">
        {t('NO DATA. SEND REQUESTS TO GENERATE STATISTICS.')}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#1a1a2e]">
            <th
              className="text-left py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
              onClick={() => handleSort('model')}
            >
              {t('MODEL')} <SortIcon column="model" />
            </th>
            <th
              className="text-right py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
              onClick={() => handleSort('request_count')}
            >
              {t('REQUESTS')} <SortIcon column="request_count" />
            </th>
            <th
              className="text-right py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
              onClick={() => handleSort('prompt_tokens')}
            >
              {t('PROMPT')} <SortIcon column="prompt_tokens" />
            </th>
            <th
              className="text-right py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
              onClick={() => handleSort('completion_tokens')}
            >
              {t('COMPLETION')} <SortIcon column="completion_tokens" />
            </th>
            <th
              className="text-right py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
              onClick={() => handleSort('reasoning_tokens')}
            >
              {t('REASONING')} <SortIcon column="reasoning_tokens" />
            </th>
            <th
              className="text-right py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
              onClick={() => handleSort('cached_tokens')}
            >
              {t('CACHED')} <SortIcon column="cached_tokens" />
            </th>
            <th
              className="text-right py-3 px-2 text-[10px] text-[#636366] font-mono uppercase tracking-widest cursor-pointer select-none"
              onClick={() => handleSort('total_tokens')}
            >
              {t('TOTAL')} <SortIcon column="total_tokens" />
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((item) => (
            <tr
              key={item.model}
              className="data-row border-b border-[#1a1a2e] last:border-0"
            >
              <td className="py-3 px-2 font-medium text-[#e8e8ed]">{item.model}</td>
              <td className="py-3 px-2 text-right text-[#e8e8ed] font-mono">
                {item.request_count.toLocaleString()}
              </td>
              <td className="py-3 px-2 text-right text-[#e8e8ed] font-mono">
                {item.prompt_tokens.toLocaleString()}
              </td>
              <td className="py-3 px-2 text-right text-[#e8e8ed] font-mono">
                {item.completion_tokens.toLocaleString()}
              </td>
              <td className="py-3 px-2 text-right text-[#e8e8ed] font-mono">
                {item.reasoning_tokens.toLocaleString()}
              </td>
              <td className="py-3 px-2 text-right text-[#e8e8ed] font-mono">
                {item.cached_tokens.toLocaleString()}
              </td>
              <td className="py-3 px-2 text-right text-[#e8e8ed] font-mono font-medium">
                {item.total_tokens.toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
