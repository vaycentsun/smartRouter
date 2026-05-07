# 配置热重载 + 测试覆盖率提升 设计文档

**日期**: 2026-04-27
**范围**: Smart Router 核心优化（第5-6批）

---

## 1. 配置热重载

### 目标
修改 `providers.yaml`、`models.yaml`、`routing.yaml` 后，运行中的 Smart Router 服务自动重新加载配置，无需重启。

### 架构

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  ConfigWatcher  │────▶│  ConfigLoader    │────▶│  SmartRouter    │
│  (watchdog)     │     │  (reload)        │     │  (update)       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### 组件

**`src/smart_router/config/watcher.py`** (新建)
- `ConfigWatcher` 类：基于 `watchdog.observers.Observer`
- 监听配置目录下的 `*.yaml` 变更
- 去抖动：500ms 内多次变更合并为一次重载
- 重载成功/失败时通过回调通知

**修改 `src/smart_router/router/plugin.py`**
- `SmartRouter.reload_config(config: Config)` 方法：
  - 更新 `sr_config`
  - 重建 classifier、selector
  - 重建 LiteLLM model_list 和 fallbacks
  - 调用父类 `Router` 的更新接口（如可用）

**修改 `src/smart_router/gateway/server.py`**
- `start_server()` 中启动 `ConfigWatcher`
- 配置变更回调中调用 `router.reload_config()`

### 边界情况
- YAML 语法错误时保留旧配置，打印错误日志
- 新配置验证失败时不切换
- 服务停止时正确关闭 observer

---

## 2. 测试覆盖率提升

### 目标
运行 `pytest --cov` 找出未覆盖代码路径，补充测试用例。

### 范围
- 所有 `src/smart_router/` 下的 Python 模块
- 重点关注异常分支、边界条件

### 工具
- `pytest-cov`（已安装）
- 终端输出即可，不生成 HTML 报告

---

## 确认

用户已确认：
- ✅ 热重载范围：3个 YAML 配置文件
- ✅ 触发方式：watchdog 文件系统监听（自动）
- ✅ 测试覆盖：尽可能提高，不需要报告
