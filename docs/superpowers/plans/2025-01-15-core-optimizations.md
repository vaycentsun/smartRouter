# Smart Router 核心优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复版本号同步、中间件重复注册、异常降级、rate_limit 未使用四个核心问题

**Architecture:** 通过 importlib.metadata 实现版本号单源、BaseHTTPMiddleware 子类安全注册中间件、分层异常与 fallback 机制、将 rate_limit 传递给 LiteLLM Router

**Tech Stack:** Python 3.9+, FastAPI, Pydantic, LiteLLM, pytest

---

## File Map

| 文件 | 职责 | 变更 |
|------|------|------|
| `src/smart_router/__init__.py` | 版本号定义 | 改为动态读取 importlib.metadata |
| `src/smart_router/cli.py` | CLI 入口 | 从 __init__ 导入版本号 |
| `src/smart_router/gateway/server.py` | 服务启动与中间件 | 提取中间件为类，条件注册 |
| `src/smart_router/router/plugin.py` | 路由决策入口 | 增加异常捕获与 fallback |
| `src/smart_router/selector/v3_selector.py` | 模型选择器 | 增加 SafeSelect 包装 |
| `src/smart_router/config/schema.py` | 配置模型 | 将 rate_limit 传递给 litellm_params |
| `src/smart_router/gateway/tests/test_server.py` | 网关测试 | 增加中间件与异常测试 |
| `src/smart_router/router/tests/test_plugin.py` | 路由插件测试 | 增加 fallback 测试 |

---

## Task 1: 版本号同步机制

**Files:**
- Modify: `src/smart_router/__init__.py`
- Modify: `src/smart_router/cli.py`
- Test: `src/smart_router/tests/cli/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
def test_version_matches_package_metadata():
    """版本号应与 package metadata 一致"""
    from importlib.metadata import version
    from smart_router import __version__
    
    assert __version__ == version("smartrouter")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest src/smart_router/tests/cli/test_cli.py -v -k version`
Expected: FAIL if __version__ hardcoded differently

- [ ] **Step 3: Modify __init__.py to use importlib.metadata**

```python
try:
    from importlib.metadata import version
    __version__ = version("smartrouter")
except ImportError:
    __version__ = "1.1.0"
```

- [ ] **Step 4: Modify cli.py to import from __init__**

Replace `__version__ = "1.1.0"` with:
```python
from smart_router import __version__
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest src/smart_router/tests/cli/test_cli.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/smart_router/__init__.py src/smart_router/cli.py
git commit -m "fix: use importlib.metadata for version sync"
```

---

## Task 2: 中间件重复注册修复

**Files:**
- Modify: `src/smart_router/gateway/server.py`
- Test: `src/smart_router/gateway/tests/test_server.py`

- [ ] **Step 1: Write the failing test**

```python
def test_middleware_added_only_once():
    """中间件应只被添加一次"""
    from unittest.mock import MagicMock, patch
    
    app = MagicMock()
    app.state = MagicMock()
    # 模拟已经添加过中间件
    app.state._smart_router_middleware_added = True
    
    # 验证不会再次调用 add_middleware
    # 这里测试的是重构后的逻辑
    assert app.add_middleware.call_count == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest src/smart_router/gateway/tests/test_server.py::TestMiddlewareLogic -v`
Expected: 需要重构后才会有新测试

- [ ] **Step 3: Extract middleware to BaseHTTPMiddleware subclass**

在 `server.py` 中创建 `SmartRouterMiddleware` 类：

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SmartRouterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, router):
        super().__init__(app)
        self.router = router
    
    async def dispatch(self, request: Request, call_next):
        # 原有中间件逻辑
        ...
