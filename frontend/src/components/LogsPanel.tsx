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
    return 'text-[#E65C5C]'
  }
  if (upper.includes('WARNING') || upper.includes('WARN')) {
    return 'text-[#8B6F18]'
  }
  if (upper.includes('INFO')) {
    return 'text-[#00A34D]'
  }
  return 'text-[#889397]'
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
        <div className="card-base rounded-xl p-4 flex items-center justify-between border border-[#E65C5C]/20 bg-[#FDECEC]">
          <p className="text-sm text-[#E65C5C] font-medium">{logError}</p>
          <button
            onClick={clearLogError}
            className="text-sm text-[#E65C5C] hover:opacity-70 transition-opacity font-medium uppercase"
          >
            {t('DISMISS')}
          </button>
        </div>
      )}

      <div className="card-base rounded-xl overflow-hidden">
        {/* Header with source tabs and level filter */}
        <div className="p-4 border-b border-[#E8EDEB] flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-4">
            <div className="w-1 h-5 bg-[#00A34D] rounded-full" />
            <h2 className="text-sm font-semibold text-[#001E2B] uppercase tracking-wider">{t('Live Logs')}</h2>
            <div className="flex gap-1 ml-4">
              {LOG_SOURCES.map((s) => (
                <button
                  key={s.key}
                  onClick={() => handleSwitch(s.key)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                    activeSource === s.key
                      ? 'bg-[#001E2B] text-white'
                      : 'text-[#889397] hover:text-[#5C6C75] hover:bg-[#F4F7F6]'
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
                  className={`px-2 py-1 rounded-full text-xs font-medium transition-all ${
                    activeLevel === l.key
                      ? 'bg-[#FEF8E8] text-[#8B6F18]'
                      : 'text-[#889397] hover:text-[#5C6C75]'
                  }`}
                >
                  {t(l.label)}
                </button>
              ))}
            </div>
            <span className="text-xs text-[#889397] border-l border-[#E8EDEB] pl-3">
              {logs.lines.length} {t('LINES')}
            </span>
          </div>
        </div>

        {/* Log content */}
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="bg-[#001E2B] p-4 overflow-auto border-b border-[#3D4F58]"
          style={{ maxHeight: '60vh', minHeight: '400px' }}
        >
          {logs.lines.length === 0 ? (
            <p className="text-sm text-[#889397] text-center py-8">{t('NO LOGS')}</p>
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
          <span className="text-xs text-[#889397]">
            {autoScroll ? t('AUTO SCROLL') : t('PAUSED')}
          </span>
          <span className="text-xs text-[#889397]">
            {t('OFFSET')}: {logs.offset} {t('BYTES')}
          </span>
        </div>
      </div>
    </div>
  )
}
