import { useEffect, useRef, useState, useCallback } from 'react'
import { useDashboardStore } from '../store/useDashboardStore'
import type { LogSource } from '../types'
import { useTranslation } from '../i18n/I18nProvider'

const LOG_SOURCES: { key: LogSource; label: string }[] = [
  { key: 'service', label: 'SERVICE' },
  { key: 'dashboard', label: 'DASHBOARD log' },
]

const LOG_LEVELS = [
  { key: 'ALL', label: 'ALL' },
  { key: 'DEBUG', label: 'DEBUG' },
  { key: 'INFO', label: 'INFO' },
  { key: 'WARNING', label: 'WARN' },
  { key: 'ERROR', label: 'ERROR' },
]

function getLineColor(line: string): string {
  const upper = line.toUpperCase()
  if (upper.includes('ERROR') || upper.includes('CRITICAL') || upper.includes('FATAL')) {
    return 'text-[#e74c3c]'
  }
  if (upper.includes('WARNING') || upper.includes('WARN')) {
    return 'text-[#f39c12]'
  }
  if (upper.includes('INFO')) {
    return 'text-[#00d4aa]'
  }
  return 'text-[#8e8e93]'
}

export function LogsPanel() {
  const { t } = useTranslation()
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
        <div className="tech-card rounded-sm p-4 flex items-center justify-between border border-[rgba(231,76,60,0.2)]">
          <p className="text-sm text-[#e74c3c] font-mono">{logError}</p>
          <button
            onClick={clearLogError}
            className="text-sm text-[#e74c3c] hover:opacity-70 transition-opacity font-mono uppercase"
          >
            {t('DISMISS')}
          </button>
        </div>
      )}

      <div className="tech-card rounded-sm overflow-hidden">
        {/* Header with source tabs and level filter */}
        <div className="p-4 border-b border-[#1a1a2e] flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-4">
            <div className="w-1 h-4 bg-[#00d4aa]" />
            <h2 className="text-sm font-semibold text-[#e8e8ed] font-mono uppercase tracking-wider">{t('Live Logs')}</h2>
            <div className="flex gap-1 ml-4">
              {LOG_SOURCES.map((s) => (
                <button
                  key={s.key}
                  onClick={() => handleSwitch(s.key)}
                  className={`px-3 py-1 rounded-sm text-xs font-mono uppercase tracking-wider transition-all ${
                    activeSource === s.key
                      ? 'tech-tab-active'
                      : 'tech-tab'
                  }`}
                >
                  {t(s.label)}
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
                  className={`px-2 py-1 rounded-sm text-xs font-mono uppercase tracking-wider transition-all ${
                    activeLevel === l.key
                      ? 'bg-[rgba(243,156,18,0.08)] text-[#f39c12] border border-[rgba(243,156,18,0.15)]'
                      : 'text-[#636366] hover:text-[#8e8e93]'
                  }`}
                >
                  {t(l.label)}
                </button>
              ))}
            </div>
            <span className="text-xs text-[#636366] font-mono border-l border-[#1a1a2e] pl-3">
              {logs.lines.length} {t('LINES')}
            </span>
          </div>
        </div>

        {/* Log content */}
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="bg-[#0a0a0f] p-4 overflow-auto border-b border-[#1a1a2e]"
          style={{ maxHeight: '60vh', minHeight: '400px' }}
        >
          {logs.lines.length === 0 ? (
            <p className="text-sm text-[#636366] font-mono text-center py-8">{t('NO LOGS')}</p>
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
        <div className="px-4 py-2 flex items-center justify-between">
          <span className="text-xs text-[#636366] font-mono">
            {autoScroll ? t('AUTO SCROLL') : t('PAUSED')}
          </span>
          <span className="text-xs text-[#636366] font-mono">
            {t('OFFSET')}: {logs.offset} {t('BYTES')}
          </span>
        </div>
      </div>
    </div>
  )
}
