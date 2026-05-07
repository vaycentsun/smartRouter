import { useEffect, useRef, useState, useCallback } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import type { LogSource } from '../types'

const LOG_SOURCES: { key: LogSource; label: string }[] = [
  { key: 'service', label: '服务日志' },
  { key: 'dashboard', label: 'Dashboard 日志' },
]

const LOG_LEVELS = [
  { key: 'ALL', label: '全部' },
  { key: 'DEBUG', label: 'DEBUG' },
  { key: 'INFO', label: 'INFO' },
  { key: 'WARNING', label: 'WARNING' },
  { key: 'ERROR', label: 'ERROR' },
]

function getLineColor(line: string): string {
  const upper = line.toUpperCase()
  if (upper.includes('ERROR') || upper.includes('CRITICAL') || upper.includes('FATAL')) {
    return 'text-[#FF3B30]'
  }
  if (upper.includes('WARNING') || upper.includes('WARN')) {
    return 'text-[#FF9500]'
  }
  if (upper.includes('INFO')) {
    return 'text-[#34C759]'
  }
  return 'text-[#e5e5ea]'
}

export function LogsPanel() {
  const { logs, fetchLogs, setLogSource, setLogLevel, logError, clearLogError } = useDashboardStore()
  const [activeSource, setActiveSource] = useState<LogSource>('service')
  const [activeLevel, setActiveLevel] = useState('ALL')
  const [autoScroll, setAutoScroll] = useState(true)
  const containerRef = useRef<HTMLDivElement>(null)
  const prevLinesLength = useRef(0)

  // 初始加载和切换源/等级
  useEffect(() => {
    setLogSource(activeSource)
    setLogLevel(activeLevel)
    fetchLogs(activeSource, activeLevel)
  }, [activeSource, activeLevel])

  // 轮询：每 10 秒获取新日志
  useEffect(() => {
    const interval = setInterval(() => {
      fetchLogs()
    }, 10000)
    return () => clearInterval(interval)
  }, [fetchLogs])

  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll && containerRef.current && logs.lines.length > prevLinesLength.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
    prevLinesLength.current = logs.lines.length
  }, [logs.lines, autoScroll])

  const handleScroll = useCallback(() => {
    if (!containerRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 50
    setAutoScroll(isNearBottom)
  }, [])

  const handleSwitch = (source: LogSource) => {
    if (source === activeSource) return
    setActiveSource(source)
  }

  const handleLevelSwitch = (level: string) => {
    if (level === activeLevel) return
    setActiveLevel(level)
  }

  return (
    <div className="space-y-4">
      {/* Error Alert */}
      {logError && (
        <div className="glass-card rounded-2xl p-4 flex items-center justify-between border border-red-400/20">
          <p className="text-sm text-[#FF3B30]">{logError}</p>
          <button
            onClick={clearLogError}
            className="text-sm text-[#FF3B30] hover:text-[#FF3B30]/70 transition-colors"
          >
            关闭
          </button>
        </div>
      )}

      <div className="glass-card rounded-2xl overflow-hidden">
        {/* Header with source tabs and level filter */}
        <div className="p-4 border-b border-[rgba(0,0,0,0.06)] flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-1 h-5 bg-[#007AFF] rounded-full" />
            <h2 className="text-base font-semibold text-[#1d1d1f] tracking-wide">实时日志</h2>
            <div className="flex gap-1 ml-4">
              {LOG_SOURCES.map((s) => (
                <button
                  key={s.key}
                  onClick={() => handleSwitch(s.key)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                    activeSource === s.key
                      ? 'bg-[rgba(0,122,255,0.08)] text-[#007AFF]'
                      : 'text-[#86868b] hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex gap-1">
              {LOG_LEVELS.map((l) => (
                <button
                  key={l.key}
                  onClick={() => handleLevelSwitch(l.key)}
                  className={`px-2 py-1 rounded-lg text-xs font-medium transition-all ${
                    activeLevel === l.key
                      ? 'bg-[rgba(255,149,0,0.08)] text-[#FF9500]'
                      : 'text-[#86868b] hover:text-[#1d1d1f] hover:bg-[rgba(0,0,0,0.03)]'
                  }`}
                >
                  {l.label}
                </button>
              ))}
            </div>
            <span className="text-xs text-[#86868b] font-mono border-l border-[rgba(0,0,0,0.1)] pl-3">
              {logs.lines.length} 行
            </span>
          </div>
        </div>

        {/* Log content */}
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="bg-[#1c1c1e] p-4 overflow-auto"
          style={{ maxHeight: '60vh', minHeight: '400px' }}
        >
          {logs.lines.length === 0 ? (
            <p className="text-sm text-[#86868b] font-mono text-center py-8">暂无日志</p>
          ) : (
            <div className="space-y-0.5">
              {logs.lines.map((line, index) => (
                <pre
                  key={`${activeSource}-${index}`}
                  className={`text-xs font-mono whitespace-pre-wrap break-all leading-relaxed ${getLineColor(line)}`}
                >
                  {line}
                </pre>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-[rgba(0,0,0,0.06)] flex items-center justify-between">
          <span className="text-xs text-[#86868b]">
            {autoScroll ? '自动滚动中' : '已暂停自动滚动'}
          </span>
          <span className="text-xs text-[#86868b] font-mono">
            offset: {logs.offset} bytes
          </span>
        </div>
      </div>
    </div>
  )
}
