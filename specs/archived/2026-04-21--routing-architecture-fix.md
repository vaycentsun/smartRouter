---
name: routing-architecture-fix
description: "修复 Pydantic v2 fallback 链、统一双重路由架构、实现 LiteLLM fallback 重试"
---

# 路由架构修复与 Fallback 重试实现

## 概述

修复 Smart Router 核心的三个架构缺陷：Pydantic v2 兼容性导致的 fallback 链失效、`server.py` 中间件与 `plugin.py` 重复路由逻辑、以及 fallback 重试机制未闭环。

## 背景与动机

在代码审查中发现以下问题：

1. **Pydantic v2 `model_post_init` 不生效**：`Config` 类使用 `model_post_init(self, __context)` 预计算 fallback 链，但 Pydantic v2 的 `BaseModel` 不会自动调用此方法，导致 `_fallback_chains` 永远是空字典，`get_fallback_chain()` 完全失效。

2. **双重路由逻辑重复**：`server.py` 的 FastAPI 中间件内嵌了完整的路由决策逻辑（解析 markers → 分类任务 → 估算上下文 → 选择模型），而 `plugin.py` 的 `SmartRouter.get_available_deployment()` 也包含相同逻辑。中间件修改请求体后，`get_available_deployment()` 看到具体模型名直接短路到父类，导致两处逻辑相互覆盖、维护困难。

3. **Fallback 重试未闭环**：`plugin.py` 定义了 `get_fallback_chain()` 并基于 quality 相似度自动推导 fallback 链，但 `SmartRouter.__init__` 从未将这些链注入 LiteLLM Router。LiteLLM 原生支持 `fallbacks` 参数，但当前未配置，导致「自动降级」只是纸上谈兵。

## 目标

- 修复 `Config` 的 fallback 链预计算，使其在 Pydantic v2 下正确初始化
- 将路由决策逻辑提取为 `SmartRouter` 的公共方法，中间件与 `get_available_deployment()` 共用同一入口
- 在 `SmartRouter.__init__` 中将 fallback 链转换为 LiteLLM 格式并注入父类 Router
- 所有修改通过现有测试（72 passed）且新增测试覆盖上述三个修复点

## 非目标

- 不重构 LiteLLM Proxy 的集成方式（仍通过中间件修改请求体）
- 不改写 `cli.py` 的 `dry_run` 逻辑（它独立构建 model_pool，与本优化无关）
- 不引入新的模型能力字段（如 speed）或策略
- 不修改 token 估算算法

## 设计方案

### 架构概述

```
请求 → FastAPI 中间件 → SmartRouter.select_model() → 修改请求体 model
                             ↑
                    (共用同一方法)
                             ↓
LiteLLM Router → SmartRouter.get_available_deployment() → select_model()
                             ↓
                    LiteLLM 原生 fallback 按配置链重试
```

### 组件设计

#### 组件 1: `Config` (schema.py)

**职责**: 正确的 Pydantic v2 配置验证与 fallback 链预计算

**变更**:
- 删除 `model_post_init(self, __context)` 方法
- 添加 `@model_validator(mode='after')` 方法 `init_fallback_chains()`
- 在该 validator 中调用 `_derive_fallback_chains()` 并赋值给 `self._fallback_chains`

**接口保持不变**:
- `get_fallback_chain(model_name: str) -> List[str]`
- `get_litellm_params(model_name: str) -> dict`

#### 组件 2: `SmartRouter` (plugin.py)

**职责**: 统一的路由决策入口 + LiteLLM fallback 集成

**新增方法**:
```python
def select_model(
    self,
    model_hint: str,
    messages: List[Dict],
    strategy: str = "auto"
) -> ModelSelectionResult:
    """
    统一路由决策：解析标记 → 分类任务 → 估算上下文 → 选择模型
    
    Args:
        model_hint: 原始请求中的模型名（如 "auto", "stage:code_review"）
        messages: OpenAI 格式的消息列表
        strategy: 路由策略（auto/quality/cost）
    
    Returns:
        ModelSelectionResult: 包含选中的模型名及决策原因
    """
```

**修改方法**:
- `get_available_deployment()`: 当 `model` 为 auto/smart-router/default/stage:*/strategy-* 时，调用 `self.select_model()` 获取结果，再调用 `super().get_available_deployment(selected_model, ...)`

**修改构造函数**:
- 构建 `fallbacks` 列表：`[{"model_a": ["fallback_b", "fallback_c"]}]`
- 传给 `super().__init__(fallbacks=fallbacks, ...)`

