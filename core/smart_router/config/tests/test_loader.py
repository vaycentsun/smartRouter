"""ConfigLoader 测试"""

import pytest
from pathlib import Path

from smart_router.config.loader import ConfigLoader, ConfigError


class TestConfigLoaderModelsDir:
    """测试 models/ 目录加载"""

    def test_load_models_from_directory(self, tmp_path):
        """从 models/ 目录加载多个 YAML 文件"""
        # 创建 providers.yaml
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
  _virtual:
    api_base: ""
    api_key: ""
    timeout: 30
""")
        # 创建 routing.yaml
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        # 创建 models/ 目录和文件
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        (models_dir / "openai.yaml").write_text("""
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        (models_dir / "_virtual.yaml").write_text("""
models:
  auto:
    provider: _virtual
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 10
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        config = loader.load()

        assert "gpt-4o" in config.models
        assert "auto" in config.models
        assert config.models["gpt-4o"].provider == "openai"
        assert config.models["auto"].provider == "_virtual"

    def test_models_key_conflict(self, tmp_path):
        """同名模型出现在多个文件中时报错"""
        # 创建基础文件
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
""")
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        (models_dir / "openai.yaml").write_text("""
models:
  gpt-4:
    provider: openai
    litellm_model: openai/gpt-4
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        (models_dir / "anthropic.yaml").write_text("""
models:
  gpt-4:
    provider: anthropic
    litellm_model: anthropic/claude-3
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        with pytest.raises(ConfigError) as exc_info:
            loader.load()
        assert "gpt-4" in str(exc_info.value)
        assert "冲突" in str(exc_info.value)

    def test_deprecated_models_yaml(self, tmp_path):
        """models/ 不存在但 models.yaml 存在时提示废弃"""
        (tmp_path / "providers.yaml").write_text("providers:\n  openai:\n    api_base: https://api.openai.com\n    api_key: sk-test\n    timeout: 30\n")
        (tmp_path / "routing.yaml").write_text("tasks: {}\ndifficulties: {}\nstrategies: {}\nfallback:\n  mode: auto\n  similarity_threshold: 2\n  provider_isolation: false\n  max_attempts: 3\n\n")
        (tmp_path / "models.yaml").write_text("models: {}\n")

        loader = ConfigLoader(tmp_path)
        with pytest.raises(ConfigError) as exc_info:
            loader.load()
        assert "已废弃" in str(exc_info.value)
        assert "models/ 目录" in str(exc_info.value)

    def test_missing_models_directory(self, tmp_path):
        """models/ 和 models.yaml 都不存在时提示缺失"""
        (tmp_path / "providers.yaml").write_text("providers:\n  openai:\n    api_base: https://api.openai.com\n    api_key: sk-test\n    timeout: 30\n")
        (tmp_path / "routing.yaml").write_text("tasks: {}\ndifficulties: {}\nstrategies: {}\nfallback:\n  mode: auto\n  similarity_threshold: 2\n  provider_isolation: false\n  max_attempts: 3\n\n")

        loader = ConfigLoader(tmp_path)
        with pytest.raises(ConfigError) as exc_info:
            loader.load()
        assert "models" in str(exc_info.value)

    def test_validate_with_models_dir(self, tmp_path):
        """validate() 正确检查 models/ 目录存在"""
        (tmp_path / "providers.yaml").write_text("providers:\n  openai:\n    api_base: https://api.openai.com\n    api_key: sk-test\n    timeout: 30\n")
        (tmp_path / "routing.yaml").write_text("tasks: {}\ndifficulties: {}\nstrategies: {}\nfallback:\n  mode: auto\n  similarity_threshold: 2\n  provider_isolation: false\n  max_attempts: 3\n\n")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "openai.yaml").write_text("models: {}\n")

        loader = ConfigLoader(tmp_path)
        errors = loader.validate()
        assert errors == []

    def test_validate_missing_models_dir(self, tmp_path):
        """validate() 检测到 models/ 缺失"""
        (tmp_path / "providers.yaml").write_text("providers:\n  openai:\n    api_base: https://api.openai.com\n    api_key: sk-test\n    timeout: 30\n")
        (tmp_path / "routing.yaml").write_text("tasks: {}\ndifficulties: {}\nstrategies: {}\nfallback:\n  mode: auto\n  similarity_threshold: 2\n  provider_isolation: false\n  max_attempts: 3\n\n")

        loader = ConfigLoader(tmp_path)
        errors = loader.validate()
        assert any("models/" in e for e in errors)

    def test_auto_inject_virtual_provider(self, tmp_path):
        """providers.yaml 缺失 _virtual 时自动注入，兼容旧配置"""
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
""")
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "_virtual.yaml").write_text("""
models:
  auto:
    provider: _virtual
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 10
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        config = loader.load()

        assert "_virtual" in config.providers
        assert config.providers["_virtual"].api_base == ""
        assert config.providers["_virtual"].api_key == ""
        assert config.models["auto"].provider == "_virtual"

    def test_virtual_model_with_zero_capabilities_fails(self, tmp_path):
        """虚拟模型 quality/cost 为 0 时应导致验证失败"""
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
""")
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "_virtual.yaml").write_text("""
models:
  auto:
    provider: _virtual
    litellm_model: openai/virtual-model
    capabilities:
      quality: 0
      cost: 0
      context: 2560000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        with pytest.raises(ConfigError) as exc_info:
            loader.load()
        assert "validation" in str(exc_info.value).lower()

    def test_preserve_existing_virtual_provider(self, tmp_path):
        """providers.yaml 已包含 _virtual 时不覆盖用户配置"""
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
  _virtual:
    api_base: "http://custom"
    api_key: "custom-key"
    timeout: 60
""")
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "_virtual.yaml").write_text("""
models:
  auto:
    provider: _virtual
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 10
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        config = loader.load()

        assert config.providers["_virtual"].api_base == "http://custom"
        assert config.providers["_virtual"].api_key == "custom-key"
        assert config.providers["_virtual"].timeout == 60
