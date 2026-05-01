# Token 统计功能 Spec

**日期**: 2026-04-30
**功能**: Dashboard Token 统计（按模型展示消耗量）
**状态**: 设计已批准，待实现

---

## 1. 需求概述

在 Dashboard 前端增加 Token 统计功能，展示每个模型的 token 消耗量（输入/输出/总计）、请求次数。数据跨服务运行周期持久化存储。

## 2. 设计方案

### 2.1 后端存储方案（已批准：方案 B）

- **存储文件**: `~/.smart-router/token_stats.json`
- **文件 Schema 示例**:
  ```json
  {
    "version": 1,
    "records": {
      "gpt-4o": {
        "prompt_tokens": 15000,
        "completion_tokens": 5000,
        "total_tokens": 20000,
        "request_count": 100
      }
    },
    "_meta": {
      "last_updated": "2026-04-30T12:00:00Z"
    }
  }
  ```
- **持久化方式**: 原子写入（先写 `.tmp` 再 `os.replace`）
- **并发保护**: `asyncio.Lock` 保护**单进程内**（`server.py` 内部）的并发写入；跨进程（`server.py` 与 `dashboard_api.py`）的并发安全依赖原子写入（`os.replace`）
- **启动加载**: 服务启动时自动读取历史数据
- **实例挂载**: 在 `server.py` 的 `start_server()` 中初始化 `TokenStats` 实例，通过 `app.state.token_stats` 挂载为全局单例，中间件通过 `request.app.state.token_stats` 访问
- **Dashboard API 读取方式**: `dashboard_api.py` 中的 `GET /api/token-stats` handler **独立实例化 TokenStats**（从同一 JSON 文件读取），不依赖 server.py 的内存实例。两个进程通过共享文件进行数据交换

### 2.2 数据采集

在 `SmartRouterMiddleware.dispatch()` 的响应阶段拦截 `/v1/chat/completions` 响应：
1. **确定统计模型名**：
   - 优先检查 `request.state.smart_router_selected`（智能路由选择的模型，见 `server.py:100`）
   - 若不存在，检查 `request.state.smart_router_override_model`（用户强制覆盖的模型，见 `server.py:59`）
   - 若两者都不存在，使用请求体中的原始 `model` 字段（用户直接请求的具体模型名）
   - 若仍无法获取，跳过统计
2. **响应 body 捕获方案**：循环消费 `response.body_iterator` 的全部 chunks，拼接为完整 body bytes，然后解析 JSON。流式响应第一期暂不处理（检测到 `text/event-stream` Content-Type 时直接跳过，不消费 body）
3. 解析响应 body 中的 `usage.prompt_tokens` / `usage.completion_tokens` / `usage.total_tokens`
4. 调用 `TokenStats.record()` 累加并**每请求实时原子写入** JSON 文件
5. 使用收集到的 body 重新构建一个新的 `Response` 对象返回给客户端，**完整继承原始 response 的 `status_code`、`headers`（包括 `Content-Type`）、`media_type`**，确保下游正常消费 body
6. 流式响应第一期暂不处理，标记为后续扩展

**降级策略**：
- `usage` 字段缺失：跳过统计，不影响主流程
- 文件损坏/无法读取：初始化空数据，记录 warning
- 统计写入异常（磁盘满、权限错误等）：捕获异常并记录 warning，**绝不阻塞主响应流程**
- 模型名无法获取：跳过统计

### 2.3 后端 API

- `GET /api/token-stats`
  ```json
  {
    "stats": [
      {
        "model": "gpt-4o",
        "prompt_tokens": 45000,
        "completion_tokens": 12000,
        "total_tokens": 57000,
        "request_count": 100
      }
    ],
    "total_prompt_tokens": 45000,
    "total_completion_tokens": 12000,
    "total_requests": 100
  }
  ```

> 注：当前需求不涉及重置/清零统计数据的功能，因此不设计 `POST /api/token-stats/reset` 接口。

### 2.4 前端 UI

新增独立页面，包含三个组件：

1. **TokenStatsOverview**: 顶部三卡片（总请求数、总输入 Token、总输出 Token）
2. **TokenStatsTable**: 模型明细表格，支持前端内存排序（点击表头切换升/降序），按 `request_count`、`prompt_tokens`、`completion_tokens`、`total_tokens` 排序
3. **TokenStatsChart**: Recharts 饼图，展示各模型 total_tokens 占比

**数据刷新策略**：前端每 5 秒轮询 `GET /api/token-stats`（与 Dashboard Store 现有 `fetchAll` 轮询机制一致）

导航入口：App.tsx Tab 导航新增第四个标签"Token 统计"。

## 3. 新增/修改文件

### 后端
| 文件 | 动作 | 说明 |
|------|------|------|
| `core/smart_router/utils/token_stats.py` | 新建 | TokenStats 类：加载/记录/保存/重置 |
| `core/smart_router/gateway/server.py` | 修改 | 中间件响应阶段增加 usage 拦截逻辑 |
| `core/smart_router/gateway/dashboard_api.py` | 修改 | 新增 `token_stats` API handler 和路由注册 |
| `core/smart_router/utils/tests/test_token_stats.py` | 新建 | TokenStats 单元测试 |
| `core/smart_router/gateway/tests/test_dashboard_api.py` | 修改 | 补充 token-stats API 测试 |
| `core/smart_router/gateway/tests/test_server.py` | 修改 | 补充中间件 usage 拦截测试 |

### 前端
| 文件 | 动作 | 说明 |
|------|------|------|
| `frontend/src/types/index.ts` | 修改 | 新增 TokenStatsItem, TokenStatsResponse |
| `frontend/src/api/client.ts` | 修改 | 新增 getTokenStats API 方法 |
| `frontend/src/store/useDashboardStore.ts` | 修改 | 新增 tokenStats 状态和 fetchTokenStats action |
| `frontend/src/App.tsx` | 修改 | Tab 导航新增"Token 统计"标签 |
| `frontend/src/components/TokenStatsPage.tsx` | 新建 | 页面容器 |
| `frontend/src/components/TokenStatsOverview.tsx` | 新建 | 顶部统计卡片 |
| `frontend/src/components/TokenStatsTable.tsx` | 新建 | 明细表格 |
| `frontend/src/components/TokenStatsChart.tsx` | 新建 | Recharts 饼图 |
| `frontend/src/components/TokenStatsPage.test.tsx` | 新建 | 页面集成测试 |
| `frontend/src/components/TokenStatsTable.test.tsx` | 新建 | 表格单元测试 |

## 4. 验收标准

- [ ] 后端：非流式 chat/completions 请求的 usage 被正确累加到 `token_stats.json`
- [ ] 后端：`GET /api/token-stats` 返回正确格式的 JSON
- [ ] 后端：服务重启后历史数据不丢失
- [ ] 后端：并发请求不造成数据损坏或丢失
- [ ] 前端：Tab 导航中出现"Token 统计"标签
- [ ] 前端：页面展示三卡片总览、明细表格、饼图
- [ ] 前端：表格支持按各列排序
- [ ] 前端：数据自动刷新（与 Dashboard 相同的 5 秒间隔）
- [ ] 测试：后端单元测试全部通过
- [ ] 测试：前端测试全部通过

## 5. 已知限制（后续扩展）

- **流式响应**: 第一期仅支持非流式请求。流式 SSE 响应的 usage 在最后一个 chunk 中，需要特殊处理
- **时间维度**: 当前仅按模型聚合，不区分时间区间。后续可按日/周/月统计
- **费用估算**: 当前只统计 token 数量，不计算实际费用（需要各模型的单价表）
