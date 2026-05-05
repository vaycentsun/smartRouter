import { useState } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import type { TokenStatsItem } from '../types'

type SortKey = keyof Omit<TokenStatsItem, 'model'> | 'model'

export function TokenStatsTable() {
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
    if (sortKey !== column) return <span className="text-[#c7c7cc] ml-1">↕</span>
    return <span className="text-[#007AFF] ml-1">{sortAsc ? '▲' : '▼'}</span>
  }

  if (tokenStats.length === 0) {
    return (
      <div className="text-center py-8 text-[#a1a1a6] text-sm">
        暂无数据，发送请求后将自动统计
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[rgba(0,0,0,0.06)]">
            <th
              className="text-left py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
              onClick={() => handleSort('model')}
            >
              模型 <SortIcon column="model" />
            </th>
            <th
              className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
              onClick={() => handleSort('request_count')}
            >
              请求次数 <SortIcon column="request_count" />
            </th>
            <th
              className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
              onClick={() => handleSort('prompt_tokens')}
            >
              输入 Token <SortIcon column="prompt_tokens" />
            </th>
            <th
              className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
              onClick={() => handleSort('completion_tokens')}
            >
              输出 Token <SortIcon column="completion_tokens" />
            </th>
            <th
              className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
              onClick={() => handleSort('total_tokens')}
            >
              总计 Token <SortIcon column="total_tokens" />
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((item) => (
            <tr
              key={item.model}
              className="border-b border-[rgba(0,0,0,0.04)] hover:bg-[rgba(0,0,0,0.02)] transition-colors"
            >
              <td className="py-3 px-2 font-medium text-[#1d1d1f]">{item.model}</td>
              <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono">
                {item.request_count.toLocaleString()}
              </td>
              <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono">
                {item.prompt_tokens.toLocaleString()}
              </td>
              <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono">
                {item.completion_tokens.toLocaleString()}
              </td>
              <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono font-medium">
                {item.total_tokens.toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
