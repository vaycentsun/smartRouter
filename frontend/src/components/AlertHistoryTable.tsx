import { useTranslation } from '../i18n/useTranslation'
import { useDashboardStore } from '../store/useDashboardStore'

export function AlertHistoryTable() {
  const { t, lang } = useTranslation()
  const { alertHistory } = useDashboardStore()

  return (
    <div className="tech-card rounded-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-[#1a1a2e]">
        <div className="flex items-center gap-2">
          <div className="w-1 h-4 bg-[#00d4aa]" />
          <h3 className="text-base font-semibold text-[#e8e8ed] uppercase tracking-wider font-mono">{t('ALERT HISTORY')}</h3>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1a1a2e]">
              <th className="text-left text-[10px] text-[#636366] font-mono uppercase tracking-widest px-6 py-3">{t('TIME')}</th>
              <th className="text-left text-[10px] text-[#636366] font-mono uppercase tracking-widest px-6 py-3">{t('RULE')}</th>
              <th className="text-left text-[10px] text-[#636366] font-mono uppercase tracking-widest px-6 py-3">{t('SEVERITY')}</th>
              <th className="text-left text-[10px] text-[#636366] font-mono uppercase tracking-widest px-6 py-3">{t('METRIC')}</th>
              <th className="text-left text-[10px] text-[#636366] font-mono uppercase tracking-widest px-6 py-3">{t('VALUE / THRESHOLD')}</th>
              <th className="text-left text-[10px] text-[#636366] font-mono uppercase tracking-widest px-6 py-3">{t('MESSAGE')}</th>
            </tr>
          </thead>
          <tbody>
            {alertHistory.map((item, index) => (
              <tr key={index} className="data-row border-b border-[#1a1a2e] last:border-0">
                <td className="px-6 py-3 text-[#e8e8ed] whitespace-nowrap">
                  {new Date(item.timestamp * 1000).toLocaleString(lang === 'zh' ? 'zh-CN' : 'en-US')}
                </td>
                <td className="px-6 py-3 text-[#e8e8ed]">{item.rule_name}</td>
                <td className="px-6 py-3">
                  <span className={`tech-tag ${
                    item.severity === 'critical'
                      ? 'tech-tag-danger'
                      : item.severity === 'warning'
                      ? 'tech-tag-warning'
                      : 'bg-[rgba(52,152,219,0.1)] border-[rgba(52,152,219,0.2)] text-[#3498db]'
                  }`}>
                    {item.severity}
                  </span>
                </td>
                <td className="px-6 py-3 text-[#e8e8ed]">{item.metric}</td>
                <td className="px-6 py-3 text-[#e8e8ed]">
                  {item.current_value} / {item.threshold}
                </td>
                <td className="px-6 py-3 text-[#636366] max-w-xs truncate">{item.message}</td>
              </tr>
            ))}
            {alertHistory.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-sm text-[#636366]">
                  {t('NO ALERT HISTORY')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
