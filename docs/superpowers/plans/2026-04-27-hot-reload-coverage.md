# 配置热重载 + 测试覆盖率提升 实施计划

> **For agentic workers:** Use superpowers:subagent-driven-development or execute inline. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 实现 watchdog 自动监听三文件配置变更并热重载；运行 pytest-cov 找出盲区并补充测试

**Architecture:** ConfigWatcher (watchdog) → debounced reload → SmartRouter.update_config() → coverage gap analysis → test supplementation

**Tech Stack:** Python 3.9+, watchdog, pytest-cov

---

## File Map

| 文件 | 职责 | 变更 |
|------|------|------|
| `src/smart_router/config/watcher.py` | 配置热重载监听器 | 新建 |
| `src/smart_router/router/plugin.py` | 路由插件 | 新增 `reload_config()` |
| `src/smart_router/gateway/server.py` | 服务启动 | 集成 ConfigWatcher |
| `src/smart_router/config/tests/test_watcher.py` | 监听器测试 | 新建 |
| `src/smart_router/router/tests/test_plugin.py` | 插件测试 | 新增 reload 测试 |
| `pyproject.toml` | 项目配置 | 添加 pytest-cov 选项 |
| 多个测试文件 | 覆盖率补充 | 按需新增 |

---

## Task 1: 配置热重载

**Files:**
- Create: `src/smart_router/config/watcher.py`
- Modify: `src/smart_router/router/plugin.py`
- Modify: `src/smart_router/gateway/server.py`
- Test: `src/smart_router/config/tests/test_watcher.py`
- Test: `src/smart_router/router/tests/test_plugin.py`

- [ ] **Step 1: Write failing test for ConfigWatcher**

```python
def test_config_watcher_detects_file_change():
    """ConfigWatcher 应能检测到配置文件变更并触发回调"""
    import tempfile
    from pathlib import Path
    from smart_router.config.watcher import ConfigWatcher
    
    callback_called = False
    
    def on_reload(config):
        nonlocal callback_called
        callback_called = True
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        (config_dir / "providers.yaml").write_text("providers:\n  test:\n    api_base: http://test.com\n    api_key: test")
        (config_dir / "models.yaml").write_text("models:")
        (config_dir / "routing.yaml").write_text("tasks:")
        
        watcher = ConfigWatcher(config_dir, on_reload)
        watcher.start()
        
        # 修改文件
        import time
        (config_dir / "providers.yaml").write_text("providers:\n  test:\n    api_base: http://new.com\n    api_key: new")
        time.sleep(1)
        
        watcher.stop()
        assert callback_called, "文件变更后回调应被触发"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest src/smart_router/config/tests/test_watcher.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create ConfigWatcher**

Create `src/smart_router/config/watcher.py`:

```python
import time
import threading
from pathlib import Path
from typing import Callable, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .loader import ConfigLoader
from .schema import Config


class ConfigWatcher:
    """配置文件热重载监听器
    
    基于 watchdog 监听配置目录下的 YAML 文件变更，
    自动重新加载配置并通过回调通知消费者。
    """
    
    def __init__(
        self,
        config_dir: Path,
        on_reload: Callable[[Config], None],
        debounce_seconds: float = 0.5
    ):
        self.config_dir = Path(config_dir)
        self.on_reload = on_reload
        self.debounce_seconds = debounce_seconds
        
        self._observer: Optional[Observer] = None
        self._last_reload = 0.0
        self._lock = threading.Lock()
    
    def start(self):
        """启动文件监听"""
        if self._observer is not None:
            return
        
        event_handler = _ConfigFileHandler(self._on_file_changed)
        self._observer = Observer()
        self._observer.schedule(event_handler, str(self.config_dir), recursive=False)
        self._observer.start()
    
    def stop(self):
        """停止文件监听"""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
    
    def _on_file_changed(self, event):
        """文件变更回调（内部）"""
        # 只处理 YAML 文件
        if not event.src_path.endswith(('.yaml', '.yml')):
            return
        
        # 去抖动
        with self._lock:
            now = time.time()
            if now - self._last_reload < self.debounce_seconds:
                return
            self._last_reload = now
        
        try:
            loader = ConfigLoader(self.config_dir)
            config = loader.load()
            errors = loader.validate()
            if errors:
                # 验证失败时保留旧配置，只打印错误
                print(f"[ConfigWatcher] 配置验证失败，跳过重载: {errors}")
                return
            self.on_reload(config)
        except Exception as e:
            print(f"[ConfigWatcher] 配置重载失败: {e}")


