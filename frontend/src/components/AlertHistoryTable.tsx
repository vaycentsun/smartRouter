import { useTranslation } from '../i18n/I18nProvider'
import { useDashboardStore } from '../store/useDashboardStore'

export function AlertHistoryTable() {
  const { t } = useTranslation()
  const { alertHistory } = useDashboardStore()

  return (
    <div className="card-base rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-[#E8EDEB]">
        <div className="flex items-center gap-2">
          <div className="w-1 h-4 bg-[#00A34D]" />
          <h3 className="text-base font-semibold text-[#001E2B]">{t('ALERT HISTORY')}</h3>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#E8EDEB]">
              <th className="text-left text-[10px] text-[#889397] font-medium px-6 py-3">{t('TIME')}</th>
              <th className="text-left text-[10px] text-[#889397] font-medium px-6 py-3">{t('RULE')}</th>
              <th className="text-left text-[10px] text-[#889397] font-medium px-6 py-3">{t('SEVERITY')}</th>
              <th className="text-left text-[10px] text-[#889397] font-medium px-6 py-3">{t('METRIC')}</th>
              <th className="text-left text-[10px] text-[#889397] font-medium px-6 py-3">{t('VALUE / THRESHOLD')}</th>
              <th className="text-left text-[10px] text-[#889397] font-medium px-6 py-3">{t('MESSAGE')}</th>
            </tr>
          </thead>
          <tbody>
            {alertHistory.map((item, index) => (
              <tr key={index} className="data-row border-b border-[#E8EDEB] last:border-0">
                <td className="px-6 py-3 text-[#001E2B] whitespace-nowrap">
                  {new Date(item.timestamp * 1000).toLocaleString('zh-CN')}
                </td>
                <td className="px-6 py-3 text-[#001E2B]">{item.rule_name}</td>
                <td className="px-6 py-3">
                  <span className={`tech-tag ${
                    item.severity === 'critical'
                      ? 'tech-tag-danger'
                      : item.severity === 'warning'
                      ? 'tech-tag-warning'
                      : 'bg-[rgba(47,135,252,0.1)] border-[rgba(47,135,252,0.2)] text-[#2F87FC]'
                  }`}>
                    {item.severity}
                  </span>
                </td>
                <td className="px-6 py-3 text-[#001E2B]">{item.metric}</td>
                <td className="px-6 py-3 text-[#001E2B]">
                  {item.current_value} / {item.threshold}
                </td>
                <td className="px-6 py-3 text-[#889397] max-w-xs truncate">{item.message}</td>
              </tr>
            ))}
            {alertHistory.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-sm text-[#889397]">
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
