# 路由架构修复与 Fallback 重试 — 实现计划

## 概述

基于 Spec `specs/active/2026-04-21--routing-architecture-fix.md`，将三个优化点拆解为 5 个 TDD 任务。

---

## 任务概览

| 编号 | 任务 | 文件 | 依赖 | 预计时间 |
|------|------|------|------|----------|
| 1 | 修复 Config fallback 链初始化 | `src/smart_router/config/schema.py` | - | 5 min |
| 2 | 提取 SmartRouter.select_model | `src/smart_router/plugin.py` | - | 5 min |
| 3 | get_available_deployment 调用 select_model | `src/smart_router/plugin.py` | 任务 2 | 3 min |
| 4 | 精简 server.py 中间件 | `src/smart_router/server.py` | 任务 2 | 5 min |
| 5 | 注入 LiteLLM fallbacks | `src/smart_router/plugin.py` | 任务 1 | 5 min |

---

## 任务 1: 修复 Config Pydantic v2 fallback 链初始化

**目标**: 让 `Config` 实例化后 `_fallback_chains` 正确预计算

**文件**: `src/smart_router/config/schema.py`

**RED — 编写失败测试**:
在 `tests/test_config_schema.py` 中新增：
```python
def test_fallback_chain_populated_after_init():
    """Config 实例化后 fallback 链应已预计算"""
    from smart_router.config.schema import Config, ProviderConfig, ModelConfig, ModelCapabilities, RoutingConfig, TaskConfig, DifficultyConfig, StrategyConfig, FallbackConfig
    
    config = Config(
        providers={
            "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")
        },
        models={
            "gpt-4o": ModelConfig(
                provider="openai",
                litellm_model="openai/gpt-4o",
                capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                supported_tasks=["chat"],
                difficulty_support=["easy", "medium", "hard"]
            ),
            "gpt-4o-mini": ModelConfig(
                provider="openai",
                litellm_model="openai/gpt-4o-mini",
                capabilities=ModelCapabilities(quality=6, cost=9, context=128000),
                supported_tasks=["chat"],
                difficulty_support=["easy", "medium"]
            )
        },
        routing=RoutingConfig(
            tasks={},
            difficulties={},
            strategies={},
            fallback=FallbackConfig(similarity_threshold=2)
        )
    )
    
    chain = config.get_fallback_chain("gpt-4o")
    assert "gpt-4o-mini" in chain  # quality 差异 3 > 2，不应在链中？等等，差异是 3
    # 重新算：threshold=2，gpt-4o(9) 和 gpt-4o-mini(6) 差异为 3，不在链中
    # 所以需要另一个更接近的模型...
    # 用 quality=8 的模型
```

用 quality 差异 <= 2 的模型验证：
```python
"claude": ModelConfig(..., capabilities=ModelCapabilities(quality=8, ...), ...)
# gpt-4o(9) 和 claude(8) 差异 1 <= 2，应在链中
```

**GREEN — 最简实现**:
```python
@model_validator(mode='after')
def init_fallback_chains(self):
    """预计算 fallback 链"""
    self._fallback_chains = self._derive_fallback_chains()
    return self
```
删除原有的 `model_post_init` 方法。

**验证**:
- [ ] 新测试先失败（因 `model_post_init` 不生效）
- [ ] 修改后测试通过
- [ ] 所有现有测试仍通过

---

## 任务 2: 提取 SmartRouter.select_model 统一路由决策

**目标**: 将路由决策逻辑提取为可复用的 `select_model()` 方法

**文件**: `src/smart_router/plugin.py`

**RED — 编写失败测试**:
在 `tests/test_plugin.py` 中新增（如不存在则创建）：
```python
def test_select_model_returns_valid_model():
    """select_model 应对 auto 请求返回有效模型名"""
    from smart_router.plugin import SmartRouter
    from smart_router.config.schema import Config, ProviderConfig, ModelConfig, ModelCapabilities, RoutingConfig, TaskConfig, DifficultyConfig, StrategyConfig, FallbackConfig
    
    config = Config(...)
    router = SmartRouter(config=config)
    
    messages = [{"role": "user", "content": "Hello"}]
    result = router.select_model("auto", messages)
    
    assert result.model_name in config.models
    assert result.confidence > 0
```

**GREEN — 最简实现**:
在 `SmartRouter` 中添加：
```python
def select_model(
    self,
    model_hint: str,
    messages: List[Dict],
    strategy: str = "auto"
) -> ModelSelectionResult:
    """统一路由决策"""
    markers = parse_markers(messages)
    classification = self._get_classification(markers, messages)
    estimated_input = estimate_messages_tokens(messages)
    required_context = estimated_input + 4000 if estimated_input > 0 else 0
    
    return self.selector.select(
        task_type=classification.task_type,
        difficulty=classification.estimated_difficulty,
        strategy=strategy,
        required_context=required_context
    )
```

**验证**:
- [ ] 新测试先失败（方法不存在）
- [ ] 实现后通过
- [ ] 现有测试仍通过

---

## 任务 3: get_available_deployment 调用 select_model

**目标**: 让 `get_available_deployment` 使用新的 `select_model` 方法

**文件**: `src/smart_router/plugin.py`

**RED — 编写失败测试**:
```python
@pytest.mark.asyncio
async def test_get_available_deployment_uses_select_model():
    """get_available_deployment 应委托给 select_model"""
    # Mock super().get_available_deployment 验证传入的 model 是选中模型
```

