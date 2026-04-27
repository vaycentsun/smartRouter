"""配置文件热重载监听器

基于 watchdog 监听配置目录下的 YAML 文件变更，
自动重新加载配置并通过回调通知消费者。
"""

import time
import threading
from pathlib import Path
from typing import Callable, Optional

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

from .loader import ConfigLoader
from .schema import Config


class ConfigWatcher:
    """配置热重载监听器
    
    基于 watchdog 监听配置目录下的 YAML 文件变更，
    自动重新加载配置并通过回调通知消费者。
    
    使用去抖动机制：在 debounce_seconds 窗口内多次变更合并为一次重载。
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
        if not HAS_WATCHDOG:
            return
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
