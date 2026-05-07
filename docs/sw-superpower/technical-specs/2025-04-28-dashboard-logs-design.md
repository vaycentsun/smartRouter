# Dashboard 日志 Tab 设计文档

> **日期**: 2025-04-28
> **状态**: 已批准

## 目标

在 Dashboard Web 管理界面新增"日志" Tab，展示 Smart Router 主服务（`smart-router.log`）和 Dashboard 自身（`dashboard.log`）的实时日志内容。

## 架构

采用**轮询 API 方案**：前端每 10 秒请求后端一次，仅获取新增日志行，追加渲染。实现简单、无持久连接、兼容所有环境。

## 数据流

```
App mount → startLogPolling()
                ↓
         每10秒: GET /api/logs?source=service&offset=N
                ↓
         后端读取文件 offset 之后的新行
                ↓
         前端追加到 lines[]，offset 更新为 total_size
                ↓
         LogsPanel 渲染新增行，自动滚动到底部
```

## 组件设计

### 后端 API

**`GET /api/logs`**

| 参数 | 类型 | 说明 |
|------|------|------|
| `source` | string | `service` 或 `dashboard` |
| `offset` | int | 已读取的字节数，首次为 0 |
| `limit` | int | 最大返回行数，默认 500 |

**响应：**
```json
{
  "lines": ["INFO: ...", "ERROR: ..."],
  "offset": 1024,
  "total_size": 2048
}
```

**实现要点：**
- 两个日志文件路径从 `daemon.py` 已定义的常量复用：
  - `DEFAULT_PID_DIR / "smart-router.log"`
  - `DEFAULT_PID_DIR / "dashboard.log"`
- **安全边界**：`source` 参数严格校验，只允许 `service` 或 `dashboard`，拒绝任何包含 `..` 或绝对路径的值
- 文件不存在时返回 `lines: []`，不报错
- 文件被清空/轮转时（offset > total_size），重置 offset 为 0，返回从文件开头开始的 `limit` 行
- 文件过大时依然只返回 offset 之后的内容，不限制总大小

### 前端

**修改 `App.tsx`：**
- `activeTab` 类型扩展为 `'dashboard' | 'models' | 'logs'`
- Tab 导航区新增"日志"按钮（带文件文本图标）

**新增 `LogsPanel.tsx`：**
- 顶部提供两个子 Tab 切换：**服务日志** / **Dashboard 日志**
- 主体为等宽字体（`font-mono`）的只读日志区域，深色背景模拟终端风格
- 自动滚动到底部（用户可手动滚动暂停自动滚动）
- ERROR 级别行显示红色，WARNING 黄色（简单正则匹配前缀）

**修改 `useDashboardStore.ts`：**
- 新增 `logs` 状态（当前源的日志行数组 + offset）
- 新增 `fetchLogs(source)` action
- 新增 `startLogPolling()` / `stopLogPolling()`，10 秒间隔，与现有的 `fetchAll` 5 秒轮询独立运行

## 错误处理

- 文件读取失败：后端返回 `lines: []`，前端显示"暂无日志"
- 网络请求失败：不重试，等待下一个 10 秒周期
- 快速切换 Tab：取消上一个源的轮询，避免竞态条件

## 安全与隐私

- API 严格限制只能读取白名单中的两个日志文件
- 日志中可能包含用户请求内容，Dashboard 默认绑定 `127.0.0.1`，仅限本地访问
- 日志查看功能不需要额外的认证（Dashboard 本身已有 Master Key 保护）

## 测试策略

- 后端：单元测试覆盖正常读取、文件不存在、offset 越界、非法 source 参数
- 前端：组件测试覆盖 Tab 切换、日志渲染、自动滚动