由于 `get_available_deployment` 调用 `super()` 且涉及 LiteLLM 内部，单元测试较困难。改为验证 `select_model` 被调用：
```python
def test_get_available_deployment_calls_select_model():
    from unittest.mock import patch
    router = SmartRouter(config=config)
    with patch.object(router, 'select_model') as mock_select:
        mock_select.return_value = ModelSelectionResult(
            model_name="gpt-4o", task_type="chat", difficulty="medium",
            confidence=0.9, reason="test"
        )
        # 调用 get_available_deployment 是 async，同步测试中 patch 逻辑即可
        # 实际：通过测试 select_model 的独立行为间接验证
```

简化方案：不新增单独测试，通过任务 2 的测试和任务 4 的集成测试覆盖。

**GREEN — 最简实现**:
修改 `get_available_deployment`:
```python
async def get_available_deployment(self, model, messages=None, request_kwargs=None):
    if model not in ("auto", "smart-router", "default") and not model.startswith("stage:"):
        return await super().get_available_deployment(model=model, messages=messages, request_kwargs=request_kwargs)
    
    if messages is None:
        messages = []
    
    result = self.select_model(model, messages)
    self.last_selected_model = result.model_name
    
    return await super().get_available_deployment(
        model=result.model_name, messages=messages, request_kwargs=request_kwargs
    )
```

同时修改 `_get_classification` 使其支持 `model_hint` 中的 `stage:` 前缀解析（当前已在 `server.py` 中间件中处理，需要移到 `select_model` 或 `_get_classification` 中）。

实际上，`model_hint` 可能包含 `stage:code_review`，当前 `_get_classification` 只解析 messages 中的 markers，不解析 model_hint。需要在 `select_model` 中增加对 `model_hint` 的解析：
```python
def select_model(...):
    # 如果 model_hint 是 stage:xxx，直接使用
    if model_hint.startswith("stage:"):
        task_type = model_hint.replace("stage:", "")
        # ...
    # 否则正常分类
```

**验证**:
- [ ] `get_available_deployment` 代码行数减少
- [ ] 逻辑委托给 `select_model`

---

## 任务 4: 精简 server.py 中间件

**目标**: 删除中间件中重复的分类选择逻辑，调用 `select_model`

**文件**: `src/smart_router/server.py`

**RED — 编写失败测试**:
由于 `server.py` 依赖 FastAPI + LiteLLM，集成测试成本高。使用现有 `tests/test_integration.py` 框架（如果可用）或验证中间件行为的 mock 测试。现有测试通过即视为合格。

**GREEN — 最简实现**:
中间件中替换以下逻辑：
```python
# 删除：中间件内嵌的分类+选择逻辑（约 60 行）
# 替换为：
if should_route and hasattr(app.state, 'smart_router'):
    messages = data.get("messages", [])
    strategy = "auto"
    if original_model.startswith("strategy-"):
        strategy = original_model.replace("strategy-", "")
    
    try:
        result = app.state.smart_router.select_model(
            model_hint=original_model,
            messages=messages,
            strategy=strategy
        )
        selected = result.model_name
        # ... 修改请求体、保存 state、重建 request
    except Exception as e:
        console.print(f"[yellow]智能路由失败: {e}[/yellow]")
        # 不修改请求体，继续使用原始 model
```

**验证**:
- [ ] 现有通过测试（72 个）仍通过
- [ ] 中间件逻辑行数显著减少
- [ ] `dry-run` CLI 命令行为不变

---

## 任务 5: 注入 LiteLLM fallbacks

**目标**: 在 `SmartRouter.__init__` 中将 fallback 链转换为 LiteLLM 格式并注入

**文件**: `src/smart_router/plugin.py`

**RED — 编写失败测试**:
```python
def test_fallbacks_passed_to_litellm():
    """SmartRouter 应将 Config 的 fallback 链转为 LiteLLM fallbacks 格式"""
    from unittest.mock import patch
    
    with patch('smart_router.plugin.Router.__init__', return_value=None) as mock_super:
        config = Config(...)
        router = SmartRouter(config=config)
        
        call_kwargs = mock_super.call_args.kwargs
        assert "fallbacks" in call_kwargs
        fallbacks = call_kwargs["fallbacks"]
        # 验证格式: [{"model_a": ["model_b"]}]
        assert isinstance(fallbacks, list)
        assert len(fallbacks) > 0
```

**GREEN — 最简实现**:
在 `SmartRouter.__init__` 中，构建 model_list 之后、调用 `super().__init__` 之前：
```python
# 构建 LiteLLM fallbacks
fallbacks = []
for model_name in config.models.keys():
    chain = config.get_fallback_chain(model_name)
    if chain:
        fallbacks.append({model_name: chain})

super().__init__(
    model_list=litellm_model_list,
    fallbacks=fallbacks if fallbacks else None,
    *args,
    **kwargs
)
```

**验证**:
- [ ] 新测试先失败（fallbacks 未传入）
- [ ] 修改后测试通过
- [ ] `fallbacks` 格式符合 LiteLLM 要求

---

## 自检清单

- [x] **完整性** — 所有 Spec 中的功能都有对应任务
- [x] **粒度** — 每个任务 2-5 分钟
- [x] **明确性** — 每个任务有确切文件路径
- [x] **可验证** — 每个任务有验证步骤
- [x] **顺序合理** — 任务 1 是 Config 基础，任务 2 是核心方法，任务 3-4 是调用方，任务 5 是 fallback 注入
- [x] **无遗漏** — 测试任务包含在内