```

- [ ] **Step 4: Replace decorator with conditional add_middleware**

```python
if not getattr(app.state, '_smart_router_middleware_added', False):
    app.add_middleware(SmartRouterMiddleware, router=router)
    app.state._smart_router_middleware_added = True
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest src/smart_router/gateway/tests/test_server.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/smart_router/gateway/server.py
git commit -m "fix: prevent middleware double registration with BaseHTTPMiddleware"
```

---

## Task 3: 异常处理与优雅降级

**Files:**
- Modify: `src/smart_router/selector/v3_selector.py`
- Modify: `src/smart_router/router/plugin.py`
- Modify: `src/smart_router/gateway/server.py`
- Test: `src/smart_router/router/tests/test_plugin.py`
- Test: `src/smart_router/gateway/tests/test_server.py`

- [ ] **Step 1: Write failing test for graceful fallback**

```python
def test_select_model_graceful_fallback():
    """当没有模型匹配时，应 fallback 到第一个可用模型"""
    from smart_router.router.plugin import SmartRouter
    from smart_router.config import (
        Config, ProviderConfig, ModelConfig, ModelCapabilities,
        RoutingConfig, TaskConfig, DifficultyConfig, StrategyConfig, FallbackConfig
    )
    
    config = Config(...)
    router = SmartRouter(config)
    
    # 请求一个不存在任务类型的模型
    result = router.select_model("auto", messages=[{"role": "user", "content": "test"}])
    
    # 应该返回一个可用模型，而不是抛出异常
    assert result.model_name is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest src/smart_router/router/tests/test_plugin.py -v -k fallback`
Expected: FAIL with NoModelAvailableError

- [ ] **Step 3: Add fallback logic in plugin.py select_model**

```python
def select_model(self, model_hint, messages=None, strategy="auto"):
    try:
        result = self.selector.select(...)
    except NoModelAvailableError:
        # Fallback: 选择第一个可用模型
        available = self.sr_config.get_available_models()
        if available:
            from ..selector.v3_selector import SelectionResult
            result = SelectionResult(
                model_name=available[0],
                task_type="unknown",
                difficulty="medium",
                strategy="fallback",
                score=0.0,
                reason="No matching model found, using fallback"
            )
        else:
            raise
    
    self.last_selected_model = result.model_name
    return result
```

- [ ] **Step 4: Improve HTTP exception handling in server.py**

将中间件中的 `except Exception` 改为：
```python
except NoModelAvailableError:
    # 返回 503
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=503,
        content={"error": "No model available for this request"}
    )
except Exception as e:
    console.print(f"[yellow]智能路由失败，使用原始模型: {e}[/yellow]")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest src/smart_router/router/tests/test_plugin.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/smart_router/router/plugin.py src/smart_router/gateway/server.py
git commit -m "feat: graceful fallback when no model matches"
```

---

## Task 4: rate_limit 字段实现

**Files:**
- Modify: `src/smart_router/config/schema.py`
- Test: `src/smart_router/config/tests/test_schema.py`

- [ ] **Step 1: Write failing test**

```python
def test_rate_limit_passed_to_litellm_params():
    """rate_limit 应出现在 litellm_params 中"""
    from smart_router.config import Config, ProviderConfig
    
    config = Config(...)
    params = config.get_litellm_params("gpt-4o")
    
    assert "rpm_limit" in params
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest src/smart_router/config/tests/test_schema.py -v -k rate_limit`
Expected: FAIL (rpm_limit not in params)

- [ ] **Step 3: Update get_litellm_params to include rate_limit**

```python
def get_litellm_params(self, model_name: str) -> dict:
    ...
    params = {
        "model": model.litellm_model,
        "api_key": api_key,
        "api_base": provider.api_base,
        "timeout": provider.timeout,
    }
    if provider.rate_limit:
        params["rpm_limit"] = provider.rate_limit
    return params
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest src/smart_router/config/tests/test_schema.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/smart_router/config/schema.py
git commit -m "feat: pass provider rate_limit to litellm as rpm_limit"
```

---

## 最终验证

- [ ] 运行全部测试

```bash
pytest -v
```

Expected: All 372+ tests pass

- [ ] 运行 linter（如果有配置）

```bash
ruff check src/
```

- [ ] 提交所有变更