class _ConfigFileHandler(FileSystemEventHandler):
    """内部事件处理器"""
    
    def __init__(self, callback):
        self.callback = callback
    
    def on_modified(self, event):
        if not event.is_directory:
            self.callback(event)
    
    def on_created(self, event):
        if not event.is_directory:
            self.callback(event)
```

- [ ] **Step 4: Add reload_config to SmartRouter**

Modify `src/smart_router/router/plugin.py`:

```python
def reload_config(self, config: Config):
    """运行时重新加载配置
    
    Args:
        config: 新的 Config 实例
    """
    self.sr_config = config
    
    # 重建分类器
    classification_rules = [
        {
            "pattern": f"(?i)({task_config.name.lower().replace('_', '|')})",
            "task_type": task_id,
            "difficulty": "medium"
        }
        for task_id, task_config in config.routing.tasks.items()
    ]
    
    task_configs = {
        task_id: {
            "keywords": list(getattr(task_config, "keywords", [])),
            "examples": list(getattr(task_config, "examples", [])),
            "description": task_config.description
        }
        for task_id, task_config in config.routing.tasks.items()
    }
    
    self.classifier = TaskClassifier(
        rules=classification_rules,
        embedding_config={"enabled": True, "threshold": 0.6, "default_task": "chat"},
        task_configs=task_configs
    )
    
    # 重建选择器
    available_models = config.get_available_models()
    self.selector = V3ModelSelector(config=config, available_models=available_models)
    
    # 更新 LiteLLM Router 的模型列表
    litellm_model_list = []
    for model_name in available_models:
        litellm_params = config.get_litellm_params(model_name)
        litellm_model_list.append({
            "model_name": model_name,
            "litellm_params": litellm_params
        })
    
    fallbacks = []
    for model_name in available_models:
        chain = config.get_fallback_chain(model_name)
        if chain:
            fallbacks.append({model_name: chain})
    
    # 更新父类 Router 的模型列表
    self.model_list = litellm_model_list
    self.set_model_list(litellm_model_list)
    if fallbacks:
        self.set_fallbacks(fallbacks)
```

- [ ] **Step 5: Integrate watcher into server.py**

Modify `src/smart_router/gateway/server.py`:

```python
from ..config.watcher import ConfigWatcher

def start_server(...):
    # ... existing code ...
    router = SmartRouter(config=config)
    
    # 启动配置热重载监听
    watcher = ConfigWatcher(
        config_dir=config_dir,
        on_reload=router.reload_config
    )
    watcher.start()
    console.print("[dim]配置热重载已启用[/dim]")
    
    # ... existing code ...
    
    try:
        uvicorn.run(app, host=host, port=port)
    finally:
        watcher.stop()
```

- [ ] **Step 6: Run tests**

Run: `pytest src/smart_router/config/tests/test_watcher.py src/smart_router/router/tests/test_plugin.py -v`
Expected: PASS

---

## Task 2: 测试覆盖率提升

**Files:**
- Modify: `pyproject.toml`
- Modify: 多个测试文件

- [ ] **Step 1: Run pytest-cov to identify gaps**

Run: `pytest --cov=smart_router --cov-report=term-missing`

- [ ] **Step 2: Add pytest-cov config to pyproject.toml**

```toml
[tool.coverage.run]
source = ["src/smart_router"]
omit = ["*/tests/*", "*/test_*.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

- [ ] **Step 3-7: Supplement tests for uncovered paths**

根据 Step 1 的输出，针对未覆盖的代码路径逐一补充测试。
重点关注：
- 异常处理分支
- 边界条件
- 未被测试的模块（如 coffee_qr.py、daemon.py 的某些分支）

- [ ] **Step 8: Final verification**

Run: `pytest -v`
Expected: All tests pass

Run: `pytest --cov=smart_router --cov-report=term`
Expected: Coverage improved