#### 组件 3: FastAPI 中间件 (server.py)

**职责**: 请求拦截、调用统一路由决策、修改请求体、注入响应头

**变更**:
- 删除中间件内嵌的分类+选择逻辑（约 60 行）
- 精简为：
  1. 判断是否需要智能路由（model 为 auto/smart-router/default/stage:*/strategy-*）
  2. 若需要，调用 `app.state.smart_router.select_model(original_model, messages)`
  3. 修改请求体中的 `model` 为选中模型
  4. 重建 Request
- 保留响应头注入逻辑（`X-Smart-Router-Model` 等）
- 异常处理：若 `select_model()` 失败，记录 warning 后继续使用原始 model（避免完全阻断）

### 数据流

```
1. 用户请求 POST /v1/chat/completions
   body: {"model": "auto", "messages": [...]}

2. 中间件拦截
   - 读取 body
   - 调用 app.state.smart_router.select_model("auto", messages)
   - 返回 ModelSelectionResult(model_name="gpt-4o", ...)
   - 修改 body["model"] = "gpt-4o"
   - 重建 Request

3. LiteLLM Proxy 处理
   - 调用 Router.get_available_deployment("gpt-4o", messages)
   - SmartRouter.get_available_deployment() 看到具体模型名
   - 直接 super() → 正常路由到 gpt-4o

4. 若 gpt-4o 调用失败
   - LiteLLM Router 根据 fallbacks=[{"gpt-4o": ["claude-3-5-sonnet"]}]
   - 自动重试 claude-3-5-sonnet
```

### 错误处理

- `select_model()` 内部任何异常（分类器失败、选择器失败）都应被捕获，返回默认模型（quality 最高的模型），并记录 warning
- 中间件中 `select_model()` 失败时，不修改请求体，让请求按原始 model 继续（避免阻断）
- LiteLLM fallback 由 LiteLLM 原生处理，SmartRouter 不干预重试逻辑

### 安全考虑

- 中间件仍需要读取请求体，但不再重复解析和分类，减少了处理时间
- `select_model()` 是同步方法（分类和选择都是 CPU 密集型、无 IO），避免阻塞事件循环

## 验收标准

- [ ] `Config` 实例化后，`get_fallback_chain("gpt-4o")` 返回非空列表（quality 差异 <= threshold 的模型）
- [ ] `SmartRouter.select_model("auto", messages)` 返回的 `model_name` 与当前中间件逻辑一致
- [ ] `server.py` 中间件行数减少（删除重复分类选择逻辑）
- [ ] `SmartRouter.__init__` 传入 `fallbacks` 参数后，LiteLLM Router 在模型失败时自动按链重试
- [ ] 所有现有通过测试（72 个）仍然通过
- [ ] 新增测试覆盖：fallback 链非空、select_model 统一入口、fallback 配置格式正确

## 实现任务（概览）

1. 修复 `Config` Pydantic v2 fallback 链初始化
2. 提取 `SmartRouter.select_model()` 统一路由决策方法
3. 精简 `server.py` 中间件，调用 `select_model()`
4. 在 `SmartRouter.__init__` 中注入 LiteLLM fallbacks
5. 编写/更新测试

## 技术栈

- Python 3.9+
- Pydantic 2.x
- LiteLLM Router
- FastAPI / Starlette

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 中间件精简后行为改变 | 高 | 保留原有判断逻辑（哪些 model 需要路由），仅替换内部实现为 `select_model()` 调用 |
| LiteLLM fallbacks 格式不兼容 | 中 | 参考 LiteLLM 文档确认格式，编写单元测试验证转换后的数据结构 |
| `select_model` 成为同步热点 | 低 | 分类和选择均为纯内存计算（正则+字典查找），< 1ms 延迟，无需异步 |

## 附录

### 参考文档
- [LiteLLM Router Fallbacks](https://docs.litellm.ai/docs/routing#fallbacks)
- Pydantic v2 `model_validator(mode='after')` 文档

### 决策记录

**决策**: 不在中间件中完全删除路由逻辑，而是将其替换为对 `SmartRouter.select_model()` 的调用
**原因**: LiteLLM Proxy 的 `initialize()` 会创建自己的 Router 实例，我们无法直接替换为 SmartRouter，因此中间件修改请求体仍是必要手段
**替代方案**: 深度 hack LiteLLM Proxy 的初始化流程以注入 SmartRouter（过于侵入，拒绝）
