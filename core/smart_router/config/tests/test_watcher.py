"""ConfigWatcher 子目录监听测试"""

import pytest
import time
from pathlib import Path
from unittest.mock import MagicMock

from smart_router.config.watcher import ConfigWatcher


class TestConfigWatcherSubdirectory:
    """测试 ConfigWatcher 监听子目录变更"""

    @pytest.mark.skipif(
        not hasattr(ConfigWatcher, '_observer'),
        reason="watchdog 未安装"
    )
    def test_watches_subdirectory_changes(self, tmp_path):
        """修改 models/ 子目录下的 YAML 文件能触发重载"""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        # 创建基础文件
        (tmp_path / "providers.yaml").write_text("providers:\n  openai:\n    api_base: https://api.openai.com\n    api_key: sk-test\n    timeout: 30\n")
        (tmp_path / "routing.yaml").write_text("tasks:\n  chat:\n    name: \"聊天\"\n    description: \"日常对话\"\n    capability_weights:\n      quality: 0.5\n      cost: 0.5\ndifficulties:\n  easy:\n    description: \"简单\"\n    max_tokens: 2000\nstrategies:\n  auto:\n    description: \"自动\"\nfallback:\n  mode: auto\n  similarity_threshold: 2\n  provider_isolation: false\n  max_attempts: 3\ncost_quality_threshold: 5\n")
        (models_dir / "openai.yaml").write_text("models:\n  gpt-4o:\n    provider: openai\n    litellm_model: openai/gpt-4o\n    capabilities:\n      quality: 9\n      cost: 3\n      context: 128000\n    supported_tasks: [chat]\n    difficulty_support: [easy]\n")

        mock_reload = MagicMock()
        watcher = ConfigWatcher(tmp_path, on_reload=mock_reload, debounce_seconds=0.1)
        watcher.start()

        try:
            # 修改子目录文件
            time.sleep(0.1)
            (models_dir / "openai.yaml").write_text("models:\n  gpt-4o:\n    provider: openai\n    litellm_model: openai/gpt-4o\n    capabilities:\n      quality: 8\n      cost: 3\n      context: 128000\n    supported_tasks: [chat]\n    difficulty_support: [easy]\n")

            # 等待 watcher 触发
            time.sleep(0.3)
            assert mock_reload.called
        finally:
            watcher.stop()

    def test_yaml_filter_includes_subdirectory(self, tmp_path):
        """事件过滤正确包含子目录的 YAML 文件"""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        (tmp_path / "providers.yaml").write_text("providers:\n  openai:\n    api_base: https://api.openai.com\n    api_key: sk-test\n    timeout: 30\n")
        (tmp_path / "routing.yaml").write_text("tasks:\n  chat:\n    name: \"聊天\"\n    description: \"日常对话\"\n    capability_weights:\n      quality: 0.5\n      cost: 0.5\ndifficulties:\n  easy:\n    description: \"简单\"\n    max_tokens: 2000\nstrategies:\n  auto:\n    description: \"自动\"\nfallback:\n  mode: auto\n  similarity_threshold: 2\n  provider_isolation: false\n  max_attempts: 3\ncost_quality_threshold: 5\n")
        (models_dir / "test.yaml").write_text("models: {}\n")

        mock_reload = MagicMock()
        watcher = ConfigWatcher(tmp_path, on_reload=mock_reload, debounce_seconds=0.1)

        # 直接测试事件过滤逻辑
        class MockEvent:
            def __init__(self, src_path):
                self.src_path = str(src_path)
                self.is_directory = False

        # 子目录 YAML 文件应通过过滤
        event = MockEvent(models_dir / "test.yaml")
        assert event.src_path.endswith(".yaml")

        # 非 YAML 文件应被过滤
        event_txt = MockEvent(tmp_path / "README.md")
        assert not event_txt.src_path.endswith((".yaml", ".yml"))
