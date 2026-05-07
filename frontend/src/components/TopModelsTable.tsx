import { useState } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import type { AnalyticsTopModelItem } from '../types'

type SortKey = keyof AnalyticsTopModelItem

export function TopModelsTable() {
  const { analyticsTopModels } = useDashboardStore()
  const [sortKey, setSortKey] = useState<SortKey>('total_tokens')
  const [sortAsc, setSortAsc] = useState(false)

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
    if (sortKey !== column) return <span className="text-[#c7c7cc] ml-1">↕</span>
    return <span className="text-[#007AFF] ml-1">{sortAsc ? '▲' : '▼'}</span>
  }

  if (analyticsTopModels.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-5">
        <h3 className="text-sm font-medium text-[#86868b] mb-4">热门模型排行</h3>
        <div className="text-center py-8 text-[#a1a1a6] text-sm">暂无数据</div>
      </div>
    )
  }

  return (
    <div className="glass-card rounded-2xl p-5">
      <h3 className="text-sm font-medium text-[#86868b] mb-4">热门模型排行</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[rgba(0,0,0,0.06)]">
              <th className="text-left py-3 px-2 font-medium text-[#86868b]">排名</th>
              <th
                className="text-left py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
                onClick={() => handleSort('model')}
              >
                模型名 <SortIcon column="model" />
              </th>
              <th
                className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
                onClick={() => handleSort('prompt_tokens')}
              >
                输入 <SortIcon column="prompt_tokens" />
              </th>
              <th
                className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
                onClick={() => handleSort('completion_tokens')}
              >
                输出 <SortIcon column="completion_tokens" />
              </th>
              <th
                className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
                onClick={() => handleSort('reasoning_tokens')}
              >
                推理 <SortIcon column="reasoning_tokens" />
              </th>
              <th
                className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
                onClick={() => handleSort('cached_tokens')}
              >
                缓存 <SortIcon column="cached_tokens" />
              </th>
              <th
                className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
                onClick={() => handleSort('total_tokens')}
              >
                总计 <SortIcon column="total_tokens" />
              </th>
              <th
                className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
                onClick={() => handleSort('cost')}
              >
                成本 <SortIcon column="cost" />
              </th>
              <th
                className="text-right py-3 px-2 font-medium text-[#86868b] cursor-pointer select-none"
                onClick={() => handleSort('request_count')}
              >
                请求数 <SortIcon column="request_count" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item, index) => (
              <tr
                key={item.model}
                className="border-b border-[rgba(0,0,0,0.04)] hover:bg-[rgba(0,0,0,0.02)] transition-colors"
              >
                <td className="py-3 px-2 text-[#86868b] font-mono">{index + 1}</td>
                <td className="py-3 px-2 font-medium text-[#1d1d1f]">{item.model}</td>
                <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono">
                  {item.prompt_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono">
                  {item.completion_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono">
                  {item.reasoning_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono">
                  {item.cached_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono font-medium">
                  {item.total_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono">
                  ¥{item.cost.toFixed(2)}
                </td>
                <td className="py-3 px-2 text-right text-[#1d1d1f] font-mono">
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
