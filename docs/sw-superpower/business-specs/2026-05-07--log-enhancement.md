# 日志功能增强 - 业务需求

## 概述
为 Smart Router 的两种日志（服务日志 smart-router.log 和 Dashboard 日志 dashboard.log）添加时间戳和日志等级，并提供按等级筛选的查看功能。

## 背景与动机
当前日志通过重定向 stdout/stderr 生成，没有统一的时间戳和日志等级格式，导致：
- 无法快速定位问题发生时间
- 无法区分 INFO/DEBUG/WARNING/ERROR 级别
- CLI 和 Web 界面查看日志时缺乏筛选能力

## 用户与角色
- **主要用户**: 系统管理员、开发者
- **使用场景**:
  - 排查服务问题时需要按时间线和等级筛选日志
  - Dashboard 界面查看日志时需要过滤掉大量 INFO 日志，专注 ERROR/WARNING

## 关键约束
- 使用 Python 标准库 `logging`，不引入新依赖
- 后台进程（daemon.py 的 Popen）需正确传递 logging 配置
- 保持向后兼容：旧日志格式的行也能被解析（无时间戳/等级时视为 INFO）
- Dashboard 日志（uvicorn）也需配置格式
- 日志文件路径保持不变（~/.smart-router/smart-router.log 和 dashboard.log）

## 目标
- 服务日志和 Dashboard 日志输出时自带时间戳和日志等级
- CLI `view_logs` 支持按等级筛选（--level 参数）
- Web API `/api/logs` 支持按等级筛选（level 查询参数）
- 日志格式：`2026-05-07 14:23:01,234 - smart_router.gateway.server - INFO - 配置已加载`

## 非目标
- 不实现日志轮转（log rotation）
- 不实现远程日志收集
- 不修改日志存储位置
- 不添加日志搜索功能（仅筛选）

## 方案决策
**选定方案**: 混合方案（使用 Python logging 模块 + 增强查看功能）
**原因**:
- 使用标准 `logging` 模块是 Python 最佳实践
- 天然支持日志等级（DEBUG/INFO/WARNING/ERROR）
- 查看功能可轻松解析等级进行筛选
- 虽然需要改造后台进程启动逻辑，但这是值得的规范化改进

**替代方案**:
1. 自定义格式化包装 — 改动小但不够灵活，难支持等级筛选（已放弃）
2. 仅使用 logging 模块但不增强查看功能 — 无法满足用户"筛选功能"需求（已放弃）

## 关键组件（草案）
1. **日志配置模块** (`core/smart_router/utils/logging_config.py`):
   - `setup_logging(log_file, level=logging.INFO)`：配置 root logger
   - 格式：`%(asctime)s,%(msecs)03d - %(name)s - %(levelname)s - %(message)s`

2. **服务入口改造** (`server_main.py`):
   - 导入并调用 `setup_logging()`，传入日志文件路径

3. **Dashboard 日志配置** (`daemon.py`):
   - uvicorn 的日志配置通过 `uvicorn.Config(log_config=...)` 设置

4. **CLI 查看增强** (`daemon.py` 的 `view_logs`):
   - 新增 `--level` 参数：ALL/DEBUG/INFO/WARNING/ERROR
   - 解析每行日志提取等级，按参数筛选

5. **Web API 增强** (`dashboard_api.py`):
   - 新增 `level` 查询参数
   - 增强 `read_log_lines` 返回结构化数据（含 timestamp、level、message）

## 验收标准（初稿）
- [ ] 新启动的服务日志每行包含 `YYYY-MM-DD HH:MM:SS,mmm - logger.name - LEVEL - message` 格式
- [ ] Dashboard 日志（uvicorn）同样包含时间戳和等级
- [ ] CLI `view_logs --level ERROR` 只显示 ERROR 级别日志
- [ ] CLI `view_logs --level INFO` 显示 INFO 及以上级别（INFO/WARNING/ERROR）
- [ ] Web API `GET /api/logs?level=WARNING` 返回结构化数据中只含 WARNING 及以上
- [ ] 旧日志文件（无时间戳/等级）仍可被读取，解析时标记为 INFO 级别
- [ ] `read_log_lines` 返回的 `structured_lines` 包含 timestamp、level、name、message 字段
- [ ] 单元测试覆盖：日志格式验证、等级筛选逻辑、旧格式兼容解析

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 后台进程 logging 配置不生效 | 日志仍无时间戳/等级 | 在 server_main.py 入口处配置，通过环境变量传递日志文件路径 |
| uvicorn 日志格式配置复杂 | Dashboard 日志格式不符合预期 | 使用 uvicorn 的 log_config 字典配置，参考官方文档 |
| 旧日志解析兼容性 | 旧日志无法被正确显示 | 实现容错解析：无法解析时整个行作为 message，标记为 INFO |
| 性能影响（大量日志解析） | 查看日志时响应慢 | 限制读取行数（默认 500），使用生成器按需解析 |
