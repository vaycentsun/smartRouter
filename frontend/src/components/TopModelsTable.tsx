import { useState } from 'react'
import { useTranslation } from '../i18n/I18nProvider'
import { useDashboardStore } from '../store/useDashboardStore'
import type { AnalyticsTopModelItem } from '../types'

type SortKey = keyof AnalyticsTopModelItem

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

  const SortIcon = ({ column }: { column: SortKey }) => {
    if (sortKey !== column) return <span className="text-[#889397] ml-1 text-xs">↕</span>
    return <span className="text-[#00A34D] ml-1 text-xs">{sortAsc ? '▲' : '▼'}</span>
  }

  if (analyticsTopModels.length === 0) {
    return (
      <div className="card-base rounded-xl p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-1 h-4 bg-[#e84393]" />
          <h3 className="text-sm font-semibold text-[#001E2B]">{t('Top Models')}</h3>
        </div>
        <div className="text-center py-8 text-[#889397] text-sm">{t('NO DATA')}</div>
      </div>
    )
  }

  return (
    <div className="card-base rounded-xl p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-1 h-4 bg-[#e84393]" />
        <h3 className="text-sm font-semibold text-[#001E2B]">{t('Top Models')}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#E8EDEB]">
              <th className="text-left py-3 px-2 text-[10px] text-[#889397] font-medium">#</th>
              <th
                className="text-left py-3 px-2 text-[10px] text-[#889397] font-medium cursor-pointer select-none"
                onClick={() => handleSort('model')}
              >
                {t('Model')} <SortIcon column="model" />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#889397] font-medium cursor-pointer select-none"
                onClick={() => handleSort('prompt_tokens')}
              >
                {t('Input')} <SortIcon column="prompt_tokens" />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#889397] font-medium cursor-pointer select-none"
                onClick={() => handleSort('completion_tokens')}
              >
                {t('Output')} <SortIcon column="completion_tokens" />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#889397] font-medium cursor-pointer select-none"
                onClick={() => handleSort('reasoning_tokens')}
              >
                {t('Reason')} <SortIcon column="reasoning_tokens" />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#889397] font-medium cursor-pointer select-none"
                onClick={() => handleSort('cached_tokens')}
              >
                {t('Cache')} <SortIcon column="cached_tokens" />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#889397] font-medium cursor-pointer select-none"
                onClick={() => handleSort('total_tokens')}
              >
                {t('Total')} <SortIcon column="total_tokens" />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#889397] font-medium cursor-pointer select-none"
                onClick={() => handleSort('cost')}
              >
                {t('Cost')} <SortIcon column="cost" />
              </th>
              <th
                className="text-right py-3 px-2 text-[10px] text-[#889397] font-medium cursor-pointer select-none"
                onClick={() => handleSort('request_count')}
              >
                {t('Req')} <SortIcon column="request_count" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item, index) => (
              <tr
                key={item.model}
                className="data-row"
              >
                <td className="py-3 px-2 text-[#889397] text-xs">{index + 1}</td>
                <td className="py-3 px-2 font-medium text-[#001E2B] font-mono text-xs">{item.model}</td>
                <td className="py-3 px-2 text-right text-[#001E2B] font-mono text-xs">
                  {item.prompt_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#001E2B] font-mono text-xs">
                  {item.completion_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#001E2B] font-mono text-xs">
                  {item.reasoning_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#001E2B] font-mono text-xs">
                  {item.cached_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#00A34D] font-mono text-xs font-medium">
                  {item.total_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#001E2B] font-mono text-xs">
                  ¥{item.cost.toFixed(2)}
                </td>
                <td className="py-3 px-2 text-right text-[#001E2B] font-mono text-xs">
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
