"""Tests for ConfigWatcher — 配置热重载监听器"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock


class TestConfigWatcher:
    """ConfigWatcher 基础功能测试"""

    def test_watcher_detects_yaml_file_change(self):
        """修改 providers.yaml 后回调应被触发"""
        from smart_router.config.watcher import ConfigWatcher

        callback_called = False
        received_config = None

        def on_reload(config):
            nonlocal callback_called, received_config
            callback_called = True
            received_config = config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            (config_dir / "providers.yaml").write_text(
                "providers:\n  test:\n    api_base: http://test.com\n    api_key: test\n"
            )
            (config_dir / "models.yaml").write_text(
                "models:\n  gpt-4o:\n    provider: test\n    litellm_model: openai/gpt-4o\n"
                "    capabilities:\n      quality: 9\n      cost: 3\n      context: 128000\n"
                "    supported_tasks: [chat]\n    difficulty_support: [easy]\n"
            )
            (config_dir / "routing.yaml").write_text(
                "tasks:\n  chat:\n    name: Chat\n    description: Chat\n"
                "    capability_weights:\n      quality: 0.5\n      cost: 0.5\n"
                "difficulties:\n  easy:\n    description: Easy\n    max_tokens: 1000\n"
                "strategies:\n  auto:\n    description: Auto\n"
                "fallback:\n  mode: auto\n"
            )

            watcher = ConfigWatcher(config_dir, on_reload, debounce_seconds=0.1)
            watcher.start()

            try:
                # 修改 providers.yaml
                (config_dir / "providers.yaml").write_text(
                    "providers:\n  test:\n    api_base: http://new.com\n    api_key: new\n"
                )

                # 等待 watchdog 检测 + debounce
                time.sleep(0.5)

                assert callback_called, "文件变更后 on_reload 回调应被触发"
                assert received_config is not None
            finally:
                watcher.stop()

    def test_watcher_ignores_non_yaml_files(self):
        """非 YAML 文件变更不应触发回调"""
        from smart_router.config.watcher import ConfigWatcher

        callback_called = False

        def on_reload(config):
            nonlocal callback_called
            callback_called = True

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            (config_dir / "providers.yaml").write_text("providers:\n")
            (config_dir / "models.yaml").write_text("models:\n")
            (config_dir / "routing.yaml").write_text("tasks:\n")

            watcher = ConfigWatcher(config_dir, on_reload, debounce_seconds=0.1)
            watcher.start()

            try:
                # 创建一个非 YAML 文件
                (config_dir / "readme.txt").write_text("hello")
                time.sleep(0.3)

                assert not callback_called, "非 YAML 文件变更不应触发回调"
            finally:
                watcher.stop()

    def test_watcher_skips_invalid_config(self):
        """YAML 语法错误时不应触发回调（保留旧配置）"""
        from smart_router.config.watcher import ConfigWatcher

        callback_called = False

        def on_reload(config):
            nonlocal callback_called
            callback_called = True

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            (config_dir / "providers.yaml").write_text(
                "providers:\n  test:\n    api_base: http://test.com\n    api_key: test\n"
            )
            (config_dir / "models.yaml").write_text("models:\n")
            (config_dir / "routing.yaml").write_text("tasks:\n")

            watcher = ConfigWatcher(config_dir, on_reload, debounce_seconds=0.1)
            watcher.start()

            try:
                # 写入无效 YAML
                (config_dir / "providers.yaml").write_text("providers: [invalid")
                time.sleep(0.5)

                assert not callback_called, "无效配置不应触发回调"
            finally:
                watcher.stop()

    def test_watcher_start_stop_idempotent(self):
        """多次 start/stop 不应报错"""
        from smart_router.config.watcher import ConfigWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            (config_dir / "providers.yaml").write_text("providers:\n")
            (config_dir / "models.yaml").write_text("models:\n")
            (config_dir / "routing.yaml").write_text("tasks:\n")

            watcher = ConfigWatcher(config_dir, lambda c: None)
            watcher.start()
            watcher.start()  # 不应报错
            watcher.stop()
            watcher.stop()  # 不应报错
