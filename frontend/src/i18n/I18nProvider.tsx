import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

type Lang = 'zh' | 'en'

interface I18nContextType {
  lang: Lang
  setLang: (lang: Lang) => void
  t: (key: string) => string
}

const I18nContext = createContext<I18nContextType>({
  lang: 'zh',
  setLang: () => {},
  t: (key: string) => key,
})

export function useTranslation() {
  return useContext(I18nContext)
}

// 完整翻译字典
const dict: Record<string, Record<Lang, string>> = {
  // ===== App / Header =====
  'Smart Router': { zh: 'Smart Router', en: 'Smart Router' },
  'Gateway Monitor': { zh: '智能模型路由网关', en: 'Intelligent Model Routing Gateway' },
  'ONLINE': { zh: '在线', en: 'ONLINE' },
  'OFFLINE': { zh: '离线', en: 'OFFLINE' },
  'REFRESH': { zh: '刷新', en: 'REFRESH' },
  'STOP': { zh: '停止', en: 'STOP' },
  'START': { zh: '启动', en: 'START' },
  '确定要停止 Smart Router 服务吗？': { zh: '确定要停止 Smart Router 服务吗？', en: 'Stop Smart Router service?' },
  'startHint': { zh: '请在终端中运行以下命令启动服务：\n\nsmart-router start\n\n或\n\nsmr start', en: 'Run in terminal:\n\nsmart-router start\n\nor\n\nsmr start' },
  'DISMISS': { zh: '关闭', en: 'DISMISS' },
  'LANGUAGE': { zh: '语言', en: 'LANG' },

  // ===== Tabs =====
  'DASHBOARD': { zh: '仪表盘', en: 'DASHBOARD' },
  'MODELS': { zh: '模型清单', en: 'MODELS' },
  'ROUTING': { zh: '路由策略', en: 'ROUTING' },
  'ANALYTICS': { zh: '数据分析', en: 'ANALYTICS' },
  'LOGS': { zh: '日志', en: 'LOGS' },
  'ALERTS': { zh: '告警', en: 'ALERTS' },

  // ===== StatsOverview =====
  'Models Total': { zh: '模型总数', en: 'Models Total' },
  'AVAILABLE': { zh: '可用', en: 'AVAILABLE' },
  'Providers': { zh: 'Provider 数', en: 'Providers' },
  'KEY MISSING': { zh: 'Key 缺失', en: 'KEY MISSING' },
  'Service Status': { zh: '服务状态', en: 'Service Status' },
  'RUNNING': { zh: '运行中', en: 'RUNNING' },
  'STOPPED': { zh: '已停止', en: 'STOPPED' },

  // ===== StatusCard =====
  'PID': { zh: 'PID', en: 'PID' },
  'Uptime': { zh: '已运行', en: 'Uptime' },
  'Endpoint': { zh: '服务地址', en: 'Endpoint' },
  'Version': { zh: '版本', en: 'Version' },
  'LOADING': { zh: '加载中...', en: 'LOADING...' },

  // ===== DryRunPanel =====
  'Route Test': { zh: '快速路由测试', en: 'Route Test' },
  'Input Prompt': { zh: '输入提示词', en: 'Input Prompt' },
  'EXECUTE TEST': { zh: '执行测试', en: 'EXECUTE TEST' },
  'TESTING': { zh: '测试中...', en: 'TESTING...' },
  'Routing Result': { zh: '路由结果', en: 'Routing Result' },
  'TASK_TYPE': { zh: '任务类型', en: 'TASK_TYPE' },
  'CONFIDENCE': { zh: '置信度', en: 'CONFIDENCE' },
  'DIFFICULTY': { zh: '难度', en: 'DIFFICULTY' },
  'MODEL': { zh: '选中模型', en: 'MODEL' },
  'STRATEGY': { zh: '策略', en: 'STRATEGY' },
  'SCORE': { zh: '得分', en: 'SCORE' },
  'REASON': { zh: '原因', en: 'REASON' },
  'FALLBACK CHAIN': { zh: 'Fallback 链', en: 'FALLBACK CHAIN' },

  // ===== ErrorStatsPanel =====
  'Error Stats': { zh: '模型错误统计', en: 'Error Stats' },
  'REQUESTS': { zh: '次请求', en: 'REQUESTS' },
  'FAILURE RATE': { zh: '失败率', en: 'FAILURE RATE' },
  'Model Failure Ranking': { zh: '模型失败排行', en: 'Model Failure Ranking' },
  'Model': { zh: '模型', en: 'Model' },
  'Provider': { zh: 'Provider', en: 'Provider' },
  'Attempts': { zh: '尝试', en: 'Attempts' },
  'Failures': { zh: '失败', en: 'Failures' },
  'Success': { zh: '成功率', en: 'Success' },
  'Error Type Distribution': { zh: '错误类型分布', en: 'Error Type Distribution' },
  'Provider Error Distribution': { zh: 'Provider 错误分布', en: 'Provider Error Distribution' },
  'NO DATA': { zh: '暂无数据', en: 'NO DATA' },

  // ===== ModelOverrideBar =====
  'OVERRIDE ON': { zh: '覆盖已启用', en: 'OVERRIDE ON' },
  'AUTO ROUTE': { zh: '自动路由', en: 'AUTO ROUTE' },
  'overridePaused': { zh: '路由策略已暂停，请求将直接发送至', en: 'Routing paused, requests will go to' },
  'overrideHint': { zh: '选择 Provider 和 Model 以绕过路由策略，直接指定目标模型', en: 'Select provider and model to bypass routing' },
  'SELECT': { zh: '请选择', en: 'SELECT' },
  'SELECT PROVIDER': { zh: '先选 Provider', en: 'SELECT PROVIDER' },
  'RESET': { zh: '重置', en: 'RESET' },

  // ===== Analytics =====
  'Total Cost': { zh: '总成本', en: 'Total Cost' },
  'ACCUMULATED': { zh: '累计费用', en: 'ACCUMULATED' },
  'Daily Avg': { zh: '日均成本', en: 'Daily Avg' },
  'PER DAY': { zh: '平均每天', en: 'PER DAY' },
  'Total Requests': { zh: '总请求数', en: 'Total Requests' },
  'API CALLS': { zh: '次 API 调用', en: 'API CALLS' },
  'Total Tokens': { zh: '总 Token 数', en: 'Total Tokens' },
  'CONSUMED': { zh: 'Token 消耗', en: 'CONSUMED' },
  'Input Tokens': { zh: '输入 Token', en: 'Input Tokens' },
  'PROMPT': { zh: 'Prompt 消耗', en: 'PROMPT' },
  'Reasoning Tokens': { zh: '推理 Token', en: 'Reasoning Tokens' },
  'REASONING': { zh: 'Reasoning 消耗', en: 'REASONING' },
  'Output Tokens': { zh: '输出 Token', en: 'Output Tokens' },
  'COMPLETION': { zh: 'Completion 消耗', en: 'COMPLETION' },
  'Cache Hits': { zh: '缓存命中', en: 'Cache Hits' },
  'CACHED': { zh: 'Cached 命中', en: 'CACHED' },
  'Cost Trend': { zh: '成本趋势', en: 'Cost Trend' },
  'Request Trend': { zh: '请求趋势', en: 'Request Trend' },
  'Model Usage': { zh: '模型使用分布', en: 'Model Usage' },
  'Top Models': { zh: '热门模型排行', en: 'Top Models' },
  'PIE': { zh: '饼图', en: 'PIE' },
  'BAR': { zh: '柱状图', en: 'BAR' },
  'Others': { zh: '其他', en: 'Others' },
  'Recent Requests': { zh: '最近请求路由记录', en: 'Recent Requests' },

  // ===== Request table =====
  'Timestamp': { zh: '时间', en: 'Timestamp' },
  'Latency': { zh: '延迟', en: 'Latency' },
  'Tokens': { zh: 'Token', en: 'Tokens' },
  'Cost': { zh: '成本', en: 'Cost' },
  'Status': { zh: '状态', en: 'Status' },
  'Input': { zh: '输入', en: 'Input' },
  'Output': { zh: '输出', en: 'Output' },
  'Reason': { zh: '推理', en: 'Reason' },
  'Cache': { zh: '缓存', en: 'Cache' },
  'Total': { zh: '总计', en: 'Total' },
  'Req': { zh: '请求数', en: 'Req' },

  // ===== Request detail =====
  'TASK TYPE': { zh: '任务类型', en: 'TASK TYPE' },
  'ATTEMPTS': { zh: '尝试回退', en: 'ATTEMPTS' },
  'INPUT TOKENS': { zh: '输入 Token', en: 'INPUT TOKENS' },
  'OUTPUT TOKENS': { zh: '输出 Token', en: 'OUTPUT TOKENS' },
  'REASONING TOKENS': { zh: '推理 Token', en: 'REASONING TOKENS' },
  'CACHE HITS': { zh: '缓存命中', en: 'CACHE HITS' },
  'RETRY HISTORY': { zh: '重试历史', en: 'RETRY HISTORY' },
  'REQUEST ID': { zh: '请求 ID', en: 'REQUEST ID' },
  'ERR': { zh: '异常', en: 'ERR' },

  // ===== ModelsExplorer =====
  'NO PROVIDERS': { zh: '暂无 Provider 数据', en: 'NO PROVIDERS' },
  'CONFIGURED': { zh: '已配置', en: 'CONFIGURED' },
  'MISSING': { zh: '缺失', en: 'MISSING' },
  'EDIT': { zh: '编辑', en: 'EDIT' },
  'CHECK': { zh: '检查连通性', en: 'CHECK' },
  'CHECKING': { zh: '检测中...', en: 'CHECKING...' },
  'API KEY': { zh: 'API Key', en: 'API KEY' },
  'ENV': { zh: '环境变量', en: 'ENV' },
  'NOT SET': { zh: '未设置', en: 'NOT SET' },
  'HIDE': { zh: '隐藏', en: 'HIDE' },
  'SHOW': { zh: '显示', en: 'SHOW' },
  'SAVE': { zh: '保存', en: 'SAVE' },
  'SAVING': { zh: '保存中...', en: 'SAVING...' },
  'saveHint1': { zh: '输入新值覆盖当前 Key，留空保存表示删除', en: 'Enter new value to override, leave empty to delete' },
  'saveHint2': { zh: '输入 Key 并保存以启用该 Provider', en: 'Enter key to enable provider' },
  'NO MODELS': { zh: '该 Provider 暂无模型数据', en: 'NO MODELS' },
  'STATUS': { zh: '状态', en: 'STATUS' },
  'ENABLED': { zh: '启用', en: 'ENABLED' },
  'CTX': { zh: '上下文', en: 'CTX' },
  'TASKS': { zh: '支持任务', en: 'TASKS' },
  'NOT FOUND': { zh: '未上架', en: 'NOT FOUND' },
  'UNCONFIGURED': { zh: '未配置', en: 'UNCONFIGURED' },
  'AUTH ERROR': { zh: 'Key 无效', en: 'AUTH ERROR' },
  'RATE LIMITED': { zh: '频率限制', en: 'RATE LIMITED' },
  'NETWORK ERR': { zh: '网络异常', en: 'NETWORK ERR' },
  'CHECK FAILED': { zh: '检查失败', en: 'CHECK FAILED' },
  'EDIT title': { zh: '编辑 Provider', en: 'EDIT' },
  'API BASE': { zh: 'API Base', en: 'API BASE' },
  'TIMEOUT': { zh: '超时时间', en: 'TIMEOUT' },
  'Leave empty to keep current': { zh: '留空则保持现有配置', en: 'Leave empty to keep current' },
  'CANCEL': { zh: '取消', en: 'CANCEL' },

  // ===== Logs =====
  'SERVICE': { zh: '服务日志', en: 'SERVICE' },
  'DASHBOARD LOG': { zh: 'Dashboard 日志', en: 'DASHBOARD LOG' },
  'ALL': { zh: '全部', en: 'ALL' },
  'DEBUG': { zh: 'DEBUG', en: 'DEBUG' },
  'INFO': { zh: 'INFO', en: 'INFO' },
  'WARN': { zh: 'WARNING', en: 'WARN' },
  'ERROR': { zh: 'ERROR', en: 'ERROR' },
  'Live Logs': { zh: '实时日志', en: 'Live Logs' },
  'LINES': { zh: '行', en: 'LINES' },
  'NO LOGS': { zh: '暂无日志', en: 'NO LOGS' },
  'AUTO SCROLL': { zh: '自动滚动中', en: 'AUTO SCROLL' },
  'PAUSED': { zh: '已暂停自动滚动', en: 'PAUSED' },
  'OFFSET': { zh: '偏移量', en: 'OFFSET' },
  'BYTES': { zh: '字节', en: 'BYTES' },

  // ===== Alerts =====
  'Active Rules': { zh: '活跃规则', en: 'Active Rules' },
  'Total Rules': { zh: '共 {count} 条规则', en: '{count} total rules' },
  'Today Triggers': { zh: '今日触发', en: 'Today Triggers' },
  'Last 24h': { zh: '最近 24 小时', en: 'Last 24h' },
  'Alert Rules': { zh: '告警规则', en: 'Alert Rules' },
  '+ NEW RULE': { zh: '+ 新建规则', en: '+ NEW RULE' },

  // ===== Formula =====
  'Routing Formula': { zh: '策略公式构建器', en: 'Routing Formula' },
  'formulaDesc': { zh: '配置全局评分公式，所有任务类型将统一使用该公式选择最佳模型。', en: 'Configure global scoring formula for model selection.' },
  'Templates': { zh: '预设模板', en: 'Templates' },
  'QUALITY FIRST': { zh: '质量优先', en: 'QUALITY FIRST' },
  'qualityDesc': { zh: '优先选择高质量模型', en: 'Prioritize high quality models' },
  'COST FIRST': { zh: '成本优先', en: 'COST FIRST' },
  'costDesc': { zh: '优先选择便宜模型', en: 'Prioritize cheaper models' },
  'BALANCED': { zh: '均衡', en: 'BALANCED' },
  'balancedDesc': { zh: '质量与成本兼顾', en: 'Balance quality and cost' },
  'Weights': { zh: '能力权重', en: 'Weights' },
  'QUALITY': { zh: '质量', en: 'QUALITY' },
  'qualityDesc2': { zh: '代码质量、推理能力', en: 'Code quality, reasoning' },
  'COST': { zh: '成本', en: 'COST' },
  'costDesc2': { zh: '成本效率（越高越便宜）', en: 'Cost efficiency' },
  'FORMULA': { zh: '当前公式', en: 'FORMULA' },
  'NOT CONFIGURED': { zh: '未配置', en: 'NOT CONFIGURED' },
  'Preview': { zh: '实时预览', en: 'Preview' },
  'Enter test prompt...': { zh: '输入测试 prompt...', en: 'Enter test prompt...' },
  'PREVIEW': { zh: '预览得分', en: 'PREVIEW' },
  'CALCULATING': { zh: '计算中...', en: 'CALCULATING...' },
  'RANKING': { zh: '模型得分排名', en: 'RANKING' },
  'BEST': { zh: '最佳', en: 'BEST' },
  'TEST': { zh: '测试', en: 'TEST' },
  'Playground': { zh: 'Playground 验证', en: 'Playground' },
  'CLOSE': { zh: '收起', en: 'CLOSE' },
  'MODELS (MAX 3)': { zh: '选择模型（最多3个）', en: 'MODELS (MAX 3)' },
  'RUN TEST': { zh: '运行测试', en: 'RUN TEST' },
  'LOAD FAILED': { zh: '加载公式失败', en: 'LOAD FAILED' },
  'ENTER TEST PROMPT': { zh: '请输入测试 prompt', en: 'ENTER TEST PROMPT' },
  'PREVIEW FAILED': { zh: '预览失败', en: 'PREVIEW FAILED' },
  'FORMULA SAVED': { zh: '公式已保存并应用', en: 'FORMULA SAVED' },
  'SAVE FAILED': { zh: '保存失败', en: 'SAVE FAILED' },
  'UNKNOWN': { zh: '未知错误', en: 'UNKNOWN' },

  // ===== Playground =====
  'PlaygroundPage title': { zh: '模型 Playground', en: 'Model Playground' },
  'PlaygroundPage desc': { zh: '在此测试不同模型的响应效果', en: 'Test different model responses here' },
  'Single': { zh: '单模型', en: 'Single' },
  'Compare': { zh: '对比模式', en: 'Compare' },
  'Select mode': { zh: '选择模式', en: 'Select mode' },
  'Select model': { zh: '选择模型', en: 'Select model' },
  'Select models': { zh: '选择模型（最多3个）', en: 'Select models (max 3)' },
  'Enter prompt...': { zh: '输入提示词...', en: 'Enter prompt...' },
  'SUBMIT': { zh: '提交', en: 'SUBMIT' },
  'Result': { zh: '结果', en: 'Result' },
  'Compare Results': { zh: '对比结果', en: 'Compare Results' },
  'ms': { zh: '毫秒', en: 'ms' },
  'Prompt Tokens': { zh: '输入 Token', en: 'Prompt Tokens' },
  'Completion Tokens': { zh: '输出 Token', en: 'Completion Tokens' },
  'Estimated Cost': { zh: '预估成本', en: 'Estimated Cost' },
  'Routing Info': { zh: '路由信息', en: 'Routing Info' },
  'Selected Model': { zh: '选中模型', en: 'Selected Model' },
  'Task Type': { zh: '任务类型', en: 'Task Type' },
  'Score': { zh: '得分', en: 'Score' },

  // ===== Footer =====

  // ===== Model Mappings =====
  'MAPPINGS': { zh: '模型映射', en: 'MAPPINGS' },
  'Model Mapping': { zh: '模型映射', en: 'Model Mapping' },
  'Mapping applies to both chat/completions and responses endpoints': { zh: '映射规则同时适用于 /v1/chat/completions 和 /v1/responses 端点', en: 'Mapping rules apply to both /v1/chat/completions and /v1/responses endpoints' },
  'Global Enabled': { zh: '全局启用', en: 'Global Enabled' },
  'From Model': { zh: '源模型', en: 'From Model' },
  'To Model': { zh: '目标模型', en: 'To Model' },
  'To Provider': { zh: '目标 Provider', en: 'To Provider' },
  'To Base URL': { zh: '目标 Base URL', en: 'To Base URL' },
  'To API Key': { zh: '目标 API Key', en: 'To API Key' },
  'Add Mapping': { zh: '添加映射', en: 'Add Mapping' },
  'Edit Mapping': { zh: '编辑映射', en: 'Edit Mapping' },
  'Delete Mapping': { zh: '删除映射', en: 'Delete Mapping' },
  'YAML Editor': { zh: 'YAML 编辑器', en: 'YAML Editor' },
  'Table View': { zh: '表格视图', en: 'Table View' },
  'No mappings configured': { zh: '暂无映射规则', en: 'No mappings configured' },

  // ===== Missing keys for new components =====
  'MODE': { zh: '模式', en: 'MODE' },
  'NO MODELS AVAILABLE': { zh: '暂无可用模型', en: 'NO MODELS AVAILABLE' },
  'Delete this alert rule?': { zh: '删除此告警规则？', en: 'Delete this alert rule?' },
  'NAME': { zh: '名称', en: 'NAME' },
  'METRIC': { zh: '指标', en: 'METRIC' },
  'CONDITION': { zh: '条件', en: 'CONDITION' },
  'SEVERITY': { zh: '严重级别', en: 'SEVERITY' },
  'ACTIONS': { zh: '操作', en: 'ACTIONS' },
  'DELETE': { zh: '删除', en: 'DELETE' },
  'DELETING...': { zh: '删除中...', en: 'DELETING...' },
  'NO ALERT RULES': { zh: '暂无告警规则', en: 'NO ALERT RULES' },
  'EDIT ALERT RULE': { zh: '编辑告警规则', en: 'EDIT ALERT RULE' },
  'NEW ALERT RULE': { zh: '新建告警规则', en: 'NEW ALERT RULE' },
  'RULE ID': { zh: '规则 ID', en: 'RULE ID' },
  'RULE NAME': { zh: '规则名称', en: 'RULE NAME' },
  'OPERATOR': { zh: '运算符', en: 'OPERATOR' },
  'THRESHOLD': { zh: '阈值', en: 'THRESHOLD' },
  'TIME WINDOW': { zh: '时间窗口', en: 'TIME WINDOW' },
  'COOLDOWN (MIN)': { zh: '冷却时间（分钟）', en: 'COOLDOWN (MIN)' },
  'NOTIFICATION CHANNELS': { zh: '通知渠道', en: 'NOTIFICATION CHANNELS' },
  'LOG': { zh: '日志', en: 'LOG' },
  'WEBHOOK': { zh: 'Webhook', en: 'WEBHOOK' },
  '+ ADD CHANNEL': { zh: '+ 添加渠道', en: '+ ADD CHANNEL' },
  'TRIGGERED': { zh: '已触发', en: 'TRIGGERED' },
  'NOT TRIGGERED': { zh: '未触发', en: 'NOT TRIGGERED' },
  'TEST FAILED': { zh: '测试失败', en: 'TEST FAILED' },
  'CREATE': { zh: '创建', en: 'CREATE' },
  'TEST RULE': { zh: '测试规则', en: 'TEST RULE' },
  '1 DAY': { zh: '1 天', en: '1 DAY' },
  '7 DAYS': { zh: '7 天', en: '7 DAYS' },
  '30 DAYS': { zh: '30 天', en: '30 DAYS' },
  'ALERT HISTORY': { zh: '告警历史', en: 'ALERT HISTORY' },
  'TIME': { zh: '时间', en: 'TIME' },
  'RULE': { zh: '规则', en: 'RULE' },
  'VALUE / THRESHOLD': { zh: '当前值 / 阈值', en: 'VALUE / THRESHOLD' },
  'MESSAGE': { zh: '消息', en: 'MESSAGE' },
  'NO ALERT HISTORY': { zh: '暂无告警历史', en: 'NO ALERT HISTORY' },
  '模型消耗明细': { zh: '模型消耗明细', en: 'Model Consumption' },
  'Token 分布': { zh: 'Token 分布', en: 'Token Distribution' },
  'TOTAL REQUESTS': { zh: '总请求数', en: 'TOTAL REQUESTS' },
  'TOTAL PROMPT': { zh: '总 Prompt', en: 'TOTAL PROMPT' },
  'PROMPT TOKENS': { zh: 'Prompt Token', en: 'PROMPT TOKENS' },
  'TOTAL COMPLETION': { zh: '总 Completion', en: 'TOTAL COMPLETION' },
  'COMPLETION TOKENS': { zh: 'Completion Token', en: 'COMPLETION TOKENS' },
  'CACHED TOKENS': { zh: 'Cached Token', en: 'CACHED TOKENS' },
  'NO DATA. SEND REQUESTS TO GENERATE STATISTICS.': { zh: '暂无数据。发送请求以生成统计。', en: 'NO DATA. SEND REQUESTS TO GENERATE STATISTICS.' },
  'Token': { zh: 'Token', en: 'Token' },
  'SEARCH MODELS...': { zh: '搜索模型...', en: 'SEARCH MODELS...' },
  'CONTEXT': { zh: '上下文', en: 'CONTEXT' },
  'DISABLED': { zh: '已禁用', en: 'DISABLED' },
  'NO MATCHING MODELS': { zh: '无匹配模型', en: 'NO MATCHING MODELS' },
  'NO MODEL DATA. CHECK CONFIGURATION.': { zh: '暂无模型数据。请检查配置。', en: 'NO MODEL DATA. CHECK CONFIGURATION.' },
  'ADD MODEL': { zh: '添加模型', en: 'ADD MODEL' },
  'LITELLM MODEL': { zh: 'LiteLLM 模型', en: 'LITELLM MODEL' },
  'SUPPORTED TASKS': { zh: '支持任务', en: 'SUPPORTED TASKS' },
  'ADDING...': { zh: '添加中...', en: 'ADDING...' },
  'Name is required': { zh: '名称不能为空', en: 'Name is required' },
  'LiteLLM model is required': { zh: 'LiteLLM 模型不能为空', en: 'LiteLLM model is required' },
  'Quality must be 1-10': { zh: '质量必须在 1-10 之间', en: 'Quality must be 1-10' },
  'Cost must be 1-10': { zh: '成本必须在 1-10 之间', en: 'Cost must be 1-10' },
  'Context must be positive': { zh: '上下文必须为正整数', en: 'Context must be positive' },
  'At least one task required': { zh: '至少需要一个支持的任务类型', en: 'At least one task required' },
  'LAT': { zh: '延迟', en: 'LAT' },
  'EST COST': { zh: '预估成本', en: 'EST COST' },
  'RETRY': { zh: '重试', en: 'RETRY' },
  'SUCCESS': { zh: '成功', en: 'SUCCESS' },
  'PROVIDERS': { zh: 'Providers', en: 'PROVIDERS' },
  'NO PROVIDER DATA': { zh: '暂无 Provider 数据', en: 'NO PROVIDER DATA' },
  'SAVE CHANGES': { zh: '保存更改', en: 'SAVE CHANGES' },
  'KEY CONFIGURED': { zh: 'Key 已配置', en: 'KEY CONFIGURED' },
  'NO API KEY': { zh: '无 API Key', en: 'NO API KEY' },
}

function lookup(key: string, lang: Lang): string {
  const entry = dict[key]
  if (!entry) return key
  return entry[lang] || entry['zh'] || key
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    const saved = localStorage.getItem('sr-lang')
    return (saved === 'en' ? 'en' : 'zh') as Lang
  })

  const setLang = useCallback((l: Lang) => {
    localStorage.setItem('sr-lang', l)
    setLangState(l)
  }, [])

  const t = useCallback(
    (key: string) => lookup(key, lang),
    [lang]
  )

  return (
    <I18nContext.Provider value={{ lang, setLang, t }}>
      {children}
    </I18nContext.Provider>
  )
}
